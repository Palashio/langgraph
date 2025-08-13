"""Tests for RemoveMessage functionality in LangGraph."""

import pytest
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import MessageGraph, RemoveMessage, add_messages
from langgraph.graph.state import StateGraph


def test_remove_message_basic_functionality():
    """Test basic RemoveMessage functionality with add_messages reducer."""
    # Test basic message removal
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi there!", id="2"),
        HumanMessage(content="How are you?", id="3")
    ]
    remove_msgs = [RemoveMessage(id="2")]
    
    result = add_messages(msgs1, remove_msgs)
    
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[0].content == "Hello"
    assert result[1].id == "3"
    assert result[1].content == "How are you?"
    
    # Test removing non-existent message ID (should not affect result)
    remove_msgs = [RemoveMessage(id="non-existent")]
    result = add_messages(msgs1, remove_msgs)
    assert len(result) == 3  # No messages should be removed
    
    # Test removing multiple messages
    remove_msgs = [RemoveMessage(id="1"), RemoveMessage(id="3")]
    result = add_messages(msgs1, remove_msgs)
    assert len(result) == 1
    assert result[0].id == "2"
    assert result[0].content == "Hi there!"


def test_remove_message_mixed_operations():
    """Test mixed operations with both regular messages and RemoveMessage objects."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi there!", id="2")
    ]
    
    # Mix of regular messages and remove messages
    mixed_msgs = [
        RemoveMessage(id="1"),  # Remove first message
        HumanMessage(content="New message", id="3"),  # Add new message
        AIMessage(content="Updated response", id="2")  # Update existing message
    ]
    
    result = add_messages(msgs1, mixed_msgs)
    
    assert len(result) == 2
    # Message with id="1" should be removed
    # Message with id="2" should be updated
    # Message with id="3" should be added
    assert result[0].id == "2"
    assert result[0].content == "Updated response"
    assert result[1].id == "3"
    assert result[1].content == "New message"


def test_remove_message_with_state_graph():
    """Test RemoveMessage functionality with StateGraph and update_state."""
    class State(TypedDict):
        messages: Annotated[list, add_messages]
    
    def chatbot(state: State) -> State:
        return {"messages": [AIMessage(content="Hello from bot!", id="bot-1")]}
    
    # Create graph with checkpointer for update_state functionality
    checkpointer = MemorySaver()
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.set_entry_point("chatbot")
    builder.set_finish_point("chatbot")
    graph = builder.compile(checkpointer=checkpointer)
    
    # Initial run
    config = {"configurable": {"thread_id": "test-thread"}}
    initial_state = {"messages": [HumanMessage(content="Hi", id="user-1")]}
    result = graph.invoke(initial_state, config)
    
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "Hi"
    assert result["messages"][1].content == "Hello from bot!"
    
    # Use update_state to remove a message
    graph.update_state(config, {"messages": [RemoveMessage(id="user-1")]})
    
    # Get updated state
    updated_state = graph.get_state(config)
    assert len(updated_state.values["messages"]) == 1
    assert updated_state.values["messages"][0].content == "Hello from bot!"
    assert updated_state.values["messages"][0].id == "bot-1"


def test_remove_message_with_message_graph():
    """Test RemoveMessage functionality with MessageGraph."""
    def chatbot(messages):
        return [AIMessage(content="Hello from message graph!", id="msg-bot-1")]
    
    def delete_messages(messages):
        # Delete the last message if it exists
        if messages:
            return [RemoveMessage(id=messages[-1].id)]
        return []
    
    # Create MessageGraph with checkpointer
    checkpointer = MemorySaver()
    builder = MessageGraph()
    builder.add_node("chatbot", chatbot)
    builder.add_node("delete_messages", delete_messages)
    builder.set_entry_point("chatbot")
    builder.add_edge("chatbot", "delete_messages")
    builder.set_finish_point("delete_messages")
    graph = builder.compile(checkpointer=checkpointer)
    
    # Initial run
    config = {"configurable": {"thread_id": "test-thread-msg"}}
    initial_messages = [HumanMessage(content="Hi there", id="user-msg-1")]
    result = graph.invoke(initial_messages, config)
    
    # The chatbot should add a message, then delete_messages should remove the last one
    # So we should end up with just the user message
    assert len(result) == 1
    assert result[0].content == "Hi there"
    assert result[0].id == "user-msg-1"


def test_remove_message_node_based_deletion():
    """Test node-based message deletion using lambda functions."""
    class State(TypedDict):
        messages: Annotated[list, add_messages]
    
    # Create graph with node that deletes messages
    checkpointer = MemorySaver()
    builder = StateGraph(State)
    
    # Node that adds a message
    builder.add_node("add_message", lambda state: {
        "messages": [AIMessage(content="Added message", id="added-1")]
    })
    
    # Node that deletes the last message using lambda
    builder.add_node("delete_last", lambda state: {
        "messages": [RemoveMessage(id=state["messages"][-1].id)] if state["messages"] else []
    })
    
    builder.set_entry_point("add_message")
    builder.add_edge("add_message", "delete_last")
    builder.set_finish_point("delete_last")
    graph = builder.compile(checkpointer=checkpointer)
    
    # Initial run
    config = {"configurable": {"thread_id": "test-node-deletion"}}
    initial_state = {
        "messages": [
            HumanMessage(content="First", id="first-1"),
            HumanMessage(content="Second", id="second-1")
        ]
    }
    result = graph.invoke(initial_state, config)
    
    # Should have: first message, added message (second message deleted by delete_last node)
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "First"
    assert result["messages"][1].content == "Added message"


def test_remove_message_edge_cases():
    """Test edge cases for RemoveMessage functionality."""
    # Test with empty left list
    result = add_messages([], [RemoveMessage(id="non-existent")])
    assert result == []
    
    # Test with empty right list
    msgs = [HumanMessage(content="Hello", id="1")]
    result = add_messages(msgs, [])
    assert len(result) == 1
    assert result[0].content == "Hello"
    
    # Test removing all messages
    msgs = [
        HumanMessage(content="First", id="1"),
        AIMessage(content="Second", id="2")
    ]
    remove_all = [RemoveMessage(id="1"), RemoveMessage(id="2")]
    result = add_messages(msgs, remove_all)
    assert result == []
    
    # Test single message (not list) with RemoveMessage
    single_msg = HumanMessage(content="Single", id="single-1")
    result = add_messages(single_msg, RemoveMessage(id="single-1"))
    assert result == []
    
    # Test single message with non-matching RemoveMessage
    result = add_messages(single_msg, RemoveMessage(id="different-id"))
    assert len(result) == 1
    assert result[0].content == "Single"


def test_remove_message_class_properties():
    """Test RemoveMessage class properties and methods."""
    # Test initialization
    rm1 = RemoveMessage(id="test-id")
    assert rm1.id == "test-id"
    
    # Test string representation
    assert repr(rm1) == "RemoveMessage(id='test-id')"
    
    # Test equality
    rm2 = RemoveMessage(id="test-id")
    rm3 = RemoveMessage(id="different-id")
    
    assert rm1 == rm2
    assert rm1 != rm3
    assert rm1 != "not-a-remove-message"
    
    # Test that id is required as keyword argument
    with pytest.raises(TypeError):
        RemoveMessage("test-id")  # Should fail - positional arg not allowed


def test_remove_message_integration_with_update_state():
    """Test comprehensive integration of RemoveMessage with update_state method."""
    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
    
    def echo_bot(state: State) -> State:
        last_message = state["messages"][-1] if state["messages"] else None
        if last_message and hasattr(last_message, 'content'):
            return {"messages": [AIMessage(content=f"Echo: {last_message.content}", id="echo-bot")]}
        return {"messages": []}
    
    # Create graph with checkpointer
    checkpointer = MemorySaver()
    builder = StateGraph(State)
    builder.add_node("echo_bot", echo_bot)
    builder.set_entry_point("echo_bot")
    builder.set_finish_point("echo_bot")
    graph = builder.compile(checkpointer=checkpointer)
    
    # Initial conversation
    config = {"configurable": {"thread_id": "integration-test"}}
    initial_state = {"messages": [HumanMessage(content="Hello", id="user-1")]}
    result = graph.invoke(initial_state, config)
    
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "Hello"
    assert result["messages"][1].content == "Echo: Hello"
    
    # Add another user message via update_state
    graph.update_state(config, {"messages": [HumanMessage(content="How are you?", id="user-2")]})
    
    # Run the graph again
    result = graph.invoke(None, config)
    assert len(result["messages"]) == 4  # user-1, echo-bot, user-2, new echo-bot
    
    # Remove the first user message and one of the bot responses
    graph.update_state(config, {"messages": [
        RemoveMessage(id="user-1"),
        RemoveMessage(id="echo-bot")
    ]})
    
    # Check final state
    final_state = graph.get_state(config)
    assert len(final_state.values["messages"]) == 2
    # Should have user-2 and the latest echo-bot response
    assert any(msg.content == "How are you?" for msg in final_state.values["messages"])
    assert any("Echo:" in msg.content for msg in final_state.values["messages"])


def test_remove_message_with_message_ids_auto_generation():
    """Test RemoveMessage works correctly when message IDs are auto-generated."""
    # Test with messages that don't have IDs initially
    msgs_without_ids = [
        HumanMessage(content="Hello"),  # No ID provided
        AIMessage(content="Hi there!")  # No ID provided
    ]
    
    # Process through add_messages to get auto-generated IDs
    processed_msgs = add_messages([], msgs_without_ids)
    assert len(processed_msgs) == 2
    assert processed_msgs[0].id is not None
    assert processed_msgs[1].id is not None
    
    # Now remove one of them using the auto-generated ID
    first_msg_id = processed_msgs[0].id
    result = add_messages(processed_msgs, [RemoveMessage(id=first_msg_id)])
    
    assert len(result) == 1
    assert result[0].content == "Hi there!"
    assert result[0].id == processed_msgs[1].id


def test_remove_message_preserves_message_order():
    """Test that RemoveMessage preserves the order of remaining messages."""
    msgs = [
        HumanMessage(content="First", id="1"),
        AIMessage(content="Second", id="2"),
        HumanMessage(content="Third", id="3"),
        AIMessage(content="Fourth", id="4"),
        HumanMessage(content="Fifth", id="5")
    ]
    
    # Remove messages 2 and 4
    remove_msgs = [RemoveMessage(id="2"), RemoveMessage(id="4")]
    result = add_messages(msgs, remove_msgs)
    
    assert len(result) == 3
    assert result[0].content == "First"
    assert result[0].id == "1"
    assert result[1].content == "Third"
    assert result[1].id == "3"
    assert result[2].content == "Fifth"
    assert result[2].id == "5"
