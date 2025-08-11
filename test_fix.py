#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges
"""
import sys
import os
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add the langgraph library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

def test_callable_in_conditional_edges_with_no_path_map():
    """Test that callable class instances work without path_map"""
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

    try:
        workflow = StateGraph(State)
        workflow.add_node("rewriter", rewrite)
        workflow.add_node("analyzer", analyze)
        workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
        workflow.set_entry_point("rewriter")
        app = workflow.compile()

        result = app.invoke({"query": "what is weather in sf"})
        expected = {"query": "analyzed: query: what is weather in sf"}
        
        assert result == expected, f"Expected {expected}, got {result}"
        print("✓ test_callable_in_conditional_edges_with_no_path_map PASSED")
        return True
    except Exception as e:
        print(f"❌ test_callable_in_conditional_edges_with_no_path_map FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_function_in_conditional_edges_with_no_path_map():
    """Test that regular functions still work without path_map"""
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

    try:
        workflow = StateGraph(State)
        workflow.add_node("rewriter", rewrite)
        workflow.add_node("analyzer", analyze)
        workflow.add_conditional_edges("rewriter", choose_analyzer)
        workflow.set_entry_point("rewriter")
        app = workflow.compile()

        result = app.invoke({"query": "what is weather in sf"})
        expected = {"query": "analyzed: query: what is weather in sf"}
        
        assert result == expected, f"Expected {expected}, got {result}"
        print("✓ test_function_in_conditional_edges_with_no_path_map PASSED")
        return True
    except Exception as e:
        print(f"❌ test_function_in_conditional_edges_with_no_path_map FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running tests to verify the fix...")
    
    test1_passed = test_callable_in_conditional_edges_with_no_path_map()
    test2_passed = test_function_in_conditional_edges_with_no_path_map()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

