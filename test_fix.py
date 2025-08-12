#!/usr/bin/env python3
"""
Test script to verify the fix for callable class instances in add_conditional_edges
"""
import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

from typing import TypedDict
from langgraph import StateGraph

def test_callable_in_conditional_edges_with_no_path_map():
    """Test that callable class instances work with add_conditional_edges"""
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    # This should not raise a TypeError anymore
    workflow = StateGraph(State)
    workflow.add_node("rewriter", rewrite)
    workflow.add_node("analyzer", analyze)
    workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
    workflow.set_entry_point("rewriter")
    app = workflow.compile()

    result = app.invoke({"query": "what is weather in sf"})
    expected = {"query": "analyzed: query: what is weather in sf"}
    
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Test passed! Callable class instance works correctly with add_conditional_edges")

if __name__ == "__main__":
    try:
        test_callable_in_conditional_edges_with_no_path_map()
        print("🎉 All tests passed successfully!")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
