#!/usr/bin/env python3
"""
Debug the import and method availability issues.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

try:
    from langgraph.graph import StateGraph
    print(f"StateGraph imported successfully: {StateGraph}")
    print(f"StateGraph MRO: {StateGraph.__mro__}")
    
    # Check available methods
    methods = [method for method in dir(StateGraph) if not method.startswith('_')]
    print(f"Available methods: {methods}")
    
    # Check if add_conditional_edges is available
    if hasattr(StateGraph, 'add_conditional_edges'):
        print("✅ add_conditional_edges method is available")
    else:
        print("❌ add_conditional_edges method is NOT available")
        
    # Try to create an instance
    from typing import TypedDict
    
    class State(TypedDict, total=False):
        query: str
        
    workflow = StateGraph(State)
    print(f"StateGraph instance created: {workflow}")
    print(f"Instance methods: {[method for method in dir(workflow) if not method.startswith('_')]}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
