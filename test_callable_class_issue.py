#!/usr/bin/env python3
"""
Test script to reproduce the TypeError issue with callable class instances
in add_conditional_edges when no path_map is provided.
"""

from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph

class State(TypedDict):
    value: str

class CallableCondition:
    """A callable class that returns a Literal type."""
    
    def __call__(self, state: State) -> Literal["left", "right"]:
        return "left" if state["value"] == "go_left" else "right"

def left_node(state: State) -> State:
    return {"value": "left_executed"}

def right_node(state: State) -> State:
    return {"value": "right_executed"}

def test_callable_class_issue():
    """Test that demonstrates the TypeError issue."""
    # Create the callable instance
    condition_instance = CallableCondition()
    
    # This should raise a TypeError with the current implementation
    workflow = StateGraph(State)
    workflow.add_node("left", left_node)
    workflow.add_node("right", right_node)
    workflow.set_entry_point("left")
    
    try:
        # This call should raise TypeError before the fix
        workflow.add_conditional_edges("left", condition_instance)
        print("SUCCESS: No TypeError raised - fix is working!")
        
        # Try to compile and run
        app = workflow.compile()
        result = app.invoke({"value": "go_left"})
        print(f"Graph execution result: {result}")
        
    except TypeError as e:
        print(f"ERROR: TypeError raised as expected: {e}")
        return False
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing callable class instance with add_conditional_edges...")
    success = test_callable_class_issue()
    if success:
        print("Test passed!")
    else:
        print("Test failed - TypeError occurred as expected before fix.")
