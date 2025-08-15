#!/usr/bin/env python3
"""
Regression test for multiple interruption bug.

This test ensures that multiple interrupts work correctly after resuming execution.
The bug was that versions_seen[INTERRUPT] wasn't being updated when interrupts occurred,
causing subsequent interrupts to be ignored.
"""

import pytest
from langgraph.channels import LastValue
from langgraph.pregel import Pregel, Channel
from langgraph.checkpoint.memory import MemorySaver


def test_multiple_interrupt_after_nodes():
    """Test multiple sequential interrupt_after_nodes."""
    
    execution_sequence = []
    
    def step_a(x: int) -> int:
        execution_sequence.append("a")
        return x + 1
    
    def step_b(x: int) -> int:
        execution_sequence.append("b")
        return x + 10
    
    def step_c(x: int) -> int:
        execution_sequence.append("c")
        return x + 100
    
    def step_d(x: int) -> int:
        execution_sequence.append("d")
        return x + 1000
    
    # Create chain: input -> a -> b -> c -> d -> output
    node_a = Channel.subscribe_to("input") | step_a | Channel.write_to("after_a")
    node_b = Channel.subscribe_to("after_a") | step_b | Channel.write_to("after_b")
    node_c = Channel.subscribe_to("after_b") | step_c | Channel.write_to("after_c")
    node_d = Channel.subscribe_to("after_c") | step_d | Channel.write_to("output")
    
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
        checkpointer=MemorySaver(),
        interrupt_after_nodes=["a", "b", "c"],  # Multiple interrupts
    )
    
    config = {"configurable": {"thread_id": "test_multi_interrupt"}}
    
    # Phase 1: Execute step a, should interrupt after
    result1 = app.invoke(5, config)
    assert result1 is None  # Should interrupt, not return final result
    state1 = app.get_state(config)
    assert state1.values["after_a"] == 6  # 5 + 1
    assert state1.next == ("b",)
    
    # Phase 2: Resume, execute step b, should interrupt after
    result2 = app.invoke(None, config)
    assert result2 is None  # Should interrupt again
    state2 = app.get_state(config)
    assert state2.values["after_b"] == 16  # 6 + 10
    assert state2.next == ("c",)
    
    # Phase 3: Resume, execute step c, should interrupt after
    result3 = app.invoke(None, config)
    assert result3 is None  # Should interrupt again
    state3 = app.get_state(config)
    assert state3.values["after_c"] == 116  # 16 + 100
    assert state3.next == ("d",)
    
    # Phase 4: Resume, execute step d, should complete
    result4 = app.invoke(None, config)
    assert result4 == 1116  # 116 + 1000
    state4 = app.get_state(config)
    assert state4.values["output"] == 1116
    assert state4.next == ()
    
    # Verify each step executed exactly once in the correct order
    assert execution_sequence == ["a", "b", "c", "d"]


def test_multiple_interrupt_before_nodes():
    """Test multiple sequential interrupt_before_nodes."""
    
    execution_sequence = []
    
    def step_x(x: int) -> int:
        execution_sequence.append("x")
        return x * 2
    
    def step_y(x: int) -> int:
        execution_sequence.append("y")
        return x * 3
    
    def step_z(x: int) -> int:
        execution_sequence.append("z")
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
        interrupt_before_nodes=["y", "z"],  # Multiple interrupts
    )
    
    config = {"configurable": {"thread_id": "test_before_interrupt"}}
    
    # Phase 1: Execute x, should interrupt before y
    result1 = app.invoke(3, config)
    assert result1 is None
    state1 = app.get_state(config)
    assert state1.values["after_x"] == 6  # 3 * 2
    assert state1.next == ("y",)
    
    # Phase 2: Resume, execute y, should interrupt before z
    result2 = app.invoke(None, config)
    assert result2 is None
    state2 = app.get_state(config)
    assert state2.values["after_y"] == 18  # 6 * 3
    assert state2.next == ("z",)
    
    # Phase 3: Resume, execute z, should complete
    result3 = app.invoke(None, config)
    assert result3 == 90  # 18 * 5
    state3 = app.get_state(config)
    assert state3.values["output"] == 90
    assert state3.next == ()
    
    # Verify execution order
    assert execution_sequence == ["x", "y", "z"]


def test_mixed_interrupt_before_and_after():
    """Test combination of interrupt_before and interrupt_after."""
    
    execution_sequence = []
    
    def step_1(x: int) -> int:
        execution_sequence.append("1")
        return x + 1
    
    def step_2(x: int) -> int:
        execution_sequence.append("2")
        return x + 2
    
    def step_3(x: int) -> int:
        execution_sequence.append("3")
        return x + 3
    
    node_1 = Channel.subscribe_to("input") | step_1 | Channel.write_to("step1")
    node_2 = Channel.subscribe_to("step1") | step_2 | Channel.write_to("step2")
    node_3 = Channel.subscribe_to("step2") | step_3 | Channel.write_to("output")
    
    app = Pregel(
        nodes={"node1": node_1, "node2": node_2, "node3": node_3},
        channels={
            "input": LastValue(int),
            "step1": LastValue(int),
            "step2": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=MemorySaver(),
        interrupt_after_nodes=["node1"],   # Interrupt after node1
        interrupt_before_nodes=["node3"],  # Interrupt before node3
    )
    
    config = {"configurable": {"thread_id": "test_mixed"}}
    
    # Phase 1: Execute node1, interrupt after
    result1 = app.invoke(10, config)
    assert result1 is None
    state1 = app.get_state(config)
    assert state1.values["step1"] == 11  # 10 + 1
    assert state1.next == ("node2",)
    
    # Phase 2: Resume, execute node2, interrupt before node3
    result2 = app.invoke(None, config)
    assert result2 is None
    state2 = app.get_state(config)
    assert state2.values["step2"] == 13  # 11 + 2
    assert state2.next == ("node3",)
    
    # Phase 3: Resume, execute node3, complete
    result3 = app.invoke(None, config)
    assert result3 == 16  # 13 + 3
    state3 = app.get_state(config)
    assert state3.values["output"] == 16
    assert state3.next == ()
    
    # Verify execution order
    assert execution_sequence == ["1", "2", "3"]


if __name__ == "__main__":
    # Run tests directly for debugging
    test_multiple_interrupt_after_nodes()
    print("✅ test_multiple_interrupt_after_nodes passed")
    
    test_multiple_interrupt_before_nodes()
    print("✅ test_multiple_interrupt_before_nodes passed")
    
    test_mixed_interrupt_before_and_after()
    print("✅ test_mixed_interrupt_before_and_after passed")
    
    print("\n🎉 All regression tests passed!")