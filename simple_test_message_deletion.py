#!/usr/bin/env python3
"""Simple test to verify message deletion functionality works."""

import sys
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from langgraph.graph.message import add_messages, MessageGraph, MessagesState
from langgraph.graph.state import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import Annotated, TypedDict

def test_add_messages_basic():
    """Test basic add_messages functionality with RemoveMessage."""
    print("Testing add_messages with RemoveMessage...")
    
    # Test basic removal
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3")
    ]
    msgs2 = [RemoveMessage(id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "3"
    assert not any(m.id == "2" for m in result)
    print("✅ Basic removal works")
    
    # Test mixed operations
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2")
    ]
    msgs2 = [
        RemoveMessage(id="1"),
        AIMessage(content="New message", id="3"),
        HumanMessage(content="Updated", id="2")
    ]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert not any(m.id == "1" for m in result)
    assert any(m.id == "2" and m.content == "Updated" for m in result)
    assert any(m.id == "3" for m in result)
    print("✅ Mixed operations work")

def test_message_graph():
    """Test MessageGraph with RemoveMessage."""
    print("Testing MessageGraph with RemoveMessage...")
    
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
    print("✅ MessageGraph with RemoveMessage works")

def test_state_graph_update_state():
    """Test StateGraph with update_state and RemoveMessage."""
    print("Testing StateGraph update_state with RemoveMessage...")
    
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
    print("✅ StateGraph update_state with RemoveMessage works")

def test_node_based_deletion():
    """Test node-based deletion."""
    print("Testing node-based deletion...")
    
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
    print("✅ Node-based deletion works")

def test_backward_compatibility():
    """Test that existing functionality still works."""
    print("Testing backward compatibility...")
    
    # Test basic message handling still works
    result = add_messages(
        [HumanMessage(content="Hello", id="1")],
        [AIMessage(content="Hi", id="2")]
    )
    assert len(result) == 2
    
    # Test message updates still work
    result = add_messages(
        [HumanMessage(content="Hello", id="1")],
        [HumanMessage(content="Updated", id="1")]
    )
    assert len(result) == 1
    assert result[0].content == "Updated"
    
    print("✅ Backward compatibility maintained")

if __name__ == "__main__":
    try:
        test_add_messages_basic()
        test_message_graph()
        test_state_graph_update_state()
        test_node_based_deletion()
        test_backward_compatibility()
        print("\n🎉 All core tests passed! Message deletion functionality is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
