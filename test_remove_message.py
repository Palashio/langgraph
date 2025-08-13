#!/usr/bin/env python3
"""Test script to verify RemoveMessage functionality in add_messages function."""

from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from langgraph.graph.message import add_messages

def test_remove_message_functionality():
    """Test that RemoveMessage correctly removes messages by ID."""
    
    # Test 1: Basic removal functionality
    print("Test 1: Basic removal functionality")
    msg1 = HumanMessage(content="Hello", id="msg1")
    msg2 = AIMessage(content="Hi there!", id="msg2")
    msg3 = HumanMessage(content="How are you?", id="msg3")
    
    left = [msg1, msg2, msg3]
    right = [RemoveMessage(id="msg2")]
    
    result = add_messages(left, right)
    print(f"Original messages: {len(left)} messages")
    print(f"After removal: {len(result)} messages")
    print(f"Remaining message IDs: {[m.id for m in result]}")
    
    # Should have msg1 and msg3, but not msg2
    assert len(result) == 2
    assert result[0].id == "msg1"
    assert result[1].id == "msg3"
    print("✓ Test 1 passed\n")
    
    # Test 2: Remove multiple messages
    print("Test 2: Remove multiple messages")
    left = [msg1, msg2, msg3]
    right = [RemoveMessage(id="msg1"), RemoveMessage(id="msg3")]
    
    result = add_messages(left, right)
    print(f"Original messages: {len(left)} messages")
    print(f"After removal: {len(result)} messages")
    print(f"Remaining message IDs: {[m.id for m in result]}")
    
    # Should have only msg2
    assert len(result) == 1
    assert result[0].id == "msg2"
    print("✓ Test 2 passed\n")
    
    # Test 3: Mix removal and addition
    print("Test 3: Mix removal and addition")
    new_msg = AIMessage(content="New message", id="msg4")
    left = [msg1, msg2, msg3]
    right = [RemoveMessage(id="msg2"), new_msg]
    
    result = add_messages(left, right)
    print(f"Original messages: {len(left)} messages")
    print(f"After removal and addition: {len(result)} messages")
    print(f"Remaining message IDs: {[m.id for m in result]}")
    
    # Should have msg1, msg3, and msg4
    assert len(result) == 3
    assert result[0].id == "msg1"
    assert result[1].id == "msg3"
    assert result[2].id == "msg4"
    print("✓ Test 3 passed\n")
    
    # Test 4: Remove non-existent message (should not affect anything)
    print("Test 4: Remove non-existent message")
    left = [msg1, msg2]
    right = [RemoveMessage(id="nonexistent")]
    
    result = add_messages(left, right)
    print(f"Original messages: {len(left)} messages")
    print(f"After attempting to remove non-existent: {len(result)} messages")
    
    # Should still have both messages
    assert len(result) == 2
    assert result[0].id == "msg1"
    assert result[1].id == "msg2"
    print("✓ Test 4 passed\n")
    
    # Test 5: Regular message merging still works
    print("Test 5: Regular message merging still works")
    updated_msg1 = HumanMessage(content="Hello updated", id="msg1")
    left = [msg1, msg2]
    right = [updated_msg1]
    
    result = add_messages(left, right)
    print(f"Original messages: {len(left)} messages")
    print(f"After update: {len(result)} messages")
    print(f"Updated message content: {result[0].content}")
    
    # Should still have 2 messages, but msg1 should be updated
    assert len(result) == 2
    assert result[0].id == "msg1"
    assert result[0].content == "Hello updated"
    assert result[1].id == "msg2"
    print("✓ Test 5 passed\n")
    
    print("All tests passed! RemoveMessage functionality is working correctly.")

if __name__ == "__main__":
    test_remove_message_functionality()
