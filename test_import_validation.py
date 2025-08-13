#!/usr/bin/env python3
"""Test that RemoveMessage can be imported from the public API."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

def test_public_api_imports():
    """Test that RemoveMessage can be imported from various locations."""
    
    print("Testing RemoveMessage imports from public API...")
    
    # Test import from main package
    try:
        from langgraph import RemoveMessage
        print("✓ Successfully imported RemoveMessage from langgraph")
    except ImportError as e:
        print(f"✗ Failed to import RemoveMessage from langgraph: {e}")
        return False
    
    # Test import from graph module
    try:
        from langgraph.graph import RemoveMessage as GraphRemoveMessage
        print("✓ Successfully imported RemoveMessage from langgraph.graph")
    except ImportError as e:
        print(f"✗ Failed to import RemoveMessage from langgraph.graph: {e}")
        return False
    
    # Test import from message module
    try:
        from langgraph.graph.message import RemoveMessage as MessageRemoveMessage
        print("✓ Successfully imported RemoveMessage from langgraph.graph.message")
    except ImportError as e:
        print(f"✗ Failed to import RemoveMessage from langgraph.graph.message: {e}")
        return False
    
    # Verify they are the same class
    assert RemoveMessage is GraphRemoveMessage
    assert RemoveMessage is MessageRemoveMessage
    print("✓ All imports reference the same RemoveMessage class")
    
    # Test basic functionality
    rm = RemoveMessage(id="test-123")
    assert rm.id == "test-123"
    print("✓ RemoveMessage functionality works correctly")
    
    print("All import tests passed successfully!")
    return True

if __name__ == "__main__":
    success = test_public_api_imports()
    if not success:
        sys.exit(1)
