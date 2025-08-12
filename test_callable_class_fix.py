"""Test case for callable class conditional edges fix."""

from typing import Any, Dict, Literal, TypedDict

from langgraph.graph import END
from langgraph.graph.state import StateGraph


def test_callable_class_conditional_edges_without_path_map():
    """Test that callable class instances work with add_conditional_edges without path_map.
    
    This test verifies the fix for the TypeError that occurred when a callable class
    instance was passed to add_conditional_edges without providing a path_map.
    The fix should automatically infer the path_map from the Literal return type hints
    of the callable class's __call__ method.
    """
    
    class CallableCondition:
        """A callable class with Literal return type annotation."""
        
        def __call__(self, state: Dict[str, Any]) -> Literal["left", "right"]:
            """Conditional logic that returns either 'left' or 'right'."""
            return "left" if state.get("value", 0) < 5 else "right"
    
    class State(TypedDict):
        value: int
        result: str
    
    # Create the callable class instance
    condition_instance = CallableCondition()
    
    # Create a StateGraph and add nodes
    graph = StateGraph(State)
    graph.add_node("start", lambda state: {"result": "started"})
    graph.add_node("left", lambda state: {"result": "went left"})
    graph.add_node("right", lambda state: {"result": "went right"})
    
    # This should not raise a TypeError and should correctly infer path_map
    # from the Literal return type hints of the __call__ method
    graph.add_conditional_edges(
        source="start",
        path=condition_instance,  # Callable class instance without path_map
        # path_map is intentionally omitted to test automatic inference
    )
    
    graph.set_entry_point("start")
    graph.add_edge("left", END)
    graph.add_edge("right", END)
    
    # Compile the graph - this should succeed without errors
    compiled_graph = graph.compile()
    
    # Test that the graph works correctly with different inputs
    result_left = compiled_graph.invoke({"value": 3, "result": ""})
    assert result_left["result"] == "went left"
    
    result_right = compiled_graph.invoke({"value": 7, "result": ""})
    assert result_right["result"] == "went right"


if __name__ == "__main__":
    test_callable_class_conditional_edges_without_path_map()
    print("Test passed! The fix works correctly.")
