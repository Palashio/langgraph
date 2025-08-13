def test_multiple_interrupts_after_resume():
    """Test that multiple interruptions work correctly after resuming execution.
    
    This test verifies the fix for the issue where subsequent interruptions
    were ignored after resuming execution with stream(None, config).
    """
    from typing import TypedDict
    from langgraph.graph.state import StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    
    class State(TypedDict):
        value: int
        steps: list[str]
    
    def node_a(state: State) -> State:
        return {"value": state["value"] + 1, "steps": state["steps"] + ["node_a"]}
    
    def node_b(state: State) -> State:
        return {"value": state["value"] + 10, "steps": state["steps"] + ["node_b"]}
    
    def node_c(state: State) -> State:
        return {"value": state["value"] + 100, "steps": state["steps"] + ["node_c"]}
    
    # Create a graph with multiple nodes that should interrupt after execution
    workflow = StateGraph(State)
    workflow.add_node("node_a", node_a)
    workflow.add_node("node_b", node_b)
    workflow.add_node("node_c", node_c)
    
    workflow.set_entry_point("node_a")
    workflow.add_edge("node_a", "node_b")
    workflow.add_edge("node_b", "node_c")
    workflow.set_finish_point("node_c")
    
    # Configure interrupts after multiple nodes
    checkpointer = MemorySaver()
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["node_a", "node_b"]
    )
    
    config = {"configurable": {"thread_id": "test_multiple_interrupts"}}
    initial_input = {"value": 0, "steps": []}
    
    # Step 1: Run the graph and hit the first interrupt (after node_a)
    stream_iter = app.stream(initial_input, config)
    chunks = list(stream_iter)
    
    # Should have executed node_a and then interrupted
    assert len(chunks) == 1
    assert "node_a" in chunks[0]
    assert chunks[0]["node_a"]["value"] == 1
    assert chunks[0]["node_a"]["steps"] == ["node_a"]
    
    # Verify the state is correctly saved at the interrupt
    state = app.get_state(config)
    assert state.values["value"] == 1
    assert state.values["steps"] == ["node_a"]
    assert state.next == ("node_b",)  # Should be ready to execute node_b next
    
    # Step 2: Resume execution with stream(None, config) - should hit second interrupt
    stream_iter = app.stream(None, config)
    chunks = list(stream_iter)
    
    # Should have executed node_b and then interrupted again
    assert len(chunks) == 1
    assert "node_b" in chunks[0]
    assert chunks[0]["node_b"]["value"] == 11  # 1 + 10
    assert chunks[0]["node_b"]["steps"] == ["node_a", "node_b"]
    
    # Verify the state is correctly saved at the second interrupt
    state = app.get_state(config)
    assert state.values["value"] == 11
    assert state.values["steps"] == ["node_a", "node_b"]
    assert state.next == ("node_c",)  # Should be ready to execute node_c next
    
    # Step 3: Resume execution again - should complete without interruption
    stream_iter = app.stream(None, config)
    chunks = list(stream_iter)
    
    # Should have executed node_c and completed
    assert len(chunks) == 1
    assert "node_c" in chunks[0]
    assert chunks[0]["node_c"]["value"] == 111  # 11 + 100
    assert chunks[0]["node_c"]["steps"] == ["node_a", "node_b", "node_c"]
    
    # Verify final state
    state = app.get_state(config)
    assert state.values["value"] == 111
    assert state.values["steps"] == ["node_a", "node_b", "node_c"]
    assert state.next == ()  # Should be completed
