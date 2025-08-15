#!/usr/bin/env python3

"""
Test to reproduce the original issue as described in the task description.

The issue was that parallel subgraph calls were able to use the same resume value,
leading to two parallel subgraph calls being able to access the same resume value.
"""

from typing import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver


class SubgraphState(TypedDict):
    result: str


class ParentState(TypedDict):
    subresults: list[str]


def create_subgraph(name: str):
    """Create a subgraph that interrupts."""
    
    def subgraph_node(state: SubgraphState):
        print(f"Subgraph {name} executing...")
        value = interrupt(f"Need input for subgraph {name}")
        print(f"Subgraph {name} received: {value}")
        return {"result": f"{name}_{value}"}
    
    return (
        StateGraph(SubgraphState)
        .add_node("node", subgraph_node)
        .add_edge(START, "node")
        .compile(checkpointer=True)  # This is key - subgraph has checkpointer=True
    )


def test_subgraph_global_resume():
    """Test the original issue with subgraphs."""
    
    subgraph1 = create_subgraph("SUB1")
    subgraph2 = create_subgraph("SUB2")
    
    def call_subgraph1(state: ParentState):
        print("Calling subgraph1...")
        result = subgraph1.invoke({"result": ""})
        return {"subresults": state.get("subresults", []) + [result["result"]]}
    
    def call_subgraph2(state: ParentState):
        print("Calling subgraph2...")
        result = subgraph2.invoke({"result": ""})
        return {"subresults": state.get("subresults", []) + [result["result"]]}
    
    # Note: Using Send to ensure parallel execution
    parent = (
        StateGraph(ParentState)
        .add_node("call1", call_subgraph1)
        .add_node("call2", call_subgraph2)
        .add_edge(START, "call1")
        .add_edge(START, "call2")
        .compile(checkpointer=MemorySaver())
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    print("=== FIRST INVOKE ===")
    try:
        result = parent.invoke({"subresults": []}, config)
        print(f"First result: {result}")
    except Exception as e:
        print(f"Expected interrupt: {e}")
    
    print("\n=== SECOND INVOKE WITH GLOBAL RESUME ===")
    try:
        result = parent.invoke(Command(resume="GLOBAL_VAL"), config)
        print(f"Resume result: {result}")
        
        # Check if both subgraphs got the resume value
        subresults = result.get("subresults", [])
        sub1_results = [r for r in subresults if r.startswith("SUB1")]
        sub2_results = [r for r in subresults if r.startswith("SUB2")]
        
        print(f"SUB1 results: {sub1_results}")
        print(f"SUB2 results: {sub2_results}")
        
        if sub1_results and sub2_results:
            # Both completed
            if "GLOBAL_VAL" in sub1_results[0] and "GLOBAL_VAL" in sub2_results[0]:
                print("BUG: Both subgraphs consumed the same global resume value!")
            else:
                print("GOOD: Subgraphs got different resume values") 
        else:
            print("INFO: Only one subgraph completed (expected with fix)")
            
    except Exception as e:
        print(f"Exception during resume: {e}")


if __name__ == "__main__":
    test_subgraph_global_resume()