#!/usr/bin/env python3

"""
Test to verify that the fix for global resume consumption is working correctly.
"""

from typing import TypedDict
from typing_extensions import Annotated
from operator import add

from langgraph.graph import StateGraph, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver


class State(TypedDict):
    results: Annotated[list[str], add]


def create_test_node(name: str):
    """Create a node that interrupts and captures the resume value."""
    def node(_):
        print(f"Node {name} requesting interrupt...")
        value = interrupt(f"Please provide value for {name}")
        print(f"Node {name} received: {value}")
        return {"results": [f"{name}:{value}"]}
    return node


def test_global_resume_consumption_fix():
    """Test that demonstrates the fix is working."""
    print("=== Testing Global Resume Consumption Fix ===\n")
    
    # Create graph with two parallel nodes that interrupt
    graph = (
        StateGraph(State)
        .add_node("node_a", create_test_node("A"))
        .add_node("node_b", create_test_node("B"))
        .add_edge(START, "node_a")
        .add_edge(START, "node_b")
        .compile(checkpointer=MemorySaver())
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    # First invoke - both nodes will interrupt
    print("1. First invoke (will interrupt):")
    try:
        result = graph.invoke({"results": []}, config)
        print(f"   Unexpected result: {result}")
    except Exception as e:
        print(f"   Expected interruption: {type(e).__name__}")
    
    print("\n2. Resuming with global value 'GLOBAL':")
    try:
        result = graph.invoke(Command(resume="GLOBAL"), config)
        print(f"   Final result: {result}")
        
        # Analyze results
        results = result.get("results", [])
        a_results = [r for r in results if r.startswith("A:")]
        b_results = [r for r in results if r.startswith("B:")]
        
        print(f"   Node A results: {a_results}")
        print(f"   Node B results: {b_results}")
        
        if len(a_results) == 1 and len(b_results) == 0:
            print("   ✓ CORRECT: Only node A consumed the global resume value")
            return True
        elif len(a_results) == 0 and len(b_results) == 1:
            print("   ✓ CORRECT: Only node B consumed the global resume value")
            return True
        elif len(a_results) == 1 and len(b_results) == 1:
            if "GLOBAL" in a_results[0] and "GLOBAL" in b_results[0]:
                print("   ✗ BUG: Both nodes consumed the same global resume value!")
                return False
            else:
                print("   ✓ CORRECT: Nodes got different resume values")
                return True
        else:
            print("   ? UNCLEAR: Unexpected result pattern")
            return False
            
    except Exception as e:
        print(f"   Error during resume: {e}")
        return False


if __name__ == "__main__":
    success = test_global_resume_consumption_fix()
    if success:
        print("\n🎉 Fix is working correctly!")
    else:
        print("\n❌ Issue still exists or new problem detected")