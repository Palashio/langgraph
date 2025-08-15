#!/usr/bin/env python3
"""
Test case to reproduce the specific multiple interruption issue mentioned.

This test attempts to reproduce the exact problem: after resuming from an interrupt,
subsequent interrupts are not respected.
"""

from langgraph.channels import LastValue
from langgraph.pregel import Pregel, Channel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START


def test_original_issue():
    """
    Test case that tries to reproduce the exact issue described.
    
    The issue states that after resuming execution, the graph ignores
    interrupt_before and interrupt_after settings.
    """
    
    print("=" * 80)
    print("Testing the original issue: Multiple interrupts after resume")
    print("=" * 80)
    
    # Create a simple graph similar to the one in test_pregel.py
    def add_one(x: int) -> int:
        print(f"add_one called with {x}")
        return x + 1
    
    def add_ten(x: int) -> int:
        print(f"add_ten called with {x}")
        return x + 10
    
    def add_hundred(x: int) -> int:
        print(f"add_hundred called with {x}")
        return x + 100
    
    # Set up nodes
    node_a = Channel.subscribe_to("input") | add_one | Channel.write_to("chan_a")
    node_b = Channel.subscribe_to("chan_a") | add_ten | Channel.write_to("chan_b") 
    node_c = Channel.subscribe_to("chan_b") | add_hundred | Channel.write_to("output")
    
    # Create the Pregel graph
    checkpointer = MemorySaver()
    app = Pregel(
        nodes={"node_a": node_a, "node_b": node_b, "node_c": node_c},
        channels={
            "input": LastValue(int),
            "chan_a": LastValue(int),
            "chan_b": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=checkpointer,
        interrupt_before=["node_b", "node_c"],  # Interrupt before node_b and node_c
    )
    
    config = {"configurable": {"thread_id": "test_1"}}
    
    print(f"Starting with input: 1")
    print()
    
    # Step 1: Start execution - should execute node_a and stop before node_b
    print("Step 1: Start execution (should execute node_a and stop before node_b)")
    result = app.invoke(1, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State values: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 2: Resume - should execute node_b and stop before node_c  
    print("Step 2: Resume (should execute node_b and stop before node_c)")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"State values: {state.values}")
    print(f"Next nodes: {state.next}")
    print()
    
    # Step 3: Resume again - should execute node_c and complete
    print("Step 3: Resume (should execute node_c and complete)")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    state = app.get_state(config)
    print(f"Final state values: {state.values}")
    print(f"Next nodes: {state.next}")
    
    # Check if we got the expected behavior
    expected_final_value = 1 + 1 + 10 + 100  # 112
    actual_final_value = state.values.get("output")
    
    print()
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print(f"Expected final output: {expected_final_value}")
    print(f"Actual final output: {actual_final_value}")
    
    if actual_final_value == expected_final_value:
        print("✅ All nodes executed correctly")
    else:
        print("❌ Unexpected execution path")
    
    # The key test is whether we had exactly 3 invocations with expected interrupts
    if state.next == ():
        print("✅ Graph completed successfully")
    else:
        print(f"❌ Graph did not complete, next nodes: {state.next}")


def test_stream_with_interrupts():
    """Test using stream method to see interrupt behavior more clearly."""
    
    print("\n" + "=" * 80)
    print("Testing stream method with multiple interrupts")
    print("=" * 80)
    
    def simple_func(x: int) -> int:
        print(f"Processing: {x}")
        return x + 1
        
    # Create a longer chain to test more interrupts
    node1 = Channel.subscribe_to("input") | simple_func | Channel.write_to("step1")
    node2 = Channel.subscribe_to("step1") | simple_func | Channel.write_to("step2")
    node3 = Channel.subscribe_to("step2") | simple_func | Channel.write_to("step3")
    node4 = Channel.subscribe_to("step3") | simple_func | Channel.write_to("output")
    
    checkpointer = MemorySaver()
    app = Pregel(
        nodes={"node1": node1, "node2": node2, "node3": node3, "node4": node4},
        channels={
            "input": LastValue(int),
            "step1": LastValue(int),
            "step2": LastValue(int), 
            "step3": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=checkpointer,
        interrupt_after=["node1", "node2", "node3"],  # Interrupt after each node
    )
    
    config = {"configurable": {"thread_id": "test_stream"}}
    
    step_count = 0
    
    # Initial execution
    print(f"Starting stream with input: 10")
    for output in app.stream(10, config):
        step_count += 1
        print(f"Step {step_count} output: {output}")
        state = app.get_state(config)
        print(f"Next nodes: {state.next}")
        print()
        break  # Stop after first output to simulate interrupt
    
    # Resume execution multiple times
    for resume_step in range(1, 4):
        print(f"Resume {resume_step}:")
        step_outputs = []
        for output in app.stream(None, config):
            step_count += 1
            print(f"Step {step_count} output: {output}")
            step_outputs.append(output)
            state = app.get_state(config)
            print(f"Next nodes: {state.next}")
            print()
            break  # Stop after first output to simulate checking interrupt
        
        if not step_outputs:
            print(f"No more outputs at resume {resume_step}")
            break
    
    # Final state
    final_state = app.get_state(config)
    print("=" * 80)
    print("FINAL ANALYSIS")
    print("=" * 80)
    print(f"Final state: {final_state.values}")
    print(f"Steps executed: {step_count}")
    print(f"Expected steps: 4 (one for each node)")
    
    if step_count == 4:
        print("✅ All interrupts respected during stream execution")
    else:
        print(f"❌ Expected 4 steps, got {step_count} - interrupts may not be working")


if __name__ == "__main__":
    test_original_issue()
    test_stream_with_interrupts()