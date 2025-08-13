#!/usr/bin/env python3
"""
Test runner to verify the callable class fix works correctly.
"""
import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

from typing import TypedDict, Literal
from langgraph.graph import StateGraph

def test_callable_class_conditional_edges():
    """Test that callable class instances work with add_conditional_edges without path_map."""
    
    class State(TypedDict):
        value: str
    
    class CallableCondition:
        """A callable class that returns a Literal type."""
        
        def __call__(self, state: State) -> Literal["left", "right"]:
            return "left" if state["value"] == "go_left" else "right"
    
    def start_node(state: State) -> State:
        return state  # Pass through the initial state
    
    def left_node(state: State) -> State:
        return {"value": "left_executed"}
    
    def right_node(state: State) -> State:
        return {"value": "right_executed"}
    
    # Create the callable instance
    condition_instance = CallableCondition()
    
    # This should not raise a TypeError after the fix
    workflow = StateGraph(State)
    workflow.add_node("start", start_node)
    workflow.add_node("left", left_node)
    workflow.add_node("right", right_node)
    workflow.set_entry_point("start")
    
    print("Testing callable class instance with add_conditional_edges...")
    
    try:
        # This call should work without raising TypeError
        # The path_map should be inferred from the __call__ method's return type
        workflow.add_conditional_edges("start", condition_instance)
        print("✅ SUCCESS: No TypeError raised when using callable class instance")
        
        # Compile and test the graph
        app = workflow.compile()
        
        # Test that it works correctly - should go to left
        result = app.invoke({"value": "go_left"})
        assert result["value"] == "left_executed", f"Expected 'left_executed', got {result['value']}"
        print("✅ SUCCESS: Graph execution works correctly (go_left → left_executed)")
        
        # Test the other path - should go to right
        result2 = app.invoke({"value": "go_right"})
        assert result2["value"] == "right_executed", f"Expected 'right_executed', got {result2['value']}"
        print("✅ SUCCESS: Both execution paths work correctly (go_right → right_executed)")
        
        return True
        
    except TypeError as e:
        print(f"❌ FAILED: TypeError still raised: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def test_regular_function_still_works():
    """Test that regular functions still work with add_conditional_edges."""
    
    class State(TypedDict):
        value: str
    
    def condition_function(state: State) -> Literal["left", "right"]:
        return "left" if state["value"] == "go_left" else "right"
    
    def start_node(state: State) -> State:
        return state  # Pass through the initial state
    
    def left_node(state: State) -> State:
        return {"value": "left_executed"}
    
    def right_node(state: State) -> State:
        return {"value": "right_executed"}
    
    print("Testing regular function with add_conditional_edges...")
    
    try:
        workflow = StateGraph(State)
        workflow.add_node("start", start_node)
        workflow.add_node("left", left_node)
        workflow.add_node("right", right_node)
        workflow.set_entry_point("start")
        
        # This should still work as before
        workflow.add_conditional_edges("start", condition_function)
        print("✅ SUCCESS: Regular functions still work")
        
        # Compile and test the graph
        app = workflow.compile()
        
        # Test that it works correctly - should go to left
        result = app.invoke({"value": "go_left"})
        assert result["value"] == "left_executed", f"Expected 'left_executed', got {result['value']}"
        print("✅ SUCCESS: Regular function graph execution works correctly (go_left → left_executed)")
        
        # Test the other path - should go to right
        result2 = app.invoke({"value": "go_right"})
        assert result2["value"] == "right_executed", f"Expected 'right_executed', got {result2['value']}"
        print("✅ SUCCESS: Regular function both paths work correctly (go_right → right_executed)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Regular function test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running tests to verify the callable class fix...")
    print("=" * 60)
    
    # Test 1: Callable class instance
    test1_passed = test_callable_class_conditional_edges()
    print()
    
    # Test 2: Regular function (regression test)
    test2_passed = test_regular_function_still_works()
    print()
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! The fix is working correctly.")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED! The fix needs more work.")
        sys.exit(1)


