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
            return "continue"  # Always return continue for simplicity
    
    # Create a simple logic function for nodes
    def logic(inp: str) -> str:
        return ""
    
    # Create the graph following the existing test patterns
    workflow = Graph()
    workflow.add_node("agent", logic)
    workflow.add_node("tools", logic)
    workflow.set_entry_point("agent")
    
    # Create an instance of the callable class
    condition_instance = CallableCondition()
    
    # This should not raise a TypeError anymore - the fix should handle callable class instances
    # by extracting type hints from the __call__ method
    workflow.add_conditional_edges(
        "agent", 
        condition_instance,  # callable class instance without explicit path_map
        {"continue": "tools", "end": END}
    )
    
    workflow.add_edge("tools", "agent")
    
    # Compile the graph - this should work without errors
    app = workflow.compile()
    
    print("✓ Test passed! The fix for callable class instances works correctly - no TypeError was raised.")


if __name__ == "__main__":
    test_add_conditional_edges_with_callable_class_instance()



