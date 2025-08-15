#!/usr/bin/env python3

"""
Test to check if the current race condition fix actually works in practice.
"""

import threading
import time
from typing import TypedDict

from langgraph.graph import StateGraph, START
from langgraph.types import Command, interrupt  
from langgraph.checkpoint.memory import MemorySaver


class State(TypedDict):
    values: list[str]


def create_interrupt_node(name: str):
    """Create a node that interrupts and records what value it gets."""
    results = []
    
    def node(_):
        print(f"Node {name} starting interrupt...")
        resumed_value = interrupt(f"Interrupt from {name}")
        print(f"Node {name} got resume value: {resumed_value}")
        results.append(resumed_value)
        return {"values": [f"{name}:{resumed_value}"]}
    
    node.results = results
    return node


def test_race_condition():
    """Test if multiple nodes can consume the same resume value."""
    
    node1 = create_interrupt_node("A")
    node2 = create_interrupt_node("B")
    
    graph = (
        StateGraph(State)
        .add_node("node1", node1)
        .add_node("node2", node2)
        .add_edge(START, "node1")
        .add_edge(START, "node2")
        .compile(checkpointer=MemorySaver())
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    # First invoke to set up interrupts
    print("=== First invoke ===")
    try:
        graph.invoke({"values": []}, config)
    except:
        pass  # Expected to interrupt
    
    # Resume - this is where the race condition could occur
    print("\n=== Resume with global value ===")
    try:
        result = graph.invoke(Command(resume="SHARED_VALUE"), config)
        print(f"Final result: {result}")
    except Exception as e:
        print(f"Exception during resume: {e}")
    
    print(f"Node A results: {node1.results}")
    print(f"Node B results: {node2.results}")
    
    # Check for the bug
    if len(node1.results) > 0 and len(node2.results) > 0:
        if node1.results[-1] == node2.results[-1] == "SHARED_VALUE":
            print("BUG: Both nodes got the same resume value!")
            return False
        else:
            print("GOOD: Nodes got different values")
            return True
    elif len(node1.results) > 0 or len(node2.results) > 0:
        print("GOOD: Only one node got the resume value")
        return True
    else:
        print("ERROR: No node got the resume value")
        return False


if __name__ == "__main__":
    success = test_race_condition()
    if success:
        print("\nTest PASSED: Resume consumption working correctly")
    else:
        print("\nTest FAILED: Race condition detected")