#!/usr/bin/env python3
"""Test script to verify the modified add_messages function works correctly with RemoveMessage"""

import sys
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from langgraph.graph.message import add_messages

def test_basic_functionality():
    """Test that basic functionality still works"""
    print("Testing basic functionality...")
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [AIMessage(content="Hi there!", id="2")]
    result = add_messages(msgs1, msgs2)
    print(f"Basic append: {[f'{m.__class__.__name__}(id={m.id})' for m in result]}")
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "2"
    print("✅ Basic functionality works")

def test_message_update():
    """Test that message updates still work"""
    print("\nTesting message updates...")
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [HumanMessage(content="Hello again", id="1")]
    result = add_messages(msgs1, msgs2)
    print(f"Update result: {[f'{m.__class__.__name__}(id={m.id}, content={m.content})' for m in result]}")
    assert len(result) == 1
    assert result[0].id == "1"
    assert result[0].content == "Hello again"
    print("✅ Message updates work")

def test_remove_message():
    """Test RemoveMessage functionality"""
    print("\nTesting RemoveMessage functionality...")
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3")
    ]
    msgs2 = [RemoveMessage(id="2")]
    result = add_messages(msgs1, msgs2)
    print(f"Remove result: {[f'{m.__class__.__name__}(id={m.id})' for m in result]}")
    assert len(result) == 2
    assert result[0].id == "1"
    assert result[1].id == "3"
    print("✅ RemoveMessage works")

def test_mixed_operations():
    """Test mixed operations with regular messages and RemoveMessage"""
    print("\nTesting mixed operations...")
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3")
    ]
    msgs2 = [
        RemoveMessage(id="2"),  # Remove message with id="2"
        AIMessage(content="I'm good!", id="4"),  # Add new message
        HumanMessage(content="Updated hello", id="1")  # Update existing message
    ]
    result = add_messages(msgs1, msgs2)
    print(f"Mixed result: {[f'{m.__class__.__name__}(id={m.id}, content={m.content})' for m in result]}")
    assert len(result) == 3
    # Check that message with id="2" was removed
    assert not any(m.id == "2" for m in result)
    # Check that message with id="1" was updated
    updated_msg = next(m for m in result if m.id == "1")
    assert updated_msg.content == "Updated hello"
    # Check that new message with id="4" was added
    assert any(m.id == "4" for m in result)
    print("✅ Mixed operations work")

def test_remove_nonexistent():
    """Test removing a message that doesn't exist"""
    print("\nTesting removal of non-existent message...")
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="999")]  # ID that doesn't exist
    result = add_messages(msgs1, msgs2)
    print(f"Remove non-existent result: {[f'{m.__class__.__name__}(id={m.id})' for m in result]}")
    assert len(result) == 1
    assert result[0].id == "1"
    print("✅ Removing non-existent message works (no error)")

if __name__ == "__main__":
    try:
        test_basic_functionality()
        test_message_update()
        test_remove_message()
        test_mixed_operations()
        test_remove_nonexistent()
        print("\n🎉 All tests passed! The add_messages function correctly handles RemoveMessage objects.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
