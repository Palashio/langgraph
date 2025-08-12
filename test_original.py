#!/usr/bin/env python3
"""
Extract and run the original test case without pytest dependencies
"""
import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

from typing import TypedDict
from langgraph.graph.state import StateGraph

def test_callable_in_conditional_edges_with_no_path_map() -> None:
    """Original test case from test_pregel.py"""
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

def main():
    """Run the original test case"""
    try:
        print("Running original test_callable_in_conditional_edges_with_no_path_map...")
        test_callable_in_conditional_edges_with_no_path_map()
        print("✅ Original test case PASSED")
        print("🎉 The fix successfully resolves the TypeError for callable class instances!")
        return True
    except Exception as e:
        print(f"❌ Original test case FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
