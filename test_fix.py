#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges
when using callable class instances without path_map.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

from typing import TypedDict
from langgraph.graph.state import StateGraph

def test_callable_in_conditional_edges_with_no_path_map():
    """Test that reproduces the original issue and verifies the fix."""
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    print("Creating StateGraph and adding nodes...")
    workflow = StateGraph(State)
    workflow.add_node("rewriter", rewrite)
    workflow.add_node("analyzer", analyze)
    
    print("Adding conditional edges with callable class instance (this would previously raise TypeError)...")
    try:
        # This line would previously raise TypeError: get_type_hints() only accepts modules, classes, methods, or functions
        workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
        print("✅ Successfully added conditional edges with callable class instance!")
    except TypeError as e:
        print(f"❌ TypeError still occurs: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    print("Setting entry point and compiling workflow...")
    workflow.set_entry_point("rewriter")
    
    try:
        app = workflow.compile()
        print("✅ Successfully compiled workflow!")
    except Exception as e:
        print(f"❌ Error compiling workflow: {e}")
        return False
    
    print("Testing workflow execution...")
    try:
        result = app.invoke({"query": "what is weather in sf"})
        expected = {"query": "analyzed: query: what is weather in sf"}
        
        if result == expected:
            print(f"✅ Test passed! Result: {result}")
            return True
        else:
            print(f"❌ Test failed! Expected: {expected}, Got: {result}")
            return False
    except Exception as e:
        print(f"❌ Error during workflow execution: {e}")
        return False

if __name__ == "__main__":
    print("Testing fix for TypeError in add_conditional_edges with callable class instances...")
    print("=" * 80)
    
    success = test_callable_in_conditional_edges_with_no_path_map()
    
    print("=" * 80)
    if success:
        print("🎉 All tests passed! The fix is working correctly.")
        sys.exit(0)
    else:
        print("💥 Test failed! The fix needs more work.")
        sys.exit(1)
