"""Tests for message deletion functionality using RemoveMessage."""

from typing import Annotated, TypedDict

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import MessageGraph, MessagesState, add_messages
from langgraph.graph.state import StateGraph


class TestAddMessagesFunction:
    """Test the add_messages function with RemoveMessage objects."""

    def test_basic_message_addition(self):
        """Test that basic message addition still works."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = [AIMessage(content="Hi there!", id="2")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "2"
        assert result[0].content == "Hello"
        assert result[1].content == "Hi there!"

    def test_message_update_by_id(self):
        """Test that message updates by ID still work."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = [HumanMessage(content="Hello again", id="1")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].content == "Hello again"

    def test_single_message_removal(self):
        """Test removing a single message by ID."""
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2"),
            HumanMessage(content="How are you?", id="3"),
        ]
        msgs2 = [RemoveMessage(id="2")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "3"
        assert not any(m.id == "2" for m in result)

    def test_multiple_message_removal(self):
        """Test removing multiple messages by ID."""
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2"),
            HumanMessage(content="How are you?", id="3"),
            AIMessage(content="I'm good", id="4"),
        ]
        msgs2 = [RemoveMessage(id="2"), RemoveMessage(id="4")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "3"
        assert not any(m.id in ["2", "4"] for m in result)

    def test_mixed_operations(self):
        """Test mixed operations: remove, add, and update messages."""
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2"),
            HumanMessage(content="How are you?", id="3"),
        ]
        msgs2 = [
            RemoveMessage(id="2"),  # Remove message with id="2"
            AIMessage(content="I'm good!", id="4"),  # Add new message
            HumanMessage(content="Updated hello", id="1"),  # Update existing message
        ]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 3
        # Check that message with id="2" was removed
        assert not any(m.id == "2" for m in result)
        # Check that message with id="1" was updated
        updated_msg = next(m for m in result if m.id == "1")
        assert updated_msg.content == "Updated hello"
        # Check that new message with id="4" was added
        assert any(m.id == "4" for m in result)
        # Check that message with id="3" remains unchanged
        unchanged_msg = next(m for m in result if m.id == "3")
        assert unchanged_msg.content == "How are you?"

    def test_remove_nonexistent_message(self):
        """Test removing a message that doesn't exist (should be graceful)."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = [RemoveMessage(id="999")]  # ID that doesn't exist
        result = add_messages(msgs1, msgs2)

        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].content == "Hello"

    def test_remove_all_messages(self):
        """Test removing all messages."""
        msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2")]
        msgs2 = [RemoveMessage(id="1"), RemoveMessage(id="2")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 0

    def test_empty_lists(self):
        """Test with empty message lists."""
        result = add_messages([], [])
        assert len(result) == 0

        msgs1 = [HumanMessage(content="Hello", id="1")]
        result = add_messages(msgs1, [])
        assert len(result) == 1
        assert result[0].id == "1"

        msgs2 = [AIMessage(content="Hi", id="2")]
        result = add_messages([], msgs2)
        assert len(result) == 1
        assert result[0].id == "2"

    def test_single_message_inputs(self):
        """Test with single message inputs (not lists)."""
        msg1 = HumanMessage(content="Hello", id="1")
        msg2 = RemoveMessage(id="1")
        result = add_messages(msg1, msg2)

        assert len(result) == 0

    def test_different_message_types(self):
        """Test removal with different message types."""
        msgs1 = [
            SystemMessage(content="System", id="1"),
            HumanMessage(content="Human", id="2"),
            AIMessage(content="AI", id="3"),
            ToolMessage(content="Tool", tool_call_id="call_1", id="4"),
        ]
        msgs2 = [RemoveMessage(id="2"), RemoveMessage(id="4")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "3"
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], AIMessage)


class TestMessageGraphIntegration:
    """Test message deletion with MessageGraph."""

    def test_message_graph_with_removal(self):
        """Test MessageGraph with node that removes messages."""

        def chatbot(messages):
            return [AIMessage(content="Hello!", id="ai-1")]

        def delete_first(messages):
            if messages:
                return [RemoveMessage(id=messages[0].id)]
            return []

        builder = MessageGraph()
        builder.add_node("chatbot", chatbot)
        builder.add_node("delete_first", delete_first)
        builder.set_entry_point("chatbot")
        builder.add_edge("chatbot", "delete_first")
        builder.set_finish_point("delete_first")

        graph = builder.compile()

        initial_messages = [HumanMessage(content="Hi there", id="human-1")]
        result = graph.invoke(initial_messages)

        # The first message (human-1) should be removed, only AI message remains
        assert len(result) == 1
        assert result[0].id == "ai-1"
        assert result[0].content == "Hello!"

    def test_message_graph_mixed_operations(self):
        """Test MessageGraph with mixed add/remove operations."""

        def process_messages(messages):
            return [
                AIMessage(content="Processing...", id="ai-process"),
                RemoveMessage(id=messages[-1].id) if messages else None,
            ]

        builder = MessageGraph()
        builder.add_node(
            "processor",
            lambda msgs: [m for m in process_messages(msgs) if m is not None],
        )
        builder.set_entry_point("processor")
        builder.set_finish_point("processor")

        graph = builder.compile()

        initial_messages = [
            HumanMessage(content="First", id="1"),
            HumanMessage(content="Second", id="2"),
        ]
        result = graph.invoke(initial_messages)

        # Should have first message + new AI message, second message removed
        assert len(result) == 2
        assert result[0].id == "1"
        assert result[1].id == "ai-process"
        assert not any(m.id == "2" for m in result)


class TestStateGraphIntegration:
    """Test message deletion with StateGraph and update_state."""

    def test_state_graph_with_messages_state(self):
        """Test StateGraph with MessagesState and message removal."""

        def chatbot(state: MessagesState):
            return {"messages": [AIMessage(content="Hello!", id="ai-1")]}

        builder = StateGraph(MessagesState)
        builder.add_node("chatbot", chatbot)
        builder.set_entry_point("chatbot")
        builder.set_finish_point("chatbot")

        graph = builder.compile()

        initial_state = {"messages": [HumanMessage(content="Hi", id="human-1")]}
        result = graph.invoke(initial_state)

        assert len(result["messages"]) == 2
        assert result["messages"][0].id == "human-1"
        assert result["messages"][1].id == "ai-1"

    def test_update_state_with_remove_message(self):
        """Test user-initiated deletion via graph.update_state()."""

        def chatbot(state: MessagesState):
            return {"messages": [AIMessage(content="Hello!", id="ai-1")]}

        builder = StateGraph(MessagesState)
        builder.add_node("chatbot", chatbot)
        builder.set_entry_point("chatbot")
        builder.set_finish_point("chatbot")

        checkpointer = MemorySaver()
        graph = builder.compile(checkpointer=checkpointer)

        # Initial run
        config = {"configurable": {"thread_id": "test-thread"}}
        initial_state = {"messages": [HumanMessage(content="Hi", id="human-1")]}
        result = graph.invoke(initial_state, config=config)

        assert len(result["messages"]) == 2

        # Update state to remove the human message
        graph.update_state(config, values={"messages": [RemoveMessage(id="human-1")]})

        # Get current state
        current_state = graph.get_state(config)
        messages = current_state.values["messages"]

        # Should only have the AI message now
        assert len(messages) == 1
        assert messages[0].id == "ai-1"
        assert not any(m.id == "human-1" for m in messages)

    def test_node_based_deletion(self):
        """Test node-based deletion via lambda function."""

        def chatbot(state: MessagesState):
            return {"messages": [AIMessage(content="Hello!", id="ai-1")]}

        def delete_messages(state: MessagesState):
            # Delete the last message
            if state["messages"]:
                return {"messages": [RemoveMessage(id=state["messages"][-1].id)]}
            return {"messages": []}

        builder = StateGraph(MessagesState)
        builder.add_node("chatbot", chatbot)
        builder.add_node("delete_messages", delete_messages)
        builder.set_entry_point("chatbot")
        builder.add_edge("chatbot", "delete_messages")
        builder.set_finish_point("delete_messages")

        graph = builder.compile()

        initial_state = {"messages": [HumanMessage(content="Hi", id="human-1")]}
        result = graph.invoke(initial_state)

        # The AI message (last one) should be removed, only human message remains
        assert len(result["messages"]) == 1
        assert result["messages"][0].id == "human-1"
        assert not any(m.id == "ai-1" for m in result["messages"])

    def test_custom_state_with_messages(self):
        """Test custom state schema with messages and RemoveMessage."""

        class CustomState(TypedDict):
            messages: Annotated[list, add_messages]
            counter: int

        def increment_and_remove(state: CustomState):
            # Increment counter and remove first message if exists
            messages_to_add = []
            if state["messages"]:
                messages_to_add.append(RemoveMessage(id=state["messages"][0].id))

            return {"messages": messages_to_add, "counter": state["counter"] + 1}

        builder = StateGraph(CustomState)
        builder.add_node("increment_and_remove", increment_and_remove)
        builder.set_entry_point("increment_and_remove")
        builder.set_finish_point("increment_and_remove")

        graph = builder.compile()

        initial_state = {
            "messages": [
                HumanMessage(content="First", id="1"),
                HumanMessage(content="Second", id="2"),
            ],
            "counter": 0,
        }
        result = graph.invoke(initial_state)

        # Counter should be incremented, first message should be removed
        assert result["counter"] == 1
        assert len(result["messages"]) == 1
        assert result["messages"][0].id == "2"
        assert not any(m.id == "1" for m in result["messages"])


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_remove_message_without_id(self):
        """Test RemoveMessage behavior when message doesn't have ID."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        # RemoveMessage should always have an ID, but test graceful handling
        msgs2 = [RemoveMessage(id=None)]
        result = add_messages(msgs1, msgs2)

        # Should not remove anything since RemoveMessage has no ID
        assert len(result) == 1
        assert result[0].id == "1"

    def test_concurrent_add_and_remove_same_id(self):
        """Test adding and removing message with same ID in same operation."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = [RemoveMessage(id="1"), AIMessage(content="New message", id="1")]
        result = add_messages(msgs1, msgs2)

        # The remove should happen first, then add
        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].content == "New message"
        assert isinstance(result[0], AIMessage)

    def test_remove_message_preserves_order(self):
        """Test that removing messages preserves the order of remaining messages."""
        msgs1 = [
            HumanMessage(content="First", id="1"),
            AIMessage(content="Second", id="2"),
            HumanMessage(content="Third", id="3"),
            AIMessage(content="Fourth", id="4"),
            HumanMessage(content="Fifth", id="5"),
        ]
        msgs2 = [RemoveMessage(id="2"), RemoveMessage(id="4")]
        result = add_messages(msgs1, msgs2)

        assert len(result) == 3
        assert result[0].content == "First"
        assert result[1].content == "Third"
        assert result[2].content == "Fifth"
        # Verify order is preserved
        assert [m.id for m in result] == ["1", "3", "5"]


class TestBackwardCompatibility:
    """Test that existing functionality remains unchanged."""

    def test_existing_message_handling_unchanged(self):
        """Test that all existing message handling patterns still work."""
        # Test basic append
        result = add_messages(
            [HumanMessage(content="Hello", id="1")], [AIMessage(content="Hi", id="2")]
        )
        assert len(result) == 2

        # Test message update
        result = add_messages(
            [HumanMessage(content="Hello", id="1")],
            [HumanMessage(content="Updated", id="1")],
        )
        assert len(result) == 1
        assert result[0].content == "Updated"

        # Test with message-like representations
        result = add_messages([("human", "Hello")], [("ai", "Hi")])
        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "Hi"

    def test_message_graph_backward_compatibility(self):
        """Test that MessageGraph still works as before."""

        def chatbot(messages):
            return [AIMessage(content="Hello!")]

        builder = MessageGraph()
        builder.add_node("chatbot", chatbot)
        builder.set_entry_point("chatbot")
        builder.set_finish_point("chatbot")

        graph = builder.compile()
        result = graph.invoke([HumanMessage(content="Hi")])

        assert len(result) == 2  # Original + new message
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)

    def test_messages_state_backward_compatibility(self):
        """Test that MessagesState still works as before."""

        def chatbot(state: MessagesState):
            return {"messages": [AIMessage(content="Hello!")]}

        builder = StateGraph(MessagesState)
        builder.add_node("chatbot", chatbot)
        builder.set_entry_point("chatbot")
        builder.set_finish_point("chatbot")

        graph = builder.compile()
        result = graph.invoke({"messages": [HumanMessage(content="Hi")]})

        assert len(result["messages"]) == 2
        assert isinstance(result["messages"][0], HumanMessage)
        assert isinstance(result["messages"][1], AIMessage)
