#!/usr/bin/env python3
"""
Test script that specifically reproduces the test case from test_pregel.py
to verify the TypeError fix in add_conditional_edges.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

def test_callable_in_conditional_edges_with_no_path_map():
    """
    Reproduce the exact test case from test_pregel.py to verify the fix.
    This test should pass with the fix and fail without it.
    """
    
    try:
        from typing import TypedDict
        from langgraph.graph.state import StateGraph
        
        print("Setting up test case...")
        
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
        
        print("Testing add_conditional_edges with callable class instance...")
        print("(This would raise TypeError without the fix)")
        
        # This is the critical line that would fail without the fix
        workflow.add_conditional_edges("rewriter", ChooseAnalyzer())
        
        print("✅ Successfully added conditional edges!")
        
        workflow.set_entry_point("rewriter")
        
        print("Compiling workflow...")
        app = workflow.compile()
        
        print("✅ Successfully compiled workflow!")
        
        print("Testing workflow execution...")
        result = app.invoke({"query": "what is weather in sf"})
        expected = {"query": "analyzed: query: what is weather in sf"}
        
        print(f"Result: {result}")
        print(f"Expected: {expected}")
        
        if result == expected:
            print("✅ Test execution successful!")
            return True
        else:
            print("❌ Test execution failed - wrong result")
            return False
            
    except TypeError as e:
        if "get_type_hints" in str(e) or "module, class, method, or function" in str(e):
            print(f"❌ Original TypeError still occurs: {e}")
            print("The fix did not work properly.")
            return False
        else:
            print(f"❌ Different TypeError: {e}")
            import traceback
            traceback.print_exc()
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing the specific fix for callable class instances in add_conditional_edges...")
    print("=" * 80)
    
    success = test_callable_in_conditional_edges_with_no_path_map()
    
    print("=" * 80)
    if success:
        print("🎉 Test passed! The fix is working correctly.")
        print("Callable class instances can now be used with add_conditional_edges without TypeError.")
        sys.exit(0)
    else:
        print("💥 Test failed! The fix needs more work.")
        sys.exit(1)
