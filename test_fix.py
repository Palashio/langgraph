#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges
when callable instance is passed without path_map.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

try:
    from typing import TypedDict
    from langgraph.graph import StateGraph
    
    print("Testing fix for callable instance in add_conditional_edges...")
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    # This should work without raising TypeError after our fix
    workflow = StateGraph(State)
    workflow.add_node("rewriter", rewrite)
    workflow.add_node("analyzer", analyze)
    
    # This line previously caused TypeError: get_type_hints() only accepts 
    # a module, class, method, or function, not instance
    workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
    workflow.set_entry_point("rewriter")
    
    # Try to compile the workflow
    app = workflow.compile()
    
    print("✅ SUCCESS: Callable instance works without path_map!")
    print("✅ No TypeError was raised during add_conditional_edges")
    
    # Test that it actually works by running it
    result = app.invoke({"query": "what is weather in sf"})
    expected = {"query": "analyzed: query: what is weather in sf"}
    
    if result == expected:
        print("✅ SUCCESS: Workflow execution produces expected result!")
        print(f"   Result: {result}")
    else:
        print("❌ FAILURE: Workflow execution result doesn't match expected")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FAILURE: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 All tests passed! The fix successfully resolves the TypeError.")
