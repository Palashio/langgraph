#!/usr/bin/env python3
"""Quick test to verify RemoveMessage implementation works correctly."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages, RemoveMessage

def test_basic_functionality():
    """Test basic add_messages functionality still works."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [AIMessage(content="Hi there!", id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "Hi there!"
    print("✓ Basic functionality works")

def test_message_replacement():
    """Test message replacement by ID still works."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [HumanMessage(content="Hello again", id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].content == "Hello again"
    print("✓ Message replacement works")

def test_remove_message():
    """Test RemoveMessage functionality."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2"),
        HumanMessage(content="How are you?", id="3")
    ]
    msgs2 = [RemoveMessage(id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "How are you?"
    print("✓ RemoveMessage works")

def test_remove_nonexistent():
    """Test removing non-existent message ID."""
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="999")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1
    assert result[0].content == "Hello"
    print("✓ Removing non-existent ID works")

def test_mixed_operations():
    """Test mixed add and remove operations."""
    msgs1 = [
        HumanMessage(content="Hello", id="1"),
        AIMessage(content="Hi", id="2")
    ]
    msgs2 = [
        RemoveMessage(id="1"),
        AIMessage(content="New message", id="3")
    ]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2
    assert result[0].content == "Hi"
    assert result[1].content == "New message"
    print("✓ Mixed operations work")

def test_remove_message_class():
    """Test RemoveMessage class methods."""
    rm1 = RemoveMessage(id="test")
    rm2 = RemoveMessage(id="test")
    rm3 = RemoveMessage(id="other")
    
    assert rm1 == rm2
    assert rm1 != rm3
    assert str(rm1) == "RemoveMessage(id='test')"
    print("✓ RemoveMessage class methods work")

if __name__ == "__main__":
    print("Testing RemoveMessage implementation...")
    
    test_basic_functionality()
    test_message_replacement()
    test_remove_message()
    test_remove_nonexistent()
    test_mixed_operations()
    test_remove_message_class()
    
    print("\n✅ All tests passed! RemoveMessage implementation is working correctly.")
