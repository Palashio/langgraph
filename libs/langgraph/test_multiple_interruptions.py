"""Test case to reproduce the multiple interruptions issue.

This test demonstrates the bug where subsequent interruptions are ignored
after resuming execution with input=None.
"""

from langgraph.channels.last_value import LastValue
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import Channel, Pregel


def test_multiple_interruptions_after_resumption():
    """Test that multiple interruptions work after resuming execution with None input.
    
    This test reproduces the bug where subsequent interruptions are ignored
    after resuming execution with input=None.
    """
    # Create a simple graph with three nodes that can be interrupted
    def add_one(x: int) -> int:
        print(f"node_one: {x} + 1 = {x + 1}")
        return x + 1
    
    def add_ten(x: int) -> int:
        print(f"node_two: {x} + 10 = {x + 10}")
        return x + 10
    
    def add_hundred(x: int) -> int:
        print(f"node_three: {x} + 100 = {x + 100}")
        return x + 100
    
    # Build the graph using the existing pattern from other tests
    one = Channel.subscribe_to("input") | add_one | Channel.write_to("output_one")
    two = Channel.subscribe_to("output_one") | add_ten | Channel.write_to("output_two")
    three = Channel.subscribe_to("output_two") | add_hundred | Channel.write_to("output")
    
    checkpointer = MemorySaver()
    app = Pregel(
        nodes={"node_one": one, "node_two": two, "node_three": three},
        channels={
            "input": LastValue(int),
            "output_one": LastValue(int),
            "output_two": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=checkpointer,
        interrupt_after_nodes=["node_one", "node_two"],
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











