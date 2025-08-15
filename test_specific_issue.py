#!/usr/bin/env python3

"""
Test to demonstrate the specific issue with global resume consumption.

The issue: When using a global resume value, multiple parallel subgraph calls
can both consume the same resume value, leading to undefined behavior.
"""

from typing import TypedDict

from langgraph.graph import StateGraph, START  
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver


class SubgraphState(TypedDict):
    name: str
    value: str


def create_subgraph(name: str):
    """Create a subgraph that interrupts and records what value it receives."""
    
    def subgraph_node(state: SubgraphState):
        print(f"Subgraph {name} starting...")
        resumed_value = interrupt(f"Need input for {name}")
        print(f"Subgraph {name} received resume value: {resumed_value}")
        return {"name": name, "value": resumed_value}
    
    return (
        StateGraph(SubgraphState)
        .add_node("node", subgraph_node)
        .add_edge(START, "node")
        .compile(checkpointer=True)
    )


def test_global_resume_consumption():
    """Test that demonstrates the consumption issue."""
    
    subgraph1 = create_subgraph("A")
    subgraph2 = create_subgraph("B")
    
    # Track how many times each subgraph gets the resume value
    results = []
    
    def call_subgraph1(_):
        print("Invoking subgraph A...")
        result = subgraph1.invoke({"name": "", "value": ""})
        results.append(("A", result["value"]))
        return {"dummy": "a"}
    
    def call_subgraph2(_):
        print("Invoking subgraph B...")
        result = subgraph2.invoke({"name": "", "value": ""})
        results.append(("B", result["value"]))
        return {"dummy": "b"}
    
    class DummyState(TypedDict):
        dummy: str
    
    # Create parent with two parallel tasks that call subgraphs
    parent = (
        StateGraph(DummyState)
        .add_node("task1", call_subgraph1)
        .add_node("task2", call_subgraph2)
        .add_edge(START, "task1") 
        .add_edge(START, "task2")
        .compile(checkpointer=MemorySaver())
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    # First invoke - both subgraphs interrupt
    print("=== FIRST INVOKE ===")
    parent.invoke({"dummy": "start"}, config)
    
    # Resume with global value - both might consume it
    print("\n=== RESUMING WITH GLOBAL VALUE ===")
    parent.invoke(Command(resume="GLOBAL_RESUME"), config)
    
    print(f"\nResults: {results}")
    
    # Check if both got the same value (the bug)
    if len(results) == 2 and results[0][1] == results[1][1] == "GLOBAL_RESUME":
        print("BUG DETECTED: Both subgraphs consumed the same global resume value!")
        return True
    else:
        print("No bug detected - subgraphs handled resume values correctly")
        return False


if __name__ == "__main__":
    test_global_resume_consumption()