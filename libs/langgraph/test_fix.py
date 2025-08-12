#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges
when no path_map is provided for callable instances.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from typing import TypedDict
from langgraph.graph.state import StateGraph

def test_callable_in_conditional_edges_with_no_path_map():
    """Test that callable class instances work with add_conditional_edges without path_map"""
    print("Testing callable class instance...")
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    try:
        workflow = StateGraph(State)
        workflow.add_node("rewriter", rewrite)
        workflow.add_node("analyzer", analyze)
        workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
        workflow.set_entry_point("rewriter")
        app = workflow.compile()

        result = app.invoke({"query": "what is weather in sf"})
        expected = {"query": "analyzed: query: what is weather in sf"}
        
        if result == expected:
            print("✅ test_callable_in_conditional_edges_with_no_path_map PASSED")
            return True
        else:
            print(f"❌ test_callable_in_conditional_edges_with_no_path_map FAILED")
            print(f"Expected: {expected}")
            print(f"Got: {result}")
            return False
    except Exception as e:
        print(f"❌ test_callable_in_conditional_edges_with_no_path_map FAILED with exception: {e}")
        return False

def test_function_in_conditional_edges_with_no_path_map():
    """Test that regular functions still work with add_conditional_edges without path_map"""
    print("Testing regular function...")
    
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    def choose_analyzer(data: State) -> str:
        return "analyzer"

    try:
        workflow = StateGraph(State)
        workflow.add_node("rewriter", rewrite)
        workflow.add_node("analyzer", analyze)
        workflow.add_conditional_edges("rewriter", choose_analyzer)
        workflow.set_entry_point("rewriter")
        app = workflow.compile()

        result = app.invoke({"query": "what is weather in sf"})
        expected = {"query": "analyzed: query: what is weather in sf"}
        
        if result == expected:
            print("✅ test_function_in_conditional_edges_with_no_path_map PASSED")
            return True
        else:
            print(f"❌ test_function_in_conditional_edges_with_no_path_map FAILED")
            print(f"Expected: {expected}")
            print(f"Got: {result}")
            return False
    except Exception as e:
        print(f"❌ test_function_in_conditional_edges_with_no_path_map FAILED with exception: {e}")
        return False

if __name__ == "__main__":
    print("Running tests to verify the fix for TypeError in add_conditional_edges...")
    print("=" * 70)
    
    test1_passed = test_callable_in_conditional_edges_with_no_path_map()
    print()
    test2_passed = test_function_in_conditional_edges_with_no_path_map()
    
    print()
    print("=" * 70)
    if test1_passed and test2_passed:
        print("🎉 All tests PASSED! The fix is working correctly.")
        sys.exit(0)
    else:
        print("💥 Some tests FAILED! The fix needs more work.")
        sys.exit(1)
