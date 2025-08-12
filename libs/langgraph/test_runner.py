#!/usr/bin/env python3
"""
Simple test runner for RemoveMessage functionality tests.
This runs the tests without requiring pytest.
"""

import sys
import traceback
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


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run_test(self, test_name, test_func):
        """Run a single test function."""
        try:
            print(f"Running {test_name}...", end=" ")
            test_func()
            print("✓ PASSED")
            self.passed += 1
        except Exception as e:
            print("✗ FAILED")
            self.failed += 1
            self.errors.append(f"{test_name}: {str(e)}")
            traceback.print_exc()

    def print_summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Test Summary: {self.passed}/{total} tests passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*50}")


def test_basic_message_removal():
    """Test basic removal of a message by ID."""
    msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2")]
    msgs2 = [RemoveMessage(id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].id == "2"
    assert result[0].content == "Hi"


def test_remove_nonexistent_id():
    """Test removing a message with non-existent ID (should not affect anything)."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="999")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].id == "1"
    assert result[0].content == "Hello"


def test_multiple_remove_messages():
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


def test_mixed_regular_and_remove_messages():
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


def test_backward_compatibility():
    """Test that regular message processing still works without RemoveMessage."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [AIMessage(content="Hi there!", id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "Hi there!"


def test_message_replacement_still_works():
    """Test that message replacement by ID still works."""
    msgs1 = [HumanMessage(content="Original", id="1")]
    msgs2 = [HumanMessage(content="Updated", id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].content == "Updated"
    assert result[0].id == "1"


def test_node_initiated_deletion():
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


def test_node_mixed_add_and_remove():
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


def test_user_initiated_deletion_via_update_state():
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
    compiled_graph.update_state(config, values={"messages": [RemoveMessage(id=message_id)]})
    
    # Get current state
    current_state = compiled_graph.get_state(config)
    assert len(current_state.values["messages"]) == 0


def test_update_state_with_mixed_operations():
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
    compiled_graph.update_state(config, values={"messages": [
        AIMessage(content="New message", id="new"),
        RemoveMessage(id="first")
    ]})
    
    # Get current state
    current_state = compiled_graph.get_state(config)
    messages = current_state.values["messages"]
    
    assert len(messages) == 2
    contents = {m.content for m in messages}
    assert "First" not in contents  # Should be removed
    assert "Second" in contents     # Should remain
    assert "New message" in contents  # Should be added


def main():
    """Run all tests."""
    runner = TestRunner()
    
    print("Running RemoveMessage functionality tests...")
    print("=" * 50)
    
    # Test add_messages function directly
    runner.run_test("test_basic_message_removal", test_basic_message_removal)
    runner.run_test("test_remove_nonexistent_id", test_remove_nonexistent_id)
    runner.run_test("test_multiple_remove_messages", test_multiple_remove_messages)
    runner.run_test("test_mixed_regular_and_remove_messages", test_mixed_regular_and_remove_messages)
    runner.run_test("test_backward_compatibility", test_backward_compatibility)
    runner.run_test("test_message_replacement_still_works", test_message_replacement_still_works)
    
    # Test MessageGraph integration
    runner.run_test("test_node_initiated_deletion", test_node_initiated_deletion)
    runner.run_test("test_node_mixed_add_and_remove", test_node_mixed_add_and_remove)
    
    # Test StateGraph integration with update_state
    runner.run_test("test_user_initiated_deletion_via_update_state", test_user_initiated_deletion_via_update_state)
    runner.run_test("test_update_state_with_mixed_operations", test_update_state_with_mixed_operations)
    
    runner.print_summary()
    
    return runner.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


