"""Test for callable class instances in add_conditional_edges."""

from typing import Literal
from typing_extensions import TypedDict

from langgraph.graph import StateGraph


def test_callable_class_conditional_edges() -> None:
    """Test that callable class instances work with add_conditional_edges without path_map."""
    
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
    
    # Create the callable instance
    condition_instance = CallableCondition()
    
    # This should not raise a TypeError after the fix
    workflow = StateGraph(State)
    workflow.add_node("left", left_node)
    workflow.add_node("right", right_node)
    workflow.set_entry_point("left")
    
    # This call should work without raising TypeError
    # The path_map should be inferred from the __call__ method's return type
    workflow.add_conditional_edges("left", condition_instance)
    
    # Compile and test the graph
    app = workflow.compile()
    
    # Test that it works correctly
    result = app.invoke({"value": "go_left"})
    assert result["value"] == "left_executed"
