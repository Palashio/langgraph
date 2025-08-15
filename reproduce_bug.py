#!/usr/bin/env python3
"""
Test case to demonstrate the multiple interruption bug.

This reproduces the exact issue: After resuming execution from an interrupt,
subsequent interrupts don't work because versions_seen[INTERRUPT] isn't updated.
"""

from langgraph.channels import LastValue
from langgraph.pregel import Pregel, Channel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import INTERRUPT


def test_multiple_interrupts_bug():
    """Reproduce the multiple interruption bug."""
    
    print("=" * 80)
    print("REPRODUCING THE MULTIPLE INTERRUPTION BUG")
    print("=" * 80)
    
    execution_log = []
    
    def step_a(x: int) -> int:
        execution_log.append("a")
        print(f"Executing step A: {x} -> {x+1}")
        return x + 1
    
    def step_b(x: int) -> int:
        execution_log.append("b")
        print(f"Executing step B: {x} -> {x+10}")
        return x + 10
    
    def step_c(x: int) -> int:
        execution_log.append("c")
        print(f"Executing step C: {x} -> {x+100}")
        return x + 100
    
    # Create linear chain: input -> a -> b -> c -> output
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
        interrupt_after_nodes=["a", "b"],  # Interrupt after both a and b
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    print("Phase 1: Initial execution - should run A and stop")
    result = app.invoke(5, config)
    print(f"Result: {result}")
    
    # Check internal state 
    checkpoint_tuple = checkpointer.get_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        print(f"Channel versions: {checkpoint['channel_versions']}")
        versions_seen = checkpoint['versions_seen']
        if INTERRUPT in versions_seen:
            print(f"Versions seen by INTERRUPT: {versions_seen[INTERRUPT]}")
        else:
            print("No versions_seen[INTERRUPT] yet")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    print()
    
    print("Phase 2: Resume - should run B and stop")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    # Check internal state after resume
    checkpoint_tuple = checkpointer.get_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        print(f"Channel versions: {checkpoint['channel_versions']}")
        versions_seen = checkpoint['versions_seen']
        if INTERRUPT in versions_seen:
            print(f"Versions seen by INTERRUPT: {versions_seen[INTERRUPT]}")
        else:
            print("No versions_seen[INTERRUPT] yet")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    print()
    
    print("Phase 3: Resume - should run C and finish")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"Final state: {state.values}")
    print(f"Next: {state.next}")
    
    print()
    print("=" * 80)
    print("ANALYSIS:")
    print("=" * 80)
    print(f"Execution log: {execution_log}")
    print(f"Expected: ['a', 'b', 'c'] with 3 separate invoke() calls")
    print(f"Actual: {execution_log}")
    
    # Count how many times we had to call invoke()
    if len(execution_log) == 3 and execution_log == ['a', 'b', 'c']:
        print("✅ SUCCESS: All interrupts worked correctly")
    elif len(execution_log) == 3:
        print("❌ FAILURE: Interrupts didn't work - all steps executed at once")
        print("This demonstrates the bug!")
    else:
        print(f"❌ UNEXPECTED: Got {len(execution_log)} executions instead of 3")


def test_simpler_case():
    """Test the simplest possible case to isolate the issue."""
    
    print("\n" + "=" * 80)
    print("TESTING SIMPLEST CASE")
    print("=" * 80)
    
    def add_one(x: int) -> int:
        print(f"add_one: {x} -> {x+1}")
        return x + 1
    
    # Two-step chain
    step1 = Channel.subscribe_to("input") | add_one | Channel.write_to("middle")
    step2 = Channel.subscribe_to("middle") | add_one | Channel.write_to("output")
    
    app = Pregel(
        nodes={"step1": step1, "step2": step2},
        channels={
            "input": LastValue(int),
            "middle": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=MemorySaver(),
        interrupt_after_nodes=["step1"],  # Interrupt after step1
    )
    
    config = {"configurable": {"thread_id": "simple"}}
    
    print("Part 1: Execute step1 and interrupt")
    result1 = app.invoke(10, config)
    print(f"Result1: {result1}")
    
    state = app.get_state(config)
    print(f"State after part 1: {state.values}")
    print(f"Next: {state.next}")
    
    print("\nPart 2: Resume and execute step2")
    result2 = app.invoke(None, config)
    print(f"Result2: {result2}")
    
    state = app.get_state(config)
    print(f"Final state: {state.values}")
    print(f"Next: {state.next}")
    
    # Expected: result1 should be None (interrupt), result2 should be 12
    if result1 is None and result2 == 12:
        print("✅ SUCCESS: Simple interrupt worked")
    else:
        print(f"❌ FAILURE: Expected None then 12, got {result1} then {result2}")


if __name__ == "__main__":
    test_simpler_case()
    test_multiple_interrupts_bug()