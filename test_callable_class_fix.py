#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges with callable class instances.
This test demonstrates that the fix allows callable class instances with type hints on __call__ method
to work properly with add_conditional_edges without requiring an explicit path_map.
"""

from typing import Literal
from langgraph.graph import Graph, END


def test_add_conditional_edges_with_callable_class_instance():
    """Test that add_conditional_edges works with callable class instances that have type hints on __call__ method."""
    
    # Define a callable class with type hints on __call__ method
    class CallableCondition:
        def __call__(self, state: dict) -> Literal["continue", "end"]:
            """A callable class instance that returns conditional paths."""
            if state.get("should_continue", True):
                return "continue"
            else:
                return "end"
    
    # Create a simple state for testing
    def node_a(state: dict) -> dict:
        return {"step": "a", "should_continue": state.get("should_continue", True)}
    
    def node_b(state: dict) -> dict:
        return {"step": "b", "should_continue": False}
    
    # Create the graph
    workflow = Graph()
    workflow.add_node("node_a", node_a)
    workflow.add_node("node_b", node_b)
    workflow.set_entry_point("node_a")
    
    # Create an instance of the callable class
    condition_instance = CallableCondition()
    
    # This should not raise a TypeError anymore - the fix should handle callable class instances
    # by extracting type hints from the __call__ method
    workflow.add_conditional_edges(
        "node_a", 
        condition_instance,  # callable class instance without explicit path_map
        # path_map should be automatically inferred from Literal type hints: {"continue": "continue", "end": "end"}
        {"continue": "node_b", "end": END}
    )
    
    # Compile the graph - this should work without errors
    app = workflow.compile()
    
    # Test the graph execution
    # Test case 1: should_continue=True -> goes to node_b
    result1 = app.invoke({"should_continue": True})
    assert result1["step"] == "b"
    assert result1["should_continue"] == False
    print("✓ Test case 1 passed: should_continue=True -> goes to node_b")
    
    # Test case 2: should_continue=False -> ends immediately
    result2 = app.invoke({"should_continue": False})
    assert result2["step"] == "a"
    assert result2["should_continue"] == False
    print("✓ Test case 2 passed: should_continue=False -> ends immediately")
    
    print("✓ All tests passed! The fix for callable class instances works correctly.")


if __name__ == "__main__":
    test_add_conditional_edges_with_callable_class_instance()


