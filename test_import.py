#!/usr/bin/env python3
"""Test to verify RemoveMessage can be imported from the graph module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

try:
    from langgraph.graph import RemoveMessage
    print("✓ Successfully imported RemoveMessage from langgraph.graph")
    
    # Test that it works
    rm = RemoveMessage(id="test")
    print(f"✓ Created RemoveMessage instance: {rm}")
    
    # Test importing alongside other graph components
    from langgraph.graph import MessageGraph, add_messages, MessagesState, RemoveMessage
    print("✓ Successfully imported RemoveMessage alongside other graph components")
    
except ImportError as e:
    print(f"✗ Failed to import RemoveMessage: {e}")
    sys.exit(1)

print("\n✅ RemoveMessage is properly exported and importable!")
