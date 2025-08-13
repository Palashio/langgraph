import pytest
from typing import Annotated, TypedDict
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from langgraph.graph.message import MessageGraph, MessagesState, RemoveMessage, add_messages
from langgraph.graph.state import StateGraph
from langgraph.checkpoint.memory import MemorySaver


class TestRemoveMessage:
    """Test the RemoveMessage class functionality."""
    
    def test_remove_message_creation(self):
        """Test RemoveMessage object creation and properties."""
        remove_msg = RemoveMessage(id="test_id")
        assert remove_msg.id == "test_id"
        assert repr(remove_msg) == "RemoveMessage(id='test_id')"
    
    def test_remove_message_equality(self):
        """Test RemoveMessage equality comparison."""
        remove_msg1 = RemoveMessage(id="test_id")
        remove_msg2 = RemoveMessage(id="test_id")
        remove_msg3 = RemoveMessage(id="different_id")
        
        assert remove_msg1 == remove_msg2
        assert remove_msg1 != remove_msg3
        assert remove_msg1 != "not_a_remove_message"


class TestAddMessagesWithDeletion:
    """Test the add_messages function with RemoveMessage support."""
    
    def test_basic_message_deletion(self):
        """Test basic message deletion by ID."""
        # Setup initial messages
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        msg3 = HumanMessage(content="How are you?", id="msg3")
        left = [msg1, msg2, msg3]
        
        # Delete middle message
        right = [RemoveMessage(id="msg2")]
        result = add_messages(left, right)
        
        assert len(result) == 2
        assert result[0].id == "msg1"
        assert result[1].id == "msg3"
        assert result[0].content == "Hello"
        assert result[1].content == "How are you?"
    
    def test_delete_nonexistent_message(self):
        """Test deletion of non-existent messages (should be no-op)."""
        # Setup initial messages
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        left = [msg1, msg2]
        
        # Try to delete non-existent message
        right = [RemoveMessage(id="nonexistent")]
        result = add_messages(left, right)
        
        # Should remain unchanged
        assert len(result) == 2
        assert result[0].id == "msg1"
        assert result[1].id == "msg2"
    
    def test_deletion_combined_with_updates(self):
        """Test deletion combined with message updates."""
        # Setup initial messages
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        msg3 = HumanMessage(content="How are you?", id="msg3")
        left = [msg1, msg2, msg3]
        
        # Delete msg2 and update msg1, add new msg4
        right = [
            RemoveMessage(id="msg2"),
            HumanMessage(content="Hello updated", id="msg1"),  # Update existing
            AIMessage(content="New message", id="msg4")  # Add new
        ]
        result = add_messages(left, right)
        
        assert len(result) == 3
        assert result[0].id == "msg1"
        assert result[0].content == "Hello updated"  # Updated
        assert result[1].id == "msg3"
        assert result[1].content == "How are you?"  # Unchanged
        assert result[2].id == "msg4"
        assert result[2].content == "New message"  # New
    
    def test_delete_multiple_messages(self):
        """Test deleting multiple messages at once."""
        # Setup initial messages
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        msg3 = HumanMessage(content="How are you?", id="msg3")
        msg4 = AIMessage(content="I'm fine", id="msg4")
        left = [msg1, msg2, msg3, msg4]
        
        # Delete multiple messages
        right = [RemoveMessage(id="msg1"), RemoveMessage(id="msg3")]
        result = add_messages(left, right)
        
        assert len(result) == 2
        assert result[0].id == "msg2"
        assert result[1].id == "msg4"
    
    def test_delete_all_messages(self):
        """Test deleting all messages."""
        # Setup initial messages
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        left = [msg1, msg2]
        
        # Delete all messages
        right = [RemoveMessage(id="msg1"), RemoveMessage(id="msg2")]
        result = add_messages(left, right)
        
        assert len(result) == 0
    
    def test_single_remove_message_input(self):
        """Test passing a single RemoveMessage (not in a list)."""
        # Setup initial messages
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        left = [msg1, msg2]
        
        # Delete single message (not in list)
        right = RemoveMessage(id="msg1")
        result = add_messages(left, right)
        
        assert len(result) == 1
        assert result[0].id == "msg2"


