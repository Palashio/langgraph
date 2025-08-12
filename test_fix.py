#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges
when no path_map is provided for callable instances.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

try:
    from typing import TypedDict
    from langgraph.graph.state import StateGraph
    
    print("Testing the fix for add_conditional_edges with callable instances...")
    
    # Test 1: Callable instance (this should work with the fix)
    class State(TypedDict, total=False):
        query: str

    def rewrite(data: State) -> State:
        return {"query": f'query: {data["query"]}'}

    def analyze(data: State) -> State:
        return {"query": f'analyzed: {data["query"]}'}

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    print("Test 1: Testing callable instance (ChooseAnalyzer())...")
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
            print("✅ Test 1 PASSED: Callable instance works correctly")
        else:
            print(f"❌ Test 1 FAILED: Expected {expected}, got {result}")
            
    except Exception as e:
        print(f"❌ Test 1 FAILED with exception: {e}")
    
    # Test 2: Regular function (this should continue to work)
    def choose_analyzer(data: State) -> str:
        return "analyzer"

    print("\nTest 2: Testing regular function (choose_analyzer)...")
    try:
        workflow2 = StateGraph(State)
        workflow2.add_node("rewriter", rewrite)
        workflow2.add_node("analyzer", analyze)
        workflow2.add_conditional_edges("rewriter", choose_analyzer)
        workflow2.set_entry_point("rewriter")
        app2 = workflow2.compile()
        
        result2 = app2.invoke({"query": "what is weather in sf"})
        expected2 = {"query": "analyzed: query: what is weather in sf"}
        
        if result2 == expected2:
            print("✅ Test 2 PASSED: Regular function works correctly")
        else:
            print(f"❌ Test 2 FAILED: Expected {expected2}, got {result2}")
            
    except Exception as e:
        print(f"❌ Test 2 FAILED with exception: {e}")
    
    print("\n" + "="*50)
    print("Fix verification complete!")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Dependencies may not be installed properly.")
except Exception as e:
    print(f"Unexpected error: {e}")
