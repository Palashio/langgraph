#!/usr/bin/env python3
"""
Simple test script to verify RemoveMessage functionality in add_messages function.
This is a temporary test file to validate the implementation.
"""

import sys
import os

# Add the langgraph package to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

from langchain_core.messages import HumanMessage, AIMessage, RemoveMessage
from langgraph.graph.message import add_messages

def test_basic_remove_message():
    """Test basic RemoveMessage functionality"""
    print("Testing basic RemoveMessage functionality...")
    
    # Test 1: Remove a message by ID
    msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2")]
    msgs2 = [RemoveMessage(id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1, f"Expected 1 message, got {len(result)}"
    assert result[0].id == "2", f"Expected message with id '2', got {result[0].id}"
    assert result[0].content == "Hi", f"Expected content 'Hi', got {result[0].content}"
    print("✓ Basic removal test passed")
    
    # Test 2: Remove non-existent ID (should not affect anything)
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [RemoveMessage(id="999")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1, f"Expected 1 message, got {len(result)}"
    assert result[0].id == "1", f"Expected message with id '1', got {result[0].id}"
    print("✓ Non-existent ID removal test passed")
    
    # Test 3: Mix regular messages with RemoveMessage
    msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2")]
    msgs2 = [AIMessage(content="New message", id="3"), RemoveMessage(id="1")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2, f"Expected 2 messages, got {len(result)}"
    message_ids = {m.id for m in result}
    assert "1" not in message_ids, "Message with id '1' should be removed"
    assert "2" in message_ids, "Message with id '2' should remain"
    assert "3" in message_ids, "Message with id '3' should be added"
    print("✓ Mixed messages with removal test passed")
    
    # Test 4: Multiple RemoveMessage instances
    msgs1 = [HumanMessage(content="Hello", id="1"), AIMessage(content="Hi", id="2"), HumanMessage(content="Test", id="3")]
    msgs2 = [RemoveMessage(id="1"), RemoveMessage(id="3")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 1, f"Expected 1 message, got {len(result)}"
    assert result[0].id == "2", f"Expected message with id '2', got {result[0].id}"
    print("✓ Multiple RemoveMessage test passed")
    
    # Test 5: Backward compatibility - regular message processing
    msgs1 = [HumanMessage(content="Hello", id="1")]
    msgs2 = [AIMessage(content="Hi there!", id="2")]
    result = add_messages(msgs1, msgs2)
    
    assert len(result) == 2, f"Expected 2 messages, got {len(result)}"
    assert result[0].content == "Hello", f"Expected first message content 'Hello', got {result[0].content}"
    assert result[1].content == "Hi there!", f"Expected second message content 'Hi there!', got {result[1].content}"
    print("✓ Backward compatibility test passed")
    
    print("\nAll tests passed! ✅")

if __name__ == "__main__":
    test_basic_remove_message()
