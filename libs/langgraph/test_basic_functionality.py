#!/usr/bin/env python3
"""
Basic functionality test for RemoveMessage implementation.
This script tests the core functionality without requiring pytest.
"""

import sys
import os

# Add the langgraph package to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.graph.message import RemoveMessage, add_messages
    from langgraph import RemoveMessage as MainRemoveMessage
    
    print("✓ All imports successful")
    
    # Test 1: Basic RemoveMessage creation
    remove_msg = RemoveMessage(id="test_id")
    assert remove_msg.id == "test_id"
    assert repr(remove_msg) == "RemoveMessage(id='test_id')"
    print("✓ Test 1: RemoveMessage creation works")
    
    # Test 2: RemoveMessage equality
    remove_msg1 = RemoveMessage(id="test_id")
    remove_msg2 = RemoveMessage(id="test_id")
    remove_msg3 = RemoveMessage(id="different_id")
    
    assert remove_msg1 == remove_msg2
    assert remove_msg1 != remove_msg3
    print("✓ Test 2: RemoveMessage equality works")
    
    # Test 3: Basic message deletion
    msg1 = HumanMessage(content="Hello", id="msg1")
    msg2 = AIMessage(content="Hi there", id="msg2")
    msg3 = HumanMessage(content="How are you?", id="msg3")
    left = [msg1, msg2, msg3]
    
    right = [RemoveMessage(id="msg2")]
    result = add_messages(left, right)
    
    assert len(result) == 2
    assert result[0].id == "msg1"
    assert result[1].id == "msg3"
    print("✓ Test 3: Basic message deletion works")
    
    # Test 4: Delete non-existent message (no-op)
    left = [msg1, msg2]
    right = [RemoveMessage(id="nonexistent")]
    result = add_messages(left, right)
    
    assert len(result) == 2
    assert result[0].id == "msg1"
    assert result[1].id == "msg2"
    print("✓ Test 4: Delete non-existent message (no-op) works")
    
    # Test 5: Mixed operations (delete + update + add)
    left = [msg1, msg2, msg3]
    right = [
        RemoveMessage(id="msg2"),
        HumanMessage(content="Hello updated", id="msg1"),  # Update existing
        AIMessage(content="New message", id="msg4")  # Add new
    ]
    result = add_messages(left, right)
    
    assert len(result) == 3
    assert result[0].id == "msg1"
    assert result[0].content == "Hello updated"  # Updated
    assert result[1].id == "msg3"
    assert result[2].id == "msg4"
    print("✓ Test 5: Mixed operations (delete + update + add) works")
    
    # Test 6: Import from main package
    assert RemoveMessage == MainRemoveMessage
    print("✓ Test 6: Import from main package works")
    
    print("\n🎉 All basic functionality tests passed!")
    print("The RemoveMessage implementation is working correctly.")
    
except Exception as e:
    print(f"❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
