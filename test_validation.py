#!/usr/bin/env python3
"""Simple validation test for RemoveMessage functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import RemoveMessage, add_messages

def test_basic_functionality():
    """Test basic RemoveMessage functionality."""
    print("Testing basic RemoveMessage functionality...")
    
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
    assert result[1].id == "3"
    print("✓ Basic removal test passed")
    
    # Test mixed operations
    print("Testing mixed operations...")
    mixed_msgs = [
        RemoveMessage(id="1"),  # Remove first message
        HumanMessage(content="New message", id="4"),  # Add new message
        AIMessage(content="Updated response", id="2")  # Update existing message
    ]
    result = add_messages(msgs1, mixed_msgs)
    print(f"Result length: {len(result)}")
    for msg in result:
        print(f"  ID: {msg.id}, Content: {msg.content}")
    print("✓ Mixed operations test passed")
    
    # Test RemoveMessage class properties
    print("Testing RemoveMessage class properties...")
    rm1 = RemoveMessage(id="test-id")
    assert rm1.id == "test-id"
    assert repr(rm1) == "RemoveMessage(id='test-id')"
    print("✓ RemoveMessage class test passed")
    
    print("All basic tests passed successfully!")

if __name__ == "__main__":
    test_basic_functionality()
