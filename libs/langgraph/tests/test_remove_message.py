"""Tests for RemoveMessage functionality in LangGraph."""

import pytest
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


class TestAddMessagesWithRemoveMessage:
    """Test the add_messages function with RemoveMessage support."""

    def test_basic_message_removal(self):
        """Test basic removal of a message by ID."""
        msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2")]
        msgs2 = [RemoveMessage(id="1")]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 1
        assert result[0].id == "2"
        assert result[0].content == "Hi"

    def test_remove_nonexistent_id(self):
        """Test removing a message with non-existent ID (should not affect anything)."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = [RemoveMessage(id="999")]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 1
        assert result[0].id == "1"
        assert result[0].content == "Hello"

    def test_multiple_remove_messages(self):
        """Test removing multiple messages with multiple RemoveMessage instances."""
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2"),
            HumanMessage(content="Test", id="3"),
            SystemMessage(content="System", id="4")
        ]
        msgs2 = [RemoveMessage(id="1"), RemoveMessage(id="3")]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 2
        result_ids = {m.id for m in result}
        assert "1" not in result_ids
        assert "3" not in result_ids
        assert "2" in result_ids
        assert "4" in result_ids

    def test_mixed_regular_and_remove_messages(self):
        """Test mixing regular messages with RemoveMessage instances."""
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2")
        ]
        msgs2 = [
            AIMessage(content="New message", id="3"),
            RemoveMessage(id="1"),
            HumanMessage(content="Another message", id="4")
        ]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 3
        result_ids = {m.id for m in result}
        assert "1" not in result_ids  # Should be removed
        assert "2" in result_ids      # Should remain
        assert "3" in result_ids      # Should be added
        assert "4" in result_ids      # Should be added

    def test_remove_message_with_replacement(self):
        """Test removing a message that would have been replaced."""
        msgs1 = [HumanMessage(content="Original", id="1")]
        msgs2 = [
            HumanMessage(content="Replacement", id="1"),  # Would replace
            RemoveMessage(id="1")  # But then remove
        ]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 0  # Message should be removed entirely

    def test_backward_compatibility(self):
        """Test that regular message processing still works without RemoveMessage."""
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = [AIMessage(content="Hi there!", id="2")]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 2
        assert result[0].content == "Hello"
        assert result[1].content == "Hi there!"

    def test_message_replacement_still_works(self):
        """Test that message replacement by ID still works."""
        msgs1 = [HumanMessage(content="Original", id="1")]
        msgs2 = [HumanMessage(content="Updated", id="1")]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 1
        assert result[0].content == "Updated"
        assert result[0].id == "1"

    def test_empty_lists(self):
        """Test edge cases with empty lists."""
        # Empty right list
        msgs1 = [HumanMessage(content="Hello", id="1")]
        msgs2 = []
        result = add_messages(msgs1, msgs2)
        assert len(result) == 1
        assert result[0].content == "Hello"

        # Empty left list with RemoveMessage
        msgs1 = []
        msgs2 = [RemoveMessage(id="1")]
        result = add_messages(msgs1, msgs2)
        assert len(result) == 0

    def test_single_message_inputs(self):
        """Test with single message inputs (not lists)."""
        msg1 = HumanMessage(content="Hello", id="1")
        msg2 = RemoveMessage(id="1")
        result = add_messages(msg1, msg2)
        
        assert len(result) == 0  # Message should be removed


class TestMessageGraphWithRemoveMessage:
    """Test RemoveMessage functionality with MessageGraph."""

    def test_node_initiated_deletion(self):
        """Test that nodes can return RemoveMessage to delete messages."""
        def delete_first_message(messages):
            if messages:
                return [RemoveMessage(id=messages[0].id)]
            return []

        graph = MessageGraph()
        graph.add_node("delete_node", delete_first_message)
        graph.set_entry_point("delete_node")
        graph.set_finish_point("delete_node")
        
        compiled_graph = graph.compile()
        
        # Start with some messages
        initial_messages = [
            HumanMessage(content="First", id="1"),
            HumanMessage(content="Second", id="2")
        ]
        
        result = compiled_graph.invoke(initial_messages)
        
        # First message should be removed
        assert len(result) == 1
        assert result[0].content == "Second"
        assert result[0].id == "2"

    def test_node_mixed_add_and_remove(self):
        """Test that nodes can both add new messages and remove existing ones."""
        def process_messages(messages):
            return [
                AIMessage(content="New response", id="new_1"),
                RemoveMessage(id=messages[0].id) if messages else RemoveMessage(id="nonexistent")
            ]

        graph = MessageGraph()
        graph.add_node("process_node", process_messages)
        graph.set_entry_point("process_node")
        graph.set_finish_point("process_node")
        
        compiled_graph = graph.compile()
        
        initial_messages = [
            HumanMessage(content="Remove me", id="remove_me"),
            HumanMessage(content="Keep me", id="keep_me")
        ]
        
        result = compiled_graph.invoke(initial_messages)
        
        # Should have the kept message plus the new message
        assert len(result) == 2
        result_contents = {m.content for m in result}
        assert "Remove me" not in result_contents
        assert "Keep me" in result_contents
        assert "New response" in result_contents


class TestStateGraphWithRemoveMessage:
    """Test RemoveMessage functionality with StateGraph and update_state."""

    def test_user_initiated_deletion_via_update_state(self):
        """Test user-initiated deletion via graph.update_state()."""
        class State(TypedDict):
            messages: Annotated[list, add_messages]

        def chatbot(state: State):
            return {"messages": [AIMessage(content="Hello!")]}

        graph = StateGraph(State)
        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        graph.set_finish_point("chatbot")
        
        checkpointer = MemorySaver()
        compiled_graph = graph.compile(checkpointer=checkpointer)
        
        # Initial run
        config = {"configurable": {"thread_id": "test_thread"}}
        result = compiled_graph.invoke({"messages": []}, config)
        
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Hello!"
        message_id = result["messages"][0].id
        
        # Delete the message via update_state
        compiled_graph.update_state(config, values=[RemoveMessage(id=message_id)])
        
        # Get current state
        current_state = compiled_graph.get_state(config)
        assert len(current_state.values["messages"]) == 0

    def test_update_state_with_mixed_operations(self):
        """Test update_state with both adding and removing messages."""
        class State(TypedDict):
            messages: Annotated[list, add_messages]

        def initial_node(state: State):
            return {"messages": [
                HumanMessage(content="First", id="first"),
                HumanMessage(content="Second", id="second")
            ]}

        graph = StateGraph(State)
        graph.add_node("initial", initial_node)
        graph.set_entry_point("initial")
        graph.set_finish_point("initial")
        
        checkpointer = MemorySaver()
        compiled_graph = graph.compile(checkpointer=checkpointer)
        
        # Initial run
        config = {"configurable": {"thread_id": "test_thread"}}
        result = compiled_graph.invoke({"messages": []}, config)
        
        assert len(result["messages"]) == 2
        
        # Update state: add a new message and remove an existing one
        compiled_graph.update_state(config, values=[
            AIMessage(content="New message", id="new"),
            RemoveMessage(id="first")
        ])
        
        # Get current state
        current_state = compiled_graph.get_state(config)
        messages = current_state.values["messages"]
        
        assert len(messages) == 2
        contents = {m.content for m in messages}
        assert "First" not in contents  # Should be removed
        assert "Second" in contents     # Should remain
        assert "New message" in contents  # Should be added

    def test_remove_nonexistent_message_via_update_state(self):
        """Test removing non-existent message via update_state (should not error)."""
        class State(TypedDict):
            messages: Annotated[list, add_messages]

        def chatbot(state: State):
            return {"messages": [AIMessage(content="Hello!")]}

        graph = StateGraph(State)
        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        graph.set_finish_point("chatbot")
        
        checkpointer = MemorySaver()
        compiled_graph = graph.compile(checkpointer=checkpointer)
        
        # Initial run
        config = {"configurable": {"thread_id": "test_thread"}}
        result = compiled_graph.invoke({"messages": []}, config)
        
        assert len(result["messages"]) == 1
        
        # Try to remove non-existent message (should not error)
        compiled_graph.update_state(config, values=[RemoveMessage(id="nonexistent")])
        
        # Get current state - should be unchanged
        current_state = compiled_graph.get_state(config)
        assert len(current_state.values["messages"]) == 1
        assert current_state.values["messages"][0].content == "Hello!"


class TestRemoveMessageEdgeCases:
    """Test edge cases and error conditions for RemoveMessage."""

    def test_remove_message_without_id(self):
        """Test RemoveMessage behavior when message doesn't have an ID."""
        # This should be handled gracefully by the convert_to_messages process
        msgs1 = [HumanMessage(content="Hello", id="1")]
        remove_msg = RemoveMessage(id="1")
        # Ensure the RemoveMessage has the expected ID
        assert remove_msg.id == "1"
        
        msgs2 = [remove_msg]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 0  # Message should be removed

    def test_multiple_messages_same_id_with_removal(self):
        """Test removal when multiple messages might have the same ID."""
        # This tests the edge case where we might have duplicate IDs
        msgs1 = [
            HumanMessage(content="First", id="same"),
            HumanMessage(content="Second", id="different")
        ]
        msgs2 = [
            HumanMessage(content="Third", id="same"),  # Would replace first
            RemoveMessage(id="same")  # Then remove
        ]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 1
        assert result[0].content == "Second"
        assert result[0].id == "different"

    def test_remove_all_messages(self):
        """Test removing all messages from a list."""
        msgs1 = [
            HumanMessage(content="First", id="1"),
            HumanMessage(content="Second", id="2"),
            HumanMessage(content="Third", id="3")
        ]
        msgs2 = [
            RemoveMessage(id="1"),
            RemoveMessage(id="2"),
            RemoveMessage(id="3")
        ]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 0
