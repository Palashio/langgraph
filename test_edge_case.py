#!/usr/bin/env python3
"""
Test to demonstrate the edge case where interrupts don't work after resuming.
"""

from langgraph.channels import LastValue
from langgraph.pregel import Pregel, Channel
from langgraph.checkpoint.memory import MemorySaver


def test_edge_case():
    """Test multiple interrupts in sequence."""
    
    print("=" * 80)
    print("Testing multiple sequential interrupts")
    print("=" * 80)
    
    counter = {"value": 0}
    
    def step_a(x: int) -> int:
        counter["value"] += 1
        print(f"step_a executed (call #{counter['value']}): {x} -> {x+10}")
        return x + 10
    
    def step_b(x: int) -> int:
        counter["value"] += 1
        print(f"step_b executed (call #{counter['value']}): {x} -> {x+100}")
        return x + 100
    
    def step_c(x: int) -> int:
        counter["value"] += 1
        print(f"step_c executed (call #{counter['value']}): {x} -> {x+1000}")
        return x + 1000
    
    # Build graph: input -> a -> b -> c -> output
    node_a = Channel.subscribe_to("input") | step_a | Channel.write_to("after_a")
    node_b = Channel.subscribe_to("after_a") | step_b | Channel.write_to("after_b")
    node_c = Channel.subscribe_to("after_b") | step_c | Channel.write_to("output")
    
    checkpointer = MemorySaver()
    app = Pregel(
        nodes={"a": node_a, "b": node_b, "c": node_c},
        channels={
            "input": LastValue(int),
            "after_a": LastValue(int),
            "after_b": LastValue(int), 
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=checkpointer,
        interrupt_after=["a", "b"],  # Interrupt after a and b
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    print("Phase 1: Initial execution (should run 'a' and interrupt)")
    results = list(app.stream(1, config))
    print(f"Results: {results}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    print()
    
    print("Phase 2: Resume (should run 'b' and interrupt)")
    results = list(app.stream(None, config))
    print(f"Results: {results}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    print()
    
    print("Phase 3: Resume (should run 'c' and finish)")
    results = list(app.stream(None, config))
    print(f"Results: {results}")
    
    state = app.get_state(config)
    print(f"Final state: {state.values}")
    print(f"Next: {state.next}")
    
    print()
    print("=" * 80)
    print("Analysis:")
    print(f"Total function calls: {counter['value']}")
    print("Expected: 3 calls (a, then b, then c)")
    
    if counter["value"] == 3:
        print("✅ SUCCESS: Each function called exactly once - interrupts working correctly")
    else:
        print(f"❌ FAILURE: Expected 3 calls, got {counter['value']} - interrupts not working correctly")
    
    expected_final = 1 + 10 + 100 + 1000  # 1111
    actual_final = state.values.get("output", 0)
    
    print(f"Expected final output: {expected_final}")
    print(f"Actual final output: {actual_final}")
    
    if actual_final == expected_final:
        print("✅ Correct final result")
    else:
        print("❌ Incorrect final result")


if __name__ == "__main__":
    test_edge_case()