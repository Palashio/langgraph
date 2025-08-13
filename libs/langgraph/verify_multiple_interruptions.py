#!/usr/bin/env python3
"""
Verification script to test multiple interruptions after resuming execution.
This script directly tests the fix without relying on pytest.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from typing import Any, Dict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


def create_test_graph():
    """Create a simple test graph for interruption testing."""
    
    def node_1(state: Dict[str, Any]) -> Dict[str, Any]:
        print("Executing node_1")
        return {"value": state.get("value", 0) + 1, "path": state.get("path", []) + ["node_1"]}
    
    def node_2(state: Dict[str, Any]) -> Dict[str, Any]:
        print("Executing node_2")
        return {"value": state["value"] + 1, "path": state["path"] + ["node_2"]}
    
    def node_3(state: Dict[str, Any]) -> Dict[str, Any]:
        print("Executing node_3")
        return {"value": state["value"] + 1, "path": state["path"] + ["node_3"]}

    # Create graph
    graph = StateGraph(dict)
    graph.add_node("node_1", node_1)
    graph.add_node("node_2", node_2)
    graph.add_node("node_3", node_3)
    
    graph.set_entry_point("node_1")
    graph.add_edge("node_1", "node_2")
    graph.add_edge("node_2", "node_3")
    graph.add_edge("node_3", END)
    
    return graph


def test_multiple_interruptions_before():
    """Test multiple interruptions using interrupt_before."""
    print("\n=== Testing Multiple Interruptions with interrupt_before ===")
    
    graph = create_test_graph()
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer, interrupt_before=["node_2", "node_3"])
    
    thread_id = "test_thread_before"
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # First execution - should interrupt before node_2
        print("\n1. First execution (should interrupt before node_2):")
        result = app.invoke({"value": 0, "path": []}, config)
        print(f"Result after first execution: {result}")
        
        # Resume execution - should interrupt before node_3
        print("\n2. Resume execution (should interrupt before node_3):")
        result = app.invoke(None, config)
        print(f"Result after resume: {result}")
        
        # Try to resume again - this should work with the fix
        print("\n3. Resume again (should complete execution):")
        result = app.invoke(None, config)
        print(f"Final result: {result}")
        
        # Verify the final state
        if result.get("value") == 3 and "node_3" in result.get("path", []):
            print("✅ SUCCESS: Multiple interruptions work correctly with interrupt_before!")
            return True
        else:
            print("❌ FAILURE: Final state is incorrect")
            return False
            
    except Exception as e:
        print(f"❌ ERROR during interrupt_before test: {e}")
        return False


def test_multiple_interruptions_after():
    """Test multiple interruptions using interrupt_after."""
    print("\n=== Testing Multiple Interruptions with interrupt_after ===")
    
    graph = create_test_graph()
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer, interrupt_after=["node_1", "node_2"])
    
    thread_id = "test_thread_after"
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # First execution - should interrupt after node_1
        print("\n1. First execution (should interrupt after node_1):")
        result = app.invoke({"value": 0, "path": []}, config)
        print(f"Result after first execution: {result}")
        
        # Resume execution - should interrupt after node_2
        print("\n2. Resume execution (should interrupt after node_2):")
        result = app.invoke(None, config)
        print(f"Result after resume: {result}")
        
        # Try to resume again - this should work with the fix
        print("\n3. Resume again (should complete execution):")
        result = app.invoke(None, config)
        print(f"Final result: {result}")
        
        # Verify the final state
        if result.get("value") == 3 and "node_3" in result.get("path", []):
            print("✅ SUCCESS: Multiple interruptions work correctly with interrupt_after!")
            return True
        else:
            print("❌ FAILURE: Final state is incorrect")
            return False
            
    except Exception as e:
        print(f"❌ ERROR during interrupt_after test: {e}")
        return False


def main():
    """Run all verification tests."""
    print("Starting verification of multiple interruption fix...")
    
    success_before = test_multiple_interruptions_before()
    success_after = test_multiple_interruptions_after()
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY:")
    print(f"interrupt_before test: {'✅ PASSED' if success_before else '❌ FAILED'}")
    print(f"interrupt_after test: {'✅ PASSED' if success_after else '❌ FAILED'}")
    
    if success_before and success_after:
        print("\n🎉 ALL TESTS PASSED! The multiple interruption fix is working correctly.")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED! The fix may not be working properly.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

