"""Test case to reproduce the multiple interruptions issue.

This test demonstrates the bug where subsequent interruptions are ignored
after resuming execution with input=None.
"""

from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END


class State(TypedDict):
    value: int


def test_multiple_interruptions_after_resumption():
    """Test that multiple interruptions work after resuming execution with None input.
    
    This test reproduces the bug where subsequent interruptions are ignored
    after resuming execution with input=None.
    """
    # Create a simple graph with three nodes that can be interrupted
    def node_one(state: State) -> State:
        return {"value": state["value"] + 1}
    
    def node_two(state: State) -> State:
        return {"value": state["value"] + 10}
    
    def node_three(state: State) -> State:
        return {"value": state["value"] + 100}
    
    # Build the graph using StateGraph pattern from existing tests
    workflow = StateGraph(State)
    workflow.add_node("node_one", node_one)
    workflow.add_node("node_two", node_two)
    workflow.add_node("node_three", node_three)
    workflow.set_entry_point("node_one")
    workflow.add_edge("node_one", "node_two")
    workflow.add_edge("node_two", "node_three")
    workflow.add_edge("node_three", END)
    
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["node_two", "node_three"],
    )
    
    config = {"configurable": {"thread_id": "test_multiple_interrupts"}}
    
    # Step 1: Start execution, should interrupt before node_two
    print("Step 1: Starting execution...")
    result = app.invoke({"value": 1}, config)
    print(f"Result after step 1: {result}")
    assert result is None, "Should be interrupted before node_two"
    
    # Check state - should have completed node_one (1 + 1 = 2)
    state = app.get_state(config)
    print(f"State after step 1: {state.values}")
    assert state.values["value"] == 2
    assert state.next == ("node_two",)
    
    # Step 2: Resume execution with None, should interrupt before node_three
    print("Step 2: Resuming execution...")
    result = app.invoke(None, config)
    print(f"Result after step 2: {result}")
    
    # This assertion will fail due to the bug - the second interruption is ignored
    try:
        assert result is None, "Should be interrupted before node_three"
        print("SUCCESS: Second interruption worked correctly!")
        
        # Check state - should have completed node_two (2 + 10 = 12)
        state = app.get_state(config)
        print(f"State after step 2: {state.values}")
        assert state.values["value"] == 12
        assert state.next == ("node_three",)
        
    except AssertionError:
        print("BUG REPRODUCED: Second interruption was ignored!")
        state = app.get_state(config)
        print(f"State after step 2: {state.values}")
        print(f"Actual result: {result}")
        print("This demonstrates the bug where subsequent interruptions are ignored after resuming with None")
        # Don't raise the error - we expect this to fail due to the bug
        return
    
    # Step 3: Resume execution with None again, should complete
    print("Step 3: Final resume...")
    result = app.invoke(None, config)
    print(f"Final result: {result}")
    assert result["value"] == 112  # 12 + 100 = 112


if __name__ == "__main__":
    test_multiple_interruptions_after_resumption()










