#!/usr/bin/env python3
"""Test to verify the sync task timing fix."""

import concurrent.futures
import threading
import time
from unittest.mock import Mock

# Import the fixed FuturesDict
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs/langgraph'))

from langgraph.pregel.runner import FuturesDict
from langgraph.types import PregelExecutableTask


def test_sync_timing_issue():
    """Test that sync tasks don't complete prematurely when multiple tasks are scheduled."""
    
    # Create a mock callback and event
    callback = Mock()
    event = threading.Event()
    
    # Create FuturesDict
    futures_dict = FuturesDict(
        event=event,
        callback=callback,
        future_type=concurrent.futures.Future,
    )
    
    # Create mock tasks
    task1 = Mock(spec=PregelExecutableTask)
    task1.id = "task1"
    task2 = Mock(spec=PregelExecutableTask)
    task2.id = "task2"
    
    # Create futures
    future1 = concurrent.futures.Future()
    future2 = concurrent.futures.Future()
    
    # Add first task and complete it immediately (simulating fast sync task)
    futures_dict[future1] = task1
    future1.set_result("result1")
    
    # Wait a moment for the first callback to execute
    time.sleep(0.01)
    
    # Before the fix, this would have set the event because counter was 0
    # After the fix, adding a new task should clear the event
    initial_event_state = event.is_set()
    
    # Add second task - this should clear the event if it was set
    futures_dict[future2] = task2
    
    # Check if event was cleared when second task was added
    if initial_event_state:
        assert not event.is_set(), "Event should be cleared when new task is added"
    
    # Complete second task
    future2.set_result("result2")
    
    # Wait for event to be set (both tasks should be done)
    event.wait(timeout=1.0)
    
    # Verify both callbacks were called
    assert callback.call_count == 2, f"Expected 2 callback calls, got {callback.call_count}"
    
    print("✅ Sync timing fix test passed!")


def test_event_clearing():
    """Test that event is properly cleared when tasks are scheduled."""
    
    callback = Mock()
    event = threading.Event()
    
    futures_dict = FuturesDict(
        event=event,
        callback=callback,
        future_type=concurrent.futures.Future,
    )
    
    # Manually set the event first
    event.set()
    assert event.is_set(), "Event should be set initially"
    
    # Add a task - this should clear the event
    task = Mock(spec=PregelExecutableTask)
    task.id = "test_task"
    future = concurrent.futures.Future()
    
    futures_dict[future] = task
    
    # Event should now be cleared
    assert not event.is_set(), "Event should be cleared after adding task"
    
    print("✅ Event clearing test passed!")


if __name__ == "__main__":
    test_event_clearing()
    test_sync_timing_issue()
    print("All tests passed! 🎉")