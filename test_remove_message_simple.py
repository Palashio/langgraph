#!/usr/bin/env python3
"""Comprehensive tests for RemoveMessage functionality in LangGraph."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import MessageGraph, RemoveMessage, add_messages, MessagesState


def test_add_messages_with_remove_message():
    """Test that add_messages function handles RemoveMessage objects correctly."""
    print("Testing basic RemoveMessage functionality...")
    
    # Test basic removal
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3")
    ]
    msgs2 = [RemoveMessage(id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[0].id == "1"
    assert result[1].content == "How are you?"
    assert result[1].id == "3"
    print("✓ Basic RemoveMessage functionality works")


def test_add_messages_remove_nonexistent():
    """Test removing non-existent message ID."""
    print("Testing removal of non-existent message ID...")
    
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="999")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].content == "Hello"
    assert result[0].id == "1"
    print("✓ Removing non-existent ID works correctly")


def test_add_messages_multiple_removals():
    """Test multiple message removals in a single operation."""
    print("Testing multiple message removals...")
    
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
    print("✓ Multiple message removals work correctly")


def test_add_messages_mixed_operations():
    """Test mixed add and remove operations."""
    print("Testing mixed add and remove operations...")
    
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
    print("✓ Mixed operations work correctly")


def test_add_messages_backward_compatibility():
    """Test that existing message merging and replacement behavior remains unchanged."""
    print("Testing backward compatibility...")
    
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
    print("✓ Backward compatibility maintained")


def test_remove_message_class():
    """Test RemoveMessage class methods."""
    print("Testing RemoveMessage class...")
    
    rm1 = RemoveMessage(id="test")
    rm2 = RemoveMessage(id="test")
    rm3 = RemoveMessage(id="other")
    
    assert rm1 == rm2
    assert rm1 != rm3
    assert str(rm1) == "RemoveMessage(id='test')"
    assert rm1.id == "test"
    print("✓ RemoveMessage class methods work correctly")


def test_message_deletion_via_update_state():
    """Test message deletion via update_state() with RemoveMessage objects."""
    print("Testing message deletion via update_state()...")
    
    checkpointer = MemorySaver()
    
    class State(MessagesState):
        pass
    
    def add_message(state):
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
    print("✓ Message deletion via update_state() works correctly")


def test_message_deletion_in_node_functions():
    """Test message deletion in node functions that return RemoveMessage objects."""
    print("Testing message deletion in node functions...")
    
    checkpointer = MemorySaver()
    
    class State(MessagesState):
        pass
    
    def add_messages_node(state):
        return {
            "messages": [
                AIMessage(content="Message 1", id="ai1"),
                AIMessage(content="Message 2", id="ai2")
            ]
        }
    
    def delete_first_message(state):
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
    print("✓ Message deletion in node functions works correctly")


def test_message_graph_with_remove_message():
    """Test MessageGraph with RemoveMessage functionality."""
    print("Testing MessageGraph with RemoveMessage...")
    
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
    print("✓ MessageGraph with RemoveMessage works correctly")


def test_edge_cases():
    """Test edge cases."""
    print("Testing edge cases...")
    
    # Test removing all messages
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2")
    ]
    msgs2 = [RemoveMessage(id="1"), RemoveMessage(id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 0
    assert result == []
    
    # Test with empty message list
    msgs1 = []
    msgs2 = [RemoveMessage(id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 0
    assert result == []
    print("✓ Edge cases handled correctly")


if __name__ == "__main__":
    print("Running comprehensive RemoveMessage tests...\n")
    
    try:
        test_add_messages_with_remove_message()
        test_add_messages_remove_nonexistent()
        test_add_messages_multiple_removals()
        test_add_messages_mixed_operations()
        test_add_messages_backward_compatibility()
        test_remove_message_class()
        test_message_deletion_via_update_state()
        test_message_deletion_in_node_functions()
        test_message_graph_with_remove_message()
        test_edge_cases()
        
        print("\n✅ All comprehensive RemoveMessage tests passed!")
        print("\nTest Coverage Summary:")
        print("✓ Message deletion via update_state() with RemoveMessage objects")
        print("✓ Message deletion in node functions that return RemoveMessage objects")
        print("✓ Edge cases like attempting to remove non-existent message IDs")
        print("✓ Multiple message removals in a single operation")
        print("✓ Mixed operations with both regular messages and RemoveMessage objects")
        print("✓ Existing message merging and replacement behavior remains unchanged")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
