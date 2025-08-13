#!/usr/bin/env python3
"""Test script to verify RemoveMessage imports work correctly."""

import sys
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

def test_direct_import():
    """Test importing RemoveMessage directly from langchain_core."""
    print("Testing direct import from langchain_core.messages...")
    try:
        from langchain_core.messages import RemoveMessage
        msg = RemoveMessage(id="test-id")
        assert msg.id == "test-id"
        print("✅ Direct import from langchain_core.messages works")
        return True
    except Exception as e:
        print(f"❌ Direct import failed: {e}")
        return False

def test_langgraph_import():
    """Test importing RemoveMessage from langgraph.graph."""
    print("Testing import from langgraph.graph...")
    try:
        from langgraph.graph import RemoveMessage
        msg = RemoveMessage(id="test-id")
        assert msg.id == "test-id"
        print("✅ Import from langgraph.graph works")
        return True
    except Exception as e:
        print(f"❌ Import from langgraph.graph failed: {e}")
        return False

def test_message_functionality():
    """Test that RemoveMessage works with add_messages function."""
    print("Testing RemoveMessage functionality with add_messages...")
    try:
        from langchain_core.messages import HumanMessage, AIMessage
        from langgraph.graph import RemoveMessage, add_messages
        
        msgs1 = [
            HumanMessage(content="Hello", id="1"),
            AIMessage(content="Hi", id="2")
        ]
        msgs2 = [RemoveMessage(id="1")]
        result = add_messages(msgs1, msgs2)
        
        assert len(result) == 1
        assert result[0].id == "2"
        print("✅ RemoveMessage functionality works with add_messages")
        return True
    except Exception as e:
        print(f"❌ RemoveMessage functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing RemoveMessage imports and exports...\n")
    
    success = True
    success &= test_direct_import()
    success &= test_langgraph_import()
    success &= test_message_functionality()
    
    if success:
        print("\n🎉 All import/export tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
