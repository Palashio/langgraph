"""Test case to demonstrate the multiple interruption issue."""

import pytest
from pytest_mock import MockerFixture

from langgraph.channels.last_value import LastValue
from langgraph.pregel import Channel, Pregel
from tests.memory_assert import MemorySaverAssertImmutable


def test_multiple_interruptions_after_resuming(mocker: MockerFixture) -> None:
    """Test that a graph can be interrupted multiple times after resuming execution."""
    add_one = mocker.Mock(side_effect=lambda x: x + 1)
    one = Channel.subscribe_to("input") | add_one | Channel.write_to("inbox")
    two = Channel.subscribe_to("inbox") | add_one | Channel.write_to("output")

    memory = MemorySaverAssertImmutable()
    app = Pregel(
        nodes={"one": one, "two": two},
        channels={
            "inbox": LastValue(int),
            "output": LastValue(int),
            "input": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=memory,
        interrupt_after_nodes=["one"],
    )

    # First execution: start and interrupt after node "one"
    assert app.invoke(10, {"configurable": {"thread_id": 1}}) is None
    
    # Verify we're interrupted after node "one"
    checkpoint = memory.get({"configurable": {"thread_id": 1}})
    assert checkpoint is not None
    assert checkpoint["channel_values"]["inbox"] == 11  # 10 + 1
    
    # Resume execution - this should complete
    assert app.invoke(None, {"configurable": {"thread_id": 1}}) == 12  # 11 + 1
    
    # Second execution: start new execution and interrupt again
    # This should interrupt after node "one" again, but currently fails due to the bug
    result = app.invoke(20, {"configurable": {"thread_id": 1}})
    print(f"Second execution result: {result}")
    
    # This assertion will fail with the current bug - the graph doesn't interrupt
    # Instead it completes execution and returns 22 (20 + 1 + 1)
    assert result is None, "Expected interruption after node 'one', but execution completed"
    
    # Verify we're interrupted after node "one" again
    checkpoint = memory.get({"configurable": {"thread_id": 1}})
    assert checkpoint is not None
    assert checkpoint["channel_values"]["inbox"] == 21  # 20 + 1
    
    # Resume execution again - this should complete
    assert app.invoke(None, {"configurable": {"thread_id": 1}}) == 22  # 21 + 1
    
    # Third execution: test multiple interruptions in sequence
    # Start execution and interrupt
    assert app.invoke(30, {"configurable": {"thread_id": 1}}) is None
    
    # Verify interruption
    checkpoint = memory.get({"configurable": {"thread_id": 1}})
    assert checkpoint is not None
    assert checkpoint["channel_values"]["inbox"] == 31  # 30 + 1
    
    # Resume and complete
    assert app.invoke(None, {"configurable": {"thread_id": 1}}) == 32  # 31 + 1


if __name__ == "__main__":
    # Run the test to demonstrate the issue
    import sys
    sys.path.append("/home/daytona/langgraph/libs/langgraph")
    
    from unittest.mock import Mock
    
    # Create a mock fixture
    class MockFixture:
        def Mock(self, **kwargs):
            return Mock(**kwargs)
    
    mocker = MockFixture()
    
    try:
        test_multiple_interruptions_after_resuming(mocker)
        print("Test passed - multiple interruptions work correctly")
    except AssertionError as e:
        print(f"Test failed as expected: {e}")
        print("This demonstrates the multiple interruption bug")
    except Exception as e:
        print(f"Unexpected error: {e}")
