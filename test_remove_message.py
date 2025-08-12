#!/usr/bin/env python3
"""Test script to verify RemoveMessage functionality"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph.message import add_messages

def test_remove_message_basic():
    """Test basic RemoveMessage functionality"""
    # Create initial messages
    msg1 = HumanMessage(content="Hello", id="1")
    msg2 = AIMessage(content="Hi there!", id="2")
    left = [msg1, msg2]
    
    # Create RemoveMessage to remove msg2
    remove_msg = RemoveMessage(id="2")
    right = [remove_msg]
    
    # Test removal
    result = add_messages(left, right)
    
    # Should only have msg1 left
    assert len(result) == 1
    assert result[0].content == "Hello"
    assert result[0].id == "1"
    print("✅ Basic RemoveMessage test passed")

def test_remove_message_with_new_messages():
    """Test RemoveMessage with new messages being added"""
    # Create initial messages
    msg1 = HumanMessage(content="Hello", id="1")
    msg2 = AIMessage(content="Hi there!", id="2")
    left = [msg1, msg2]
    
    # Create RemoveMessage and new message
    remove_msg = RemoveMessage(id="2")
    new_msg = AIMessage(content="How can I help?", id="3")
    right = [remove_msg, new_msg]
    
    # Test removal and addition
    result = add_messages(left, right)
    
    # Should have msg1 and new_msg
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "How can I help?"
    print("✅ RemoveMessage with new messages test passed")

def test_remove_nonexistent_message():
    """Test RemoveMessage with non-existent ID"""
    # Create initial messages
    msg1 = HumanMessage(content="Hello", id="1")
    left = [msg1]
    
    # Create RemoveMessage for non-existent ID
    remove_msg = RemoveMessage(id="999")
    right = [remove_msg]
    
    # Test removal
    result = add_messages(left, right)
    
    # Should still have msg1
    assert len(result) == 1
    assert result[0].content == "Hello"
    print("✅ Remove non-existent message test passed")

if __name__ == "__main__":
    try:
        test_remove_message_basic()
        test_remove_message_with_new_messages()
        test_remove_nonexistent_message()
        print("\n🎉 All tests passed! RemoveMessage implementation is working correctly.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
