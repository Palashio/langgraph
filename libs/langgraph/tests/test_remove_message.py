"""Tests for RemoveMessage functionality in LangGraph."""
import pytest
from typing import Annotated, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
)

from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages


def test_add_messages_with_remove_message():
    """Test add_messages function handles RemoveMessage correctly."""
    # Test basic removal
    msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2")]
    msgs2 = [RemoveMessage(id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].id == "2"
    assert result[0].content == "Hi"


def test_add_messages_remove_nonexistent_id():
    """Test RemoveMessage with non-existent ID."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="nonexistent")]
    result = add_messages(msgs1, msgs2)
    
    # Should keep original message
    assert len(result) == 1
    assert result[0].id == "1"
    assert result[0].content == "Hello"


def test_add_messages_mixed_operations():
    """Test mixing RemoveMessage with regular messages."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3"),
    ]
    msgs2 = [
        RemoveMessage(id="2"),  # Remove middle message
        AIMessage(content="I'm good, thanks!", id="4"),  # Add new message
        HumanMessage(content="Updated hello", id="1"),  # Update existing message
    ]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 3
    # Check updated message
    updated_msg = next(m for m in result if m.id == "1")
    assert updated_msg.content == "Updated hello"
    # Check removed message is gone
    assert not any(m.id == "2" for m in result)
    # Check new message is added
    new_msg = next(m for m in result if m.id == "4")
    assert new_msg.content == "I'm good, thanks!"


def test_add_messages_remove_multiple():
    """Test removing multiple messages."""
    msgs1 = [
        HumanMessage(content="Msg 1", id="1"),
        AIMessage(content="Msg 2", id="2"),
        HumanMessage(content="Msg 3", id="3"),
        AIMessage(content="Msg 4", id="4"),
    ]
    msgs2 = [RemoveMessage(id="1"), RemoveMessage(id="3")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert {m.id for m in result} == {"2", "4"}


def test_state_graph_with_remove_message():
    """Test RemoveMessage works in a StateGraph."""
    
    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
    
    def add_message(state: State) -> State:
        return {"messages": [AIMessage(content="Added message", id="new")]}
    
    def remove_first_message(state: State) -> State:
        if state["messages"]:
            first_id = state["messages"][0].id
            return {"messages": [RemoveMessage(id=first_id)]}
        return {"messages": []}
    
    builder = StateGraph(State)
    builder.add_node("add", add_message)
    builder.add_node("remove", remove_first_message)
    builder.set_entry_point("add")
    builder.add_edge("add", "remove")
    builder.set_finish_point("remove")
    
    graph = builder.compile()
    
    # Start with initial messages
    initial_state = {
        "messages": [
            HumanMessage(content="Initial message", id="initial")
        ]
    }
    
    result = graph.invoke(initial_state)
    
    # Should have removed the initial message and added the new one
    assert len(result["messages"]) == 1
    assert result["messages"][0].id == "new"
    assert result["messages"][0].content == "Added message"


def test_update_state_with_remove_message():
    """Test using update_state with RemoveMessage."""
    from langgraph.checkpoint.memory import MemorySaver
    
    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
    
    def chatbot(state: State) -> State:
        return {"messages": [AIMessage(content="Hello from bot!")]}
    
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.set_entry_point("chatbot")
    builder.set_finish_point("chatbot")
    
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": "1"}}
    
    # Initial run
    initial_messages = [
        HumanMessage(content="Hello", id="user1"),
        HumanMessage(content="How are you?", id="user2")
    ]
    result = graph.invoke({"messages": initial_messages}, config)
    
    # Should have 3 messages now
    assert len(result["messages"]) == 3
    
    # Remove the first user message using update_state
    removed_id = result["messages"][0].id
    graph.update_state(config, {"messages": [RemoveMessage(id=removed_id)]})
    
    # Get updated state
    state = graph.get_state(config)
    
    # Should now have 2 messages (removed the first one)
    assert len(state.values["messages"]) == 2
    assert not any(m.id == removed_id for m in state.values["messages"])


def test_node_returning_remove_message():
    """Test a node that returns RemoveMessage directly."""
    
    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
    
    def delete_messages_node(state: State) -> dict:
        # Delete the last message if it exists
        if state["messages"]:
            last_msg_id = state["messages"][-1].id
            return {"messages": [RemoveMessage(id=last_msg_id)]}
        return {"messages": []}
    
    builder = StateGraph(State)
    builder.add_node("delete", delete_messages_node)
    builder.set_entry_point("delete")
    builder.set_finish_point("delete")
    
    graph = builder.compile()
    
    initial_state = {
        "messages": [
            HumanMessage(content="Keep this", id="keep"),
            AIMessage(content="Delete this", id="delete_me")
        ]
    }
    
    result = graph.invoke(initial_state)
    
    # Should have only the first message
    assert len(result["messages"]) == 1
    assert result["messages"][0].id == "keep"
    assert result["messages"][0].content == "Keep this"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])