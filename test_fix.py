#!/usr/bin/env python3
"""
Test to verify that the multiple interruption fix works correctly.
"""

from langgraph.channels import LastValue
from langgraph.pregel import Pregel, Channel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import INTERRUPT


def test_fix_multiple_interrupts():
    """Test that multiple interrupts work after the fix."""
    
    print("=" * 80)
    print("TESTING THE FIX FOR MULTIPLE INTERRUPTS")
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
    
    def step_d(x: int) -> int:
        execution_log.append("d")
        print(f"Executing step D: {x} -> {x+1000}")
        return x + 1000
    
    # Create longer chain: input -> a -> b -> c -> d -> output
    node_a = Channel.subscribe_to("input") | step_a | Channel.write_to("after_a")
    node_b = Channel.subscribe_to("after_a") | step_b | Channel.write_to("after_b")
    node_c = Channel.subscribe_to("after_b") | step_c | Channel.write_to("after_c")
    node_d = Channel.subscribe_to("after_c") | step_d | Channel.write_to("output")
    
    checkpointer = MemorySaver()
    app = Pregel(
        nodes={"a": node_a, "b": node_b, "c": node_c, "d": node_d},
        channels={
            "input": LastValue(int),
            "after_a": LastValue(int),
            "after_b": LastValue(int),
            "after_c": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=checkpointer,
        interrupt_after_nodes=["a", "b", "c"],  # Interrupt after a, b, and c
    )
    
    config = {"configurable": {"thread_id": "test_fix"}}
    
    print("Phase 1: Initial execution - should run A and stop")
    result = app.invoke(1, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    
    # Debug checkpoint state
    checkpoint_tuple = checkpointer.get_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        print(f"Channel versions: {checkpoint['channel_versions']}")
        if INTERRUPT in checkpoint['versions_seen']:
            print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    print()
    
    print("Phase 2: Resume - should run B and stop") 
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    
    # Debug checkpoint state
    checkpoint_tuple = checkpointer.get_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        print(f"Channel versions: {checkpoint['channel_versions']}")
        if INTERRUPT in checkpoint['versions_seen']:
            print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    print()
    
    print("Phase 3: Resume - should run C and stop")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    
    # Debug checkpoint state
    checkpoint_tuple = checkpointer.get_tuple(config)
    if checkpoint_tuple:
        checkpoint = checkpoint_tuple.checkpoint
        print(f"Channel versions: {checkpoint['channel_versions']}")
        if INTERRUPT in checkpoint['versions_seen']:
            print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    print()
    
    print("Phase 4: Resume - should run D and finish")
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
    print(f"Expected: ['a', 'b', 'c', 'd'] with 4 separate invoke() calls")
    
    if execution_log == ['a', 'b', 'c', 'd']:
        print("✅ SUCCESS: All interrupts worked correctly! The fix is working.")
    else:
        print("❌ FAILURE: Interrupts still not working correctly")
    
    # Verify final result
    expected_result = 1 + 1 + 10 + 100 + 1000  # 1112
    actual_result = state.values.get("output")
    
    if actual_result == expected_result:
        print(f"✅ Correct final result: {actual_result}")
    else:
        print(f"❌ Incorrect final result: expected {expected_result}, got {actual_result}")


def test_interrupt_before():
    """Test interrupt_before functionality with the fix."""
    
    print("\n" + "=" * 80)
    print("TESTING INTERRUPT_BEFORE WITH THE FIX")
    print("=" * 80)
    
    execution_log = []
    
    def step_x(x: int) -> int:
        execution_log.append("x")
        print(f"Step X: {x} -> {x*2}")
        return x * 2
    
    def step_y(x: int) -> int:
        execution_log.append("y")
        print(f"Step Y: {x} -> {x*3}")
        return x * 3
    
    def step_z(x: int) -> int:
        execution_log.append("z")
        print(f"Step Z: {x} -> {x*5}")
        return x * 5
    
    node_x = Channel.subscribe_to("input") | step_x | Channel.write_to("after_x")
    node_y = Channel.subscribe_to("after_x") | step_y | Channel.write_to("after_y")
    node_z = Channel.subscribe_to("after_y") | step_z | Channel.write_to("output")
    
    app = Pregel(
        nodes={"x": node_x, "y": node_y, "z": node_z},
        channels={
            "input": LastValue(int),
            "after_x": LastValue(int),
            "after_y": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=MemorySaver(),
        interrupt_before_nodes=["y", "z"],  # Interrupt before y and z
    )
    
    config = {"configurable": {"thread_id": "test_before"}}
    
    print("Step 1: Should run X and stop before Y")
    result = app.invoke(2, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    print()
    
    print("Step 2: Should run Y and stop before Z")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State: {state.values}")
    print(f"Next: {state.next}")
    print()
    
    print("Step 3: Should run Z and finish")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"Final state: {state.values}")
    print(f"Next: {state.next}")
    
    print()
    print("ANALYSIS:")
    print(f"Execution log: {execution_log}")
    print(f"Expected: ['x', 'y', 'z']")
    
    if execution_log == ['x', 'y', 'z']:
        print("✅ SUCCESS: interrupt_before working correctly!")
    else:
        print("❌ FAILURE: interrupt_before not working")
    
    # Check final calculation: 2 * 2 * 3 * 5 = 60
    expected = 2 * 2 * 3 * 5
    actual = state.values.get("output")
    
    if actual == expected:
        print(f"✅ Correct calculation: {actual}")
    else:
        print(f"❌ Wrong calculation: expected {expected}, got {actual}")


if __name__ == "__main__":
    test_fix_multiple_interrupts()
    test_interrupt_before()