class TestMessageGraphWithDeletion:
    """Test message deletion in MessageGraph nodes."""
    
    def test_node_returns_remove_message(self):
        """Test a node returning RemoveMessage objects."""
        def delete_node(state):
            # Delete the first message if it exists
            if state and len(state) > 0:
                return [RemoveMessage(id=state[0].id)]
            return []
        
        # Create graph
        graph = MessageGraph()
        graph.add_node("delete", delete_node)
        graph.set_entry_point("delete")
        graph.set_finish_point("delete")
        app = graph.compile()
        
        # Test with initial messages
        initial_messages = [
            HumanMessage(content="Hello", id="msg1"),
            AIMessage(content="Hi there", id="msg2")
        ]
        
        result = app.invoke(initial_messages)
        
        # First message should be deleted
        assert len(result) == 1
        assert result[0].id == "msg2"
        assert result[0].content == "Hi there"
    
    def test_node_mixed_operations(self):
        """Test a node performing mixed operations (add, update, delete)."""
        def mixed_operations_node(state):
            operations = []
            
            # If we have messages, delete the first one
            if state and len(state) > 0:
                operations.append(RemoveMessage(id=state[0].id))
            
            # Add a new message
            operations.append(AIMessage(content="New AI message", id="new_msg"))
            
            # Update an existing message if it exists
            if state and len(state) > 1:
                operations.append(HumanMessage(content="Updated message", id=state[1].id))
            
            return operations
        
        # Create graph
        graph = MessageGraph()
        graph.add_node("mixed", mixed_operations_node)
        graph.set_entry_point("mixed")
        graph.set_finish_point("mixed")
        app = graph.compile()
        
        # Test with initial messages
        initial_messages = [
            HumanMessage(content="First", id="msg1"),
            HumanMessage(content="Second", id="msg2"),
            AIMessage(content="Third", id="msg3")
        ]
        
        result = app.invoke(initial_messages)
        
        # Should have: updated msg2, unchanged msg3, new new_msg
        assert len(result) == 3
        
        # Find messages by ID
        result_by_id = {msg.id: msg for msg in result}
        
        assert "msg1" not in result_by_id  # Deleted
        assert result_by_id["msg2"].content == "Updated message"  # Updated
        assert result_by_id["msg3"].content == "Third"  # Unchanged
        assert result_by_id["new_msg"].content == "New AI message"  # New


class TestStateGraphWithDeletion:
    """Test message deletion in StateGraph with custom state."""
    
    def test_stategraph_with_message_deletion(self):
        """Test StateGraph with message deletion functionality."""
        class State(TypedDict):
            messages: Annotated[list, add_messages]
            count: int
        
        def delete_and_count(state: State):
            messages = state["messages"]
            operations = []
            
            # Delete messages containing "delete"
            for msg in messages:
                if "delete" in msg.content.lower():
                    operations.append(RemoveMessage(id=msg.id))
            
            # Add a summary message
            operations.append(AIMessage(content=f"Processed {len(messages)} messages", id="summary"))
            
            return {"messages": operations, "count": state.get("count", 0) + 1}
        
        # Create graph
        graph = StateGraph(State)
        graph.add_node("process", delete_and_count)
        graph.set_entry_point("process")
        graph.set_finish_point("process")
        app = graph.compile()
        
        # Test with initial state
        initial_state = {
            "messages": [
                HumanMessage(content="Keep this", id="msg1"),
                HumanMessage(content="Delete this message", id="msg2"),
                AIMessage(content="Also keep", id="msg3")
            ],
            "count": 0
        }
        
        result = app.invoke(initial_state)
        
        # Should have: msg1, msg3, summary (msg2 deleted)
        assert len(result["messages"]) == 3
        assert result["count"] == 1
        
        # Find messages by ID
        result_by_id = {msg.id: msg for msg in result["messages"]}
        
        assert "msg1" in result_by_id
        assert "msg2" not in result_by_id  # Deleted
        assert "msg3" in result_by_id
        assert "summary" in result_by_id


class TestUpdateStateWithDeletion:
    """Test message deletion via update_state method."""
    
    def test_update_state_with_remove_message(self):
        """Test using update_state to delete messages."""
        # Create a simple graph
        def echo_node(state):
            return [AIMessage(content="Echo", id="echo")]
        
        graph = MessageGraph()
        graph.add_node("echo", echo_node)
        graph.set_entry_point("echo")
        graph.set_finish_point("echo")
        app = graph.compile(checkpointer=MemorySaver())
        
        # Initial run
        config = {"configurable": {"thread_id": "test"}}
        initial_messages = [
            HumanMessage(content="Hello", id="msg1"),
            HumanMessage(content="World", id="msg2")
        ]
        
        result = app.invoke(initial_messages, config)
        assert len(result) == 3  # msg1, msg2, echo
        
        # Update state to delete a message
        app.update_state(config, [RemoveMessage(id="msg1")])
        
        # Get current state
        state = app.get_state(config)
        messages = state.values
        
        # msg1 should be deleted
        assert len(messages) == 2
        message_ids = [msg.id for msg in messages]
        assert "msg1" not in message_ids
        assert "msg2" in message_ids
        assert "echo" in message_ids
    
    def test_update_state_mixed_operations(self):
        """Test update_state with mixed add/update/delete operations."""
        # Create a simple graph
        def simple_node(state):
            return []  # No-op node
        
        graph = MessageGraph()
        graph.add_node("simple", simple_node)
        graph.set_entry_point("simple")
        graph.set_finish_point("simple")
        app = graph.compile(checkpointer=MemorySaver())
        
        # Initial run
        config = {"configurable": {"thread_id": "test"}}
        initial_messages = [
            HumanMessage(content="First", id="msg1"),
            HumanMessage(content="Second", id="msg2"),
            AIMessage(content="Third", id="msg3")
        ]
        
        result = app.invoke(initial_messages, config)
        assert len(result) == 3
        
        # Mixed operations: delete msg2, update msg1, add new msg4
        updates = [
            RemoveMessage(id="msg2"),
            HumanMessage(content="First Updated", id="msg1"),
            AIMessage(content="Fourth", id="msg4")
        ]
        app.update_state(config, updates)
        
        # Get current state
        state = app.get_state(config)
        messages = state.values
        
        # Should have: updated msg1, unchanged msg3, new msg4
        assert len(messages) == 3
        
        # Find messages by ID
        result_by_id = {msg.id: msg for msg in messages}
        
        assert result_by_id["msg1"].content == "First Updated"  # Updated
        assert "msg2" not in result_by_id  # Deleted
        assert result_by_id["msg3"].content == "Third"  # Unchanged
        assert result_by_id["msg4"].content == "Fourth"  # New


