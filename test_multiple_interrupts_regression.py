#!/usr/bin/env python3

"""
Test to reproduce the issue where parallel subgraph calls can use the same global resume value.

The issue occurs when:
1. A parent graph has multiple nodes that call subgraphs
2. Both subgraphs have interrupts
3. The parent graph is resumed with a global resume value
4. Both subgraph tasks might try to consume the same resume value

This test demonstrates the race condition where both parallel tasks
might access the same null_resume value before it gets consumed.
"""

import asyncio
from typing import TypedDict
from typing_extensions import Annotated
from operator import add

from langgraph.graph import StateGraph, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver


class ParentState(TypedDict):
    values: Annotated[list[str], add]


class SubgraphState(TypedDict):
    subvalue: str


def create_subgraph(name: str) -> StateGraph:
    """Create a subgraph that has an interrupt."""
    
    def subgraph_node(state: SubgraphState):
        print(f"Subgraph {name} executing...")
        resumed_value = interrupt(f"Need input for {name}")
        return {"subvalue": f"{name}:{resumed_value}"}
    
    return (
        StateGraph(SubgraphState)
        .add_node("sub_node", subgraph_node)
        .add_edge(START, "sub_node")
        .compile(checkpointer=True)
    )


def test_parallel_subgraph_resume_consumption():
    """Test that parallel subgraph calls don't consume the same resume value."""
    
    # Create two subgraphs
    subgraph1 = create_subgraph("sub1") 
    subgraph2 = create_subgraph("sub2")
    
    def call_subgraph1(state: ParentState):
        print("Calling subgraph1...")
        result = subgraph1.invoke({"subvalue": ""})
        return {"values": [f"sub1:{result['subvalue']}"]}
    
    def call_subgraph2(state: ParentState):
        print("Calling subgraph2...")  
        result = subgraph2.invoke({"subvalue": ""})
        return {"values": [f"sub2:{result['subvalue']}"]} 
    
    # Create parent graph with parallel subgraph calls
    parent = (
        StateGraph(ParentState)
        .add_node("node1", call_subgraph1)
        .add_node("node2", call_subgraph2)
        .add_edge(START, "node1")
        .add_edge(START, "node2")
        .compile(checkpointer=MemorySaver())
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    try:
        # First invoke - should trigger interrupts in both subgraphs
        print("First invoke...")
        result = parent.invoke({"values": []}, config)
        print(f"First result: {result}")
        
        # Resume with a global value - this is where the bug occurs
        print("Resuming with global value...")
        result = parent.invoke(Command(resume="global_resume_value"), config)
        print(f"Resume result: {result}")
        
        # The bug: both subgraphs might get the same resume value
        # Expected: each subgraph should get its own resume value or handle this gracefully
        # Actual: race condition where both might consume the same value
        
        print("Test completed successfully")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        raise


if __name__ == "__main__":
    test_parallel_subgraph_resume_consumption()