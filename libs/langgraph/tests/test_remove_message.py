"""Tests for RemoveMessage functionality in LangGraph."""

import unittest
from typing import Annotated
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import MessageGraph, RemoveMessage, add_messages, MessagesState
from langgraph.pregel import StateSnapshot


class TestRemoveMessage(unittest.TestCase):
    """Test suite for RemoveMessage functionality."""


    def test_add_messages_with_remove_message(self):
        """Test that add_messages function handles RemoveMessage objects correctly."""
        # Test basic removal
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2"),
            HumanMessage(content="How are you?", id="3")
        ]
        msgs2 = [RemoveMessage(id="2")]
        result = add_messages(msgs1, msgs2)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].content, "Hello")
        self.assertEqual(result[0].id, "1")
        self.assertEqual(result[1].content, "How are you?")
        self.assertEqual(result[1].id, "3")


def test_add_messages_remove_nonexistent():
    """Test removing non-existent message ID."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="999")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].content == "Hello"
    assert result[0].id == "1"


def test_add_messages_multiple_removals():
    """Test multiple message removals in a single operation."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3"),
        AIMessage(content="Fine", id="4")
    ]
    msgs2 = [RemoveMessage(id="2"), RemoveMessage(id="4")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[0].id == "1"
    assert result[1].content == "How are you?"
    assert result[1].id == "3"


def test_add_messages_mixed_operations():
    """Test mixed add and remove operations."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2")
    ]
    msgs2 = [
        RemoveMessage(id="1"),
        AIMessage(content="New message", id="3"),
        HumanMessage(content="Updated", id="2")  # This should replace existing id="2"
    ]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Updated"  # Replaced message with id="2"
    assert result[0].id == "2"
    assert result[1].content == "New message"  # New message with id="3"
    assert result[1].id == "3"


def test_add_messages_backward_compatibility():
    """Test that existing message merging and replacement behavior remains unchanged."""
    # Test basic appending
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [AIMessage(content="Hi there!", id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "Hi there!"
    
    # Test replacement by ID
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [HumanMessage(content="Hello again", id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].content == "Hello again"
    assert result[0].id == "1"


def test_remove_message_class():
    """Test RemoveMessage class methods."""
    rm1 = RemoveMessage(id="test")
    rm2 = RemoveMessage(id="test")
    rm3 = RemoveMessage(id="other")
    
    assert rm1 == rm2
    assert rm1 != rm3
    assert str(rm1) == "RemoveMessage(id='test')"
    assert rm1.id == "test"


def test_message_deletion_via_update_state():
    """Test message deletion via update_state() with RemoveMessage objects."""
    checkpointer = MemorySaver()
    
    class State(MessagesState):
        pass
    
    def add_message(state: State):
        return {"messages": [AIMessage(content="Hello", id="ai1")]}
    
    builder = StateGraph(State)
    builder.add_node("add_message", add_message)
    builder.set_entry_point("add_message")
    builder.set_finish_point("add_message")
    
    app = builder.compile(checkpointer=checkpointer)
    
    # Initial run
    config = {"configurable": {"thread_id": "test"}}
    result = app.invoke({"messages": [HumanMessage(content="Hi", id="human1")]}, config)
    
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "Hi"
    assert result["messages"][1].content == "Hello"
    
    # Remove the AI message via update_state
    app.update_state(config, {"messages": [RemoveMessage(id="ai1")]})
    
    # Check that the message was removed
    state = app.get_state(config)
    assert len(state.values["messages"]) == 1
    assert state.values["messages"][0].content == "Hi"
    assert state.values["messages"][0].id == "human1"


def test_message_deletion_in_node_functions():
    """Test message deletion in node functions that return RemoveMessage objects."""
    checkpointer = MemorySaver()
    
    class State(MessagesState):
        pass
    
    def add_messages_node(state: State):
        return {
            "messages": [
                AIMessage(content="Message 1", id="ai1"),
                AIMessage(content="Message 2", id="ai2")
            ]
        }
    
    def delete_first_message(state: State):
        # Delete the first AI message
        return {"messages": [RemoveMessage(id="ai1")]}
    
    builder = StateGraph(State)
    builder.add_node("add_messages", add_messages_node)
    builder.add_node("delete_message", delete_first_message)
    builder.set_entry_point("add_messages")
    builder.add_edge("add_messages", "delete_message")
    builder.set_finish_point("delete_message")
    
    app = builder.compile(checkpointer=checkpointer)
    
    # Run the graph
    config = {"configurable": {"thread_id": "test"}}
    result = app.invoke({"messages": [HumanMessage(content="Hi", id="human1")]}, config)
    
    # Should have human message and only the second AI message
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "Hi"
    assert result["messages"][0].id == "human1"
    assert result["messages"][1].content == "Message 2"
    assert result["messages"][1].id == "ai2"


def test_message_graph_with_remove_message():
    """Test MessageGraph with RemoveMessage functionality."""
    checkpointer = MemorySaver()
    
    def add_ai_message(messages):
        return [AIMessage(content="AI response", id="ai1")]
    
    def delete_human_message(messages):
        # Find and delete the first human message
        for msg in messages:
            if isinstance(msg, HumanMessage):
                return [RemoveMessage(id=msg.id)]
        return []
    
    builder = MessageGraph()
    builder.add_node("ai_responder", add_ai_message)
    builder.add_node("delete_human", delete_human_message)
    builder.set_entry_point("ai_responder")
    builder.add_edge("ai_responder", "delete_human")
    builder.set_finish_point("delete_human")
    
    app = builder.compile(checkpointer=checkpointer)
    
    # Run with initial human message
    config = {"configurable": {"thread_id": "test"}}
    result = app.invoke([HumanMessage(content="Hello", id="human1")], config)
    
    # Should only have the AI message, human message should be deleted
    assert len(result) == 1
    assert result[0].content == "AI response"
    assert result[0].id == "ai1"


def test_edge_case_remove_all_messages():
    """Test edge case where all messages are removed."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2")
    ]
    msgs2 = [RemoveMessage(id="1"), RemoveMessage(id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 0
    assert result == []


def test_edge_case_empty_message_list():
    """Test edge case with empty message list."""
    msgs1 = []
    msgs2 = [RemoveMessage(id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 0
    assert result == []


def test_complex_mixed_operations():
    """Test complex scenario with multiple mixed operations."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3"),
        AIMessage(content="Fine", id="4")
    ]
    msgs2 = [
        RemoveMessage(id="2"),  # Remove AI message
        HumanMessage(content="Updated hello", id="1"),  # Replace human message
        RemoveMessage(id="4"),  # Remove another AI message
        AIMessage(content="New AI message", id="5")  # Add new AI message
    ]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 3
    assert result[0].content == "Updated hello"  # Replaced
    assert result[0].id == "1"
    assert result[1].content == "How are you?"  # Unchanged
    assert result[1].id == "3"
    assert result[2].content == "New AI message"  # Added
    assert result[2].id == "5"


def test_remove_message_with_state_snapshot():
    """Test RemoveMessage works correctly with state snapshots."""
    checkpointer = MemorySaver()
    
    class State(MessagesState):
        pass
    
    def add_message(state: State):
        return {"messages": [AIMessage(content="Hello", id="ai1")]}
    
    builder = StateGraph(State)
    builder.add_node("add_message", add_message)
    builder.set_entry_point("add_message")
    builder.set_finish_point("add_message")
    
    app = builder.compile(checkpointer=checkpointer)
    
    # Initial run
    config = {"configurable": {"thread_id": "test"}}
    app.invoke({"messages": [HumanMessage(content="Hi", id="human1")]}, config)
    
    # Get state before deletion
    state_before = app.get_state(config)
    assert len(state_before.values["messages"]) == 2
    
    # Remove message
    updated_config = app.update_state(config, {"messages": [RemoveMessage(id="ai1")]})
    
    # Get state after deletion
    state_after = app.get_state(config)
    assert len(state_after.values["messages"]) == 1
    assert state_after.values["messages"][0].id == "human1"
    
    # Verify the state snapshot structure
    assert isinstance(state_after, StateSnapshot)
    assert state_after.config == updated_config
    assert "source" in state_after.metadata
    assert state_after.metadata["source"] == "update"


