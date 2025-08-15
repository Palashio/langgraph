#!/usr/bin/env python3
"""
Test case to reproduce the multiple interruption issue.

The issue: Once the graph resumes execution after an interruption, it continues 
executing without respecting further `interrupt_before` and `interrupt_after` 
settings, effectively ignoring additional interrupts.
"""

from typing import Any
from langgraph.channels import LastValue
from langgraph.graph import StateGraph
from langgraph.pregel import Channel
from langgraph.checkpoint.memory import MemorySaver


def create_test_graph():
    """Creates a simple graph with multiple nodes for testing interruptions."""
    
    def node_a(state: dict) -> dict:
        print(f"Executing node_a with state: {state}")
        return {"value": state["value"] + 1, "history": state.get("history", []) + ["a"]}
    
    def node_b(state: dict) -> dict:
        print(f"Executing node_b with state: {state}")
        return {"value": state["value"] + 10, "history": state.get("history", []) + ["b"]}
    
    def node_c(state: dict) -> dict:
        print(f"Executing node_c with state: {state}")
        return {"value": state["value"] + 100, "history": state.get("history", []) + ["c"]}
    
    # Create a simple state graph
    graph = StateGraph(dict)
    graph.add_node("node_a", node_a)
    graph.add_node("node_b", node_b)
    graph.add_node("node_c", node_c)
    
    # Set up the flow: START -> node_a -> node_b -> node_c
    graph.set_entry_point("node_a")
    graph.add_edge("node_a", "node_b")
    graph.add_edge("node_b", "node_c")
    graph.set_finish_point("node_c")
    
    return graph


def test_multiple_interrupts():
    """Test multiple interruptions in a single execution path."""
    
    print("=" * 60)
    print("Testing Multiple Interruptions")
    print("=" * 60)
    
    # Create graph with checkpointer and interrupt settings
    graph = create_test_graph()
    checkpointer = MemorySaver()
    
    # Compile with interrupts before each node
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["node_a", "node_b", "node_c"]
    )
    
    config = {"configurable": {"thread_id": "test_thread"}}
    initial_state = {"value": 0, "history": []}
    
    print(f"Initial state: {initial_state}")
    print()
    
    # Step 1: Start execution - should interrupt before node_a
    print("Step 1: Starting execution (should interrupt before node_a)")
    result = list(app.stream(initial_state, config))
    print(f"Result after step 1: {result}")
    
    state = app.get_state(config)
    print(f"Current state: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 2: Resume execution - should execute node_a and interrupt before node_b
    print("Step 2: Resume execution (should execute node_a and interrupt before node_b)")
    result = list(app.stream(None, config))
    print(f"Result after step 2: {result}")
    
    state = app.get_state(config)
    print(f"Current state: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 3: Resume execution again - should execute node_b and interrupt before node_c
    print("Step 3: Resume execution (should execute node_b and interrupt before node_c)")
    result = list(app.stream(None, config))
    print(f"Result after step 3: {result}")
    
    state = app.get_state(config)
    print(f"Current state: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 4: Resume execution final time - should execute node_c and finish
    print("Step 4: Resume execution (should execute node_c and finish)")
    result = list(app.stream(None, config))
    print(f"Result after step 4: {result}")
    
    state = app.get_state(config)
    print(f"Final state: {state.values}")
    print(f"Next nodes: {state.next}")
    
    # Verify that we got the expected interruptions
    expected_history = ["a", "b", "c"]
    actual_history = state.values.get("history", [])
    
    print()
    print("=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print(f"Expected execution history: {expected_history}")
    print(f"Actual execution history: {actual_history}")
    
    if actual_history == expected_history and len(actual_history) == 3:
        print("✅ SUCCESS: All nodes executed and were properly interrupted")
    else:
        print("❌ FAILURE: Interrupts were not working as expected")
        print("This demonstrates the multiple interruption bug!")


def test_interrupt_after():
    """Test multiple interruptions using interrupt_after."""
    
    print("\n" + "=" * 60)
    print("Testing Multiple Interruptions with interrupt_after")
    print("=" * 60)
    
    # Create graph with checkpointer and interrupt settings
    graph = create_test_graph()
    checkpointer = MemorySaver()
    
    # Compile with interrupts after each node
    app = graph.compile(
        checkpointer=checkpointer,
        interrupt_after=["node_a", "node_b"]  # Don't interrupt after node_c since it's the last
    )
    
    config = {"configurable": {"thread_id": "test_thread_after"}}
    initial_state = {"value": 0, "history": []}
    
    print(f"Initial state: {initial_state}")
    print()
    
    # Step 1: Start execution - should execute node_a and interrupt after
    print("Step 1: Starting execution (should execute node_a and interrupt after)")
    result = list(app.stream(initial_state, config))
    print(f"Result after step 1: {result}")
    
    state = app.get_state(config)
    print(f"Current state: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 2: Resume execution - should execute node_b and interrupt after
    print("Step 2: Resume execution (should execute node_b and interrupt after)")
    result = list(app.stream(None, config))
    print(f"Result after step 2: {result}")
    
    state = app.get_state(config)
    print(f"Current state: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 3: Resume execution - should execute node_c and finish
    print("Step 3: Resume execution (should execute node_c and finish)")
    result = list(app.stream(None, config))
    print(f"Result after step 3: {result}")
    
    state = app.get_state(config)
    print(f"Final state: {state.values}")
    print(f"Next nodes: {state.next}")
    
    expected_history = ["a", "b", "c"]
    actual_history = state.values.get("history", [])
    
    print()
    print("=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print(f"Expected execution history: {expected_history}")
    print(f"Actual execution history: {actual_history}")
    
    if actual_history == expected_history and len(actual_history) == 3:
        print("✅ SUCCESS: All nodes executed and were properly interrupted")
    else:
        print("❌ FAILURE: Interrupts were not working as expected")
        print("This demonstrates the multiple interruption bug!")


if __name__ == "__main__":
    test_multiple_interrupts()
    test_interrupt_after()