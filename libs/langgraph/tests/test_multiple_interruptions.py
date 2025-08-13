"""Test case to reproduce the multiple interruption issue.

This test demonstrates the problem where a graph cannot be interrupted multiple times
after resuming execution because versions_seen[INTERRUPT] is incorrectly updated when resuming.
"""

import pytest
from pytest_mock import MockerFixture

from langgraph.channels.last_value import LastValue
from langgraph.pregel import Channel, Pregel
from tests.memory_assert import MemorySaverAssertImmutable


def test_multiple_interruptions_after_resuming(mocker: MockerFixture) -> None:
    """Test that a graph can be interrupted multiple times after resuming execution.

    This test reproduces the issue where after resuming execution from an interrupt,
    the graph cannot be interrupted again because versions_seen[INTERRUPT] is
    incorrectly updated when resuming.
    """
    # Create mock functions to track execution
    add_one = mocker.Mock(side_effect=lambda x: x + 1)
    add_two = mocker.Mock(side_effect=lambda x: x + 2)

    # Create nodes that will be interrupted
    node_one = Channel.subscribe_to("input") | add_one | Channel.write_to("value")
    node_two = Channel.subscribe_to("value") | add_two | Channel.write_to("output")

    memory = MemorySaverAssertImmutable()
    app = Pregel(
        nodes={"node_one": node_one, "node_two": node_two},
        channels={
            "input": LastValue(int),
            "value": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=memory,
        interrupt_before_nodes=["node_two"],  # Interrupt before node_two
    )

    config = {"configurable": {"thread_id": "test_multiple_interrupts"}}

    # First execution: start and interrupt before node_two
    result = app.invoke(10, config)
    assert result is None  # Should be None because of interrupt

    # Check that node_one executed but node_two didn't
    assert add_one.call_count == 1
    assert add_two.call_count == 0

    # Check intermediate state
    state = app.get_state(config)
    assert state.values["value"] == 11  # 10 + 1
    assert "output" not in state.values or state.values["output"] is None
    assert state.next == ("node_two",)  # node_two should be next

    # Resume execution - this should complete
    result = app.invoke(None, config)
    assert result == 13  # 11 + 2
    assert add_one.call_count == 1  # Still 1, not called again
    assert add_two.call_count == 1  # Now called once

    # Reset mocks for second test
    add_one.reset_mock()
    add_two.reset_mock()

    # Second execution: start again and interrupt before node_two
    # This should work the same as the first time
    result = app.invoke(20, config)
    assert result is None  # Should be None because of interrupt

    # Check that node_one executed but node_two didn't
    assert add_one.call_count == 1
    assert add_two.call_count == 0

    # Check intermediate state
    state = app.get_state(config)
    assert state.values["value"] == 21  # 20 + 1
    assert state.values["output"] == 13  # Previous output still there
    assert state.next == ("node_two",)  # node_two should be next

    # Resume execution again - this should complete
    result = app.invoke(None, config)
    assert result == 23  # 21 + 2
    assert add_one.call_count == 1  # Still 1, not called again
    assert add_two.call_count == 1  # Now called once

    # Reset mocks for third test - this is where the bug manifests
    add_one.reset_mock()
    add_two.reset_mock()

    # Third execution: This should interrupt again, but currently doesn't due to the bug
    result = app.invoke(30, config)

    # BUG: Currently this returns 33 instead of None because the interrupt doesn't work
    # After the fix, this should be None (interrupted)
    # For now, we'll document the current broken behavior
    if result is None:
        # This is the expected behavior after the fix
        assert add_one.call_count == 1
        assert add_two.call_count == 0

        state = app.get_state(config)
        assert state.values["value"] == 31  # 30 + 1
        assert state.next == ("node_two",)  # node_two should be next

        # Resume execution
        result = app.invoke(None, config)
        assert result == 33  # 31 + 2
        assert add_two.call_count == 1
    else:
        # This is the current broken behavior - execution doesn't interrupt
        # Both nodes execute without interruption
        assert result == 33  # 30 + 1 + 2
        assert add_one.call_count == 1
        assert add_two.call_count == 1

        # This demonstrates the bug: the graph should have interrupted but didn't
        pytest.fail(
            "BUG REPRODUCED: Graph should have interrupted before node_two on third execution, "
            "but it executed both nodes without interruption. This demonstrates the issue where "
            "multiple interruptions don't work after resuming execution."
        )


def test_multiple_interruptions_after_resuming_with_interrupt_after(
    mocker: MockerFixture,
) -> None:
    """Test multiple interruptions with interrupt_after_nodes.

    This test verifies the same issue exists with interrupt_after_nodes.
    """
    # Create mock functions to track execution
    add_one = mocker.Mock(side_effect=lambda x: x + 1)
    add_two = mocker.Mock(side_effect=lambda x: x + 2)

    # Create nodes that will be interrupted
    node_one = Channel.subscribe_to("input") | add_one | Channel.write_to("value")
    node_two = Channel.subscribe_to("value") | add_two | Channel.write_to("output")

    memory = MemorySaverAssertImmutable()
    app = Pregel(
        nodes={"node_one": node_one, "node_two": node_two},
        channels={
            "input": LastValue(int),
            "value": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=memory,
        interrupt_after_nodes=["node_one"],  # Interrupt after node_one
    )

    config = {"configurable": {"thread_id": "test_multiple_interrupts_after"}}

    # First execution: start and interrupt after node_one
    result = app.invoke(10, config)
    assert result is None  # Should be None because of interrupt

    # Check that node_one executed but node_two didn't
    assert add_one.call_count == 1
    assert add_two.call_count == 0

    # Check intermediate state
    state = app.get_state(config)
    assert state.values["value"] == 11  # 10 + 1
    assert "output" not in state.values or state.values["output"] is None
    assert state.next == ("node_two",)  # node_two should be next

    # Resume execution - this should complete
    result = app.invoke(None, config)
    assert result == 13  # 11 + 2
    assert add_one.call_count == 1  # Still 1, not called again
    assert add_two.call_count == 1  # Now called once

    # Reset mocks for second test
    add_one.reset_mock()
    add_two.reset_mock()

    # Second execution: This should interrupt again after node_one, but currently doesn't
    result = app.invoke(20, config)

    # BUG: This should be None (interrupted after node_one) but currently returns 23
    if result is None:
        # This is the expected behavior after the fix
        assert add_one.call_count == 1
        assert add_two.call_count == 0

        state = app.get_state(config)
        assert state.values["value"] == 21  # 20 + 1
        assert state.next == ("node_two",)  # node_two should be next

        # Resume execution
        result = app.invoke(None, config)
        assert result == 23  # 21 + 2
        assert add_two.call_count == 1
    else:
        # This is the current broken behavior - execution doesn't interrupt
        assert result == 23  # 20 + 1 + 2
        assert add_one.call_count == 1
        assert add_two.call_count == 1

        # This demonstrates the bug
        pytest.fail(
            "BUG REPRODUCED: Graph should have interrupted after node_one on second execution, "
            "but it executed both nodes without interruption. This demonstrates the issue where "
            "multiple interruptions don't work after resuming execution."
        )
