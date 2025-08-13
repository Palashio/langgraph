"""Test for the callable class fix in add_conditional_edges."""

from typing import Literal, TypedDict
from langgraph.graph import StateGraph


def test_add_conditional_edges_with_callable_class_instance():
    """Test that add_conditional_edges works with callable class instances without path_map."""
    
    class State(TypedDict):
        value: str
        next_node: str
    
    class CallableRouter:
        """A callable class that acts as a router for conditional edges."""
        
        def __call__(self, state: State) -> Literal["node_a", "node_b", "end"]:
            """Route based on the state value."""
            if state["value"] == "go_to_a":
                return "node_a"
            elif state["value"] == "go_to_b":
                return "node_b"
            else:
                return "end"
    
    def node_a(state: State) -> State:
        return {"value": state["value"], "next_node": "a"}
    
    def node_b(state: State) -> State:
        return {"value": state["value"], "next_node": "b"}
    
    # Create the callable class instance
    router_instance = CallableRouter()
    
    # Build the graph - this should not raise a TypeError
    workflow = StateGraph(State)
    workflow.add_node("start", lambda state: state)
    workflow.add_node("node_a", node_a)
    workflow.add_node("node_b", node_b)
    workflow.set_entry_point("start")
    
    # This should work without raising TypeError, even without path_map
    # The fix should handle the callable class instance correctly
    workflow.add_conditional_edges("start", router_instance)
    
    # Compile the graph
    app = workflow.compile()
    
    # Test routing to node_a
    result_a = app.invoke({"value": "go_to_a", "next_node": ""})
    assert result_a["next_node"] == "a"
    assert result_a["value"] == "go_to_a"
    
    # Test routing to node_b
    result_b = app.invoke({"value": "go_to_b", "next_node": ""})
    assert result_b["next_node"] == "b"
    assert result_b["value"] == "go_to_b"
    
    # Test routing to end (should stop at start node)
    result_end = app.invoke({"value": "go_to_end", "next_node": ""})
    assert result_end["next_node"] == ""
    assert result_end["value"] == "go_to_end"


if __name__ == "__main__":
    test_add_conditional_edges_with_callable_class_instance()
    print("Test passed! The fix works correctly.")
