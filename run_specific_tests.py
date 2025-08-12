#!/usr/bin/env python3
"""
Run the specific test cases to verify the fix for TypeError in add_conditional_edges.
"""

import sys
import os
import traceback

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

def test_callable_in_conditional_edges_with_no_path_map():
    """Test case for callable instances with no path_map"""
    from typing import TypedDict
    from langgraph.graph.state import StateGraph
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    workflow = StateGraph(State)
    workflow.add_node("rewriter", rewrite)
    workflow.add_node("analyzer", analyze)
    workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
    workflow.set_entry_point("rewriter")
    app = workflow.compile()

    result = app.invoke({"query": "what is weather in sf"})
    expected = {"query": "analyzed: query: what is weather in sf"}
    
    assert result == expected, f"Expected {expected}, got {result}"
    return True

def test_function_in_conditional_edges_with_no_path_map():
    """Test case for regular functions with no path_map"""
    from typing import TypedDict
    from langgraph.graph.state import StateGraph
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    def choose_analyzer(data: State) -> str:
        return "analyzer"

    workflow = StateGraph(State)
    workflow.add_node("rewriter", rewrite)
    workflow.add_node("analyzer", analyze)
    workflow.add_conditional_edges("rewriter", choose_analyzer)
    workflow.set_entry_point("rewriter")
    app = workflow.compile()

    result = app.invoke({"query": "what is weather in sf"})
    expected = {"query": "analyzed: query: what is weather in sf"}
    
    assert result == expected, f"Expected {expected}, got {result}"
    return True

def main():
    print("Running specific test cases to verify the fix...")
    print("=" * 60)
    
    # Test 1: Callable instance
    print("\nTest 1: test_callable_in_conditional_edges_with_no_path_map")
    try:
        test_callable_in_conditional_edges_with_no_path_map()
        print("✅ PASSED: Callable instance test")
    except Exception as e:
        print(f"❌ FAILED: Callable instance test - {e}")
        print("Traceback:")
        traceback.print_exc()
    
    # Test 2: Regular function
    print("\nTest 2: test_function_in_conditional_edges_with_no_path_map")
    try:
        test_function_in_conditional_edges_with_no_path_map()
        print("✅ PASSED: Regular function test")
    except Exception as e:
        print(f"❌ FAILED: Regular function test - {e}")
        print("Traceback:")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test execution complete!")

if __name__ == "__main__":
    main()
