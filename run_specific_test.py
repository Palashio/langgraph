#!/usr/bin/env python3
"""
Run the specific test function to verify the fix works.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

try:
    # Import the test function directly
    from typing import TypedDict
    from langgraph.graph import StateGraph
    
    print("Running test_callable_in_conditional_edges_with_no_path_map()...")
    
    # This is the exact test case from the test file
    def test_callable_in_conditional_edges_with_no_path_map() -> None:
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

        assert app.invoke({"query": "what is weather in sf"}) == {
            "query": "analyzed: query: what is weather in sf",
        }
    
    # Run the test
    test_callable_in_conditional_edges_with_no_path_map()
    print("✅ SUCCESS: test_callable_in_conditional_edges_with_no_path_map() passed!")
    print("✅ The fix successfully resolves the TypeError for callable instances!")
    
except Exception as e:
    print(f"❌ FAILURE: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 Test completed successfully! The fix works as expected.")
