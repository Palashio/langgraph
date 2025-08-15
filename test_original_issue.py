#!/usr/bin/env python3
"""
Test to reproduce the exact issue described in the GitHub issue.
"""

from langgraph.channels import LastValue
from langgraph.pregel import Pregel, Channel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import INTERRUPT


def test_interrupt_versions_tracking():
    """Test to verify the root cause of the interrupt issue."""
    
    print("=" * 80)
    print("Testing versions_seen[INTERRUPT] tracking")
    print("=" * 80)
    
    def add_one(x: int) -> int:
        print(f"add_one: {x} -> {x+1}")
        return x + 1
    
    # Simple linear chain: input -> a -> b -> output
    node_a = Channel.subscribe_to("input") | add_one | Channel.write_to("intermediate")
    node_b = Channel.subscribe_to("intermediate") | add_one | Channel.write_to("output")
    
    checkpointer = MemorySaver()
    app = Pregel(
        nodes={"a": node_a, "b": node_b},
        channels={
            "input": LastValue(int),
            "intermediate": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=checkpointer,
        interrupt_before=["b"],  # Interrupt before node b
    )
    
    config = {"configurable": {"thread_id": "debug"}}
    
    print("Step 1: Execute node_a and interrupt before node_b")
    result = app.invoke(5, config)
    print(f"Result: {result}")
    
    # Check checkpoint state
    checkpoint_tuple = checkpointer.get_tuple(config)
    checkpoint = checkpoint_tuple.checkpoint
    
    print(f"Channel versions: {checkpoint['channel_versions']}")
    print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    print()
    
    print("Step 2: Resume execution")
    result = app.invoke(None, config)
    print(f"Result: {result}")
    
    # Check checkpoint state again
    checkpoint_tuple = checkpointer.get_tuple(config)
    checkpoint = checkpoint_tuple.checkpoint
    
    print(f"Channel versions: {checkpoint['channel_versions']}")
    print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    print()
    
    print("Now let's test multiple interrupts...")
    print()
    
    # Create a longer chain to test multiple interrupts
    def process(x: int) -> int:
        print(f"process: {x} -> {x+1}")
        return x + 1
    
    node1 = Channel.subscribe_to("input") | process | Channel.write_to("step1")
    node2 = Channel.subscribe_to("step1") | process | Channel.write_to("step2")
    node3 = Channel.subscribe_to("step2") | process | Channel.write_to("output")
    
    app2 = Pregel(
        nodes={"node1": node1, "node2": node2, "node3": node3},
        channels={
            "input": LastValue(int),
            "step1": LastValue(int),
            "step2": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=MemorySaver(),
        interrupt_before=["node2", "node3"],  # Interrupt before both node2 and node3
    )
    
    config2 = {"configurable": {"thread_id": "multi"}}
    
    print("Multi-interrupt test:")
    print("Step 1: Execute node1 and interrupt before node2")
    result = app2.invoke(10, config2)
    print(f"Result: {result}")
    
    checkpoint_tuple = app2.checkpointer.get_tuple(config2)
    checkpoint = checkpoint_tuple.checkpoint
    print(f"Channel versions: {checkpoint['channel_versions']}")
    print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    print()
    
    print("Step 2: Resume and try to interrupt before node3")
    result = app2.invoke(None, config2)
    print(f"Result: {result}")
    
    checkpoint_tuple = app2.checkpointer.get_tuple(config2)
    checkpoint = checkpoint_tuple.checkpoint
    print(f"Channel versions: {checkpoint['channel_versions']}")
    print(f"Versions seen by INTERRUPT: {checkpoint['versions_seen'][INTERRUPT]}")
    
    state = app2.get_state(config2)
    print(f"Next tasks: {state.next}")
    
    if len(state.next) > 0:
        print("✅ SUCCESS: Second interrupt worked!")
    else:
        print("❌ FAILURE: Second interrupt did not work - this demonstrates the bug!")


if __name__ == "__main__":
    test_interrupt_versions_tracking()