@pytest.mark.asyncio
class TestAsyncMessageDeletion:
    """Test async message deletion functionality."""
    
    async def test_async_message_graph_deletion(self):
        """Test message deletion in async MessageGraph."""
        async def async_delete_node(state):
            # Delete messages containing "async"
            operations = []
            for msg in state:
                if "async" in msg.content.lower():
                    operations.append(RemoveMessage(id=msg.id))
            
            # Add confirmation message
            operations.append(AIMessage(content="Async processing complete", id="async_result"))
            return operations
        
        # Create graph
        graph = MessageGraph()
        graph.add_node("async_delete", async_delete_node)
        graph.set_entry_point("async_delete")
        graph.set_finish_point("async_delete")
        app = graph.compile()
        
        # Test with initial messages
        initial_messages = [
            HumanMessage(content="Keep this", id="msg1"),
            HumanMessage(content="Delete this async message", id="msg2"),
            AIMessage(content="Also keep", id="msg3")
        ]
        
        result = await app.ainvoke(initial_messages)
        
        # Should have: msg1, msg3, async_result (msg2 deleted)
        assert len(result) == 3
        
        # Find messages by ID
        result_by_id = {msg.id: msg for msg in result}
        
        assert "msg1" in result_by_id
        assert "msg2" not in result_by_id  # Deleted
        assert "msg3" in result_by_id
        assert "async_result" in result_by_id
    
    async def test_async_update_state_deletion(self):
        """Test async update_state with message deletion."""
        # Create a simple async graph
        async def async_echo_node(state):
            return [AIMessage(content="Async Echo", id="async_echo")]
        
        graph = MessageGraph()
        graph.add_node("async_echo", async_echo_node)
        graph.set_entry_point("async_echo")
        graph.set_finish_point("async_echo")
        app = graph.compile(checkpointer=MemorySaver())
        
        # Initial run
        config = {"configurable": {"thread_id": "async_test"}}
        initial_messages = [
            HumanMessage(content="Hello async", id="async_msg1"),
            HumanMessage(content="World async", id="async_msg2")
        ]
        
        result = await app.ainvoke(initial_messages, config)
        assert len(result) == 3  # async_msg1, async_msg2, async_echo
        
        # Update state to delete a message
        await app.aupdate_state(config, [RemoveMessage(id="async_msg1")])
        
        # Get current state
        state = await app.aget_state(config)
        messages = state.values
        
        # async_msg1 should be deleted
        assert len(messages) == 2
        message_ids = [msg.id for msg in messages]
        assert "async_msg1" not in message_ids
        assert "async_msg2" in message_ids
        assert "async_echo" in message_ids


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_message_list_deletion(self):
        """Test deletion from empty message list."""
        left = []
        right = [RemoveMessage(id="nonexistent")]
        result = add_messages(left, right)
        
        assert len(result) == 0
    
    def test_only_remove_messages(self):
        """Test when right contains only RemoveMessage objects."""
        msg1 = HumanMessage(content="Hello", id="msg1")
        msg2 = AIMessage(content="Hi there", id="msg2")
        left = [msg1, msg2]
        
        right = [RemoveMessage(id="msg1"), RemoveMessage(id="msg2")]
        result = add_messages(left, right)
        
        assert len(result) == 0
    
    def test_remove_message_with_none_id(self):
        """Test RemoveMessage with None ID (edge case)."""
        # This should not cause errors, but won't match anything
        msg1 = HumanMessage(content="Hello", id="msg1")
        left = [msg1]
        
        # Create RemoveMessage with None ID (unusual but possible)
        right = [RemoveMessage(id=None)]
        result = add_messages(left, right)
        
        # Should remain unchanged since None won't match "msg1"
        assert len(result) == 1
        assert result[0].id == "msg1"
    
    def test_message_without_id_deletion(self):
        """Test deletion behavior with messages that have auto-generated IDs."""
        # Create messages without explicit IDs (will get auto-generated)
        msg1 = HumanMessage(content="Hello")
        msg2 = AIMessage(content="Hi there")
        left = [msg1, msg2]
        
        # First, let add_messages assign IDs
        result1 = add_messages([], left)
        assert len(result1) == 2
        assert all(msg.id is not None for msg in result1)
        
        # Now try to delete the first message by its auto-generated ID
        first_id = result1[0].id
        right = [RemoveMessage(id=first_id)]
        result2 = add_messages(result1, right)
        
        assert len(result2) == 1
        assert result2[0].id == result1[1].id
