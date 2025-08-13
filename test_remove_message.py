#!/usr/bin/env python3
"""Test script to check if RemoveMessage exists in langchain_core.messages"""

try:
    from langchain_core.messages import RemoveMessage
    print("✅ RemoveMessage class found in langchain_core.messages")
    print(f"RemoveMessage class: {RemoveMessage}")
    
    # Test creating an instance
    try:
        remove_msg = RemoveMessage(id="test-id")
        print(f"✅ Successfully created RemoveMessage instance: {remove_msg}")
        print(f"RemoveMessage attributes: {dir(remove_msg)}")
    except Exception as e:
        print(f"❌ Error creating RemoveMessage instance: {e}")
        
except ImportError as e:
    print(f"❌ RemoveMessage not found in langchain_core.messages: {e}")
    print("Will need to implement RemoveMessage class locally")

# Also check what's available in langchain_core.messages
try:
    import langchain_core.messages as messages_module
    available_classes = [name for name in dir(messages_module) if not name.startswith('_')]
    print(f"\nAvailable classes in langchain_core.messages: {available_classes}")
except Exception as e:
    print(f"Error inspecting langchain_core.messages: {e}")
