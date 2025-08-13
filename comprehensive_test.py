#!/usr/bin/env python3
import sys
import os
import traceback

# Set environment variable to disable colors for cleaner output
os.environ['NO_COLOR'] = '1'

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

def test_basic_graph_functionality():
    """Test basic graph functionality to ensure core features work."""
    from langgraph.graph.state import StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from typing import TypedDict
    
    class State(TypedDict):
        value: int
    
    def add_one(state: State) -> State:
        return {"value": state["value"] + 1}
    
    def add_ten(state: State) -> State:
        return {"value": state["value"] + 10}
    
    # Test basic graph without interrupts
    workflow = StateGraph(State)
    workflow.add_node("add_one", add_one)
    workflow.add_node("add_ten", add_ten)
    workflow.set_entry_point("add_one")
    workflow.add_edge("add_one", "add_ten")
    workflow.set_finish_point("add_ten")
    
    app = workflow.compile()
    result = app.invoke({"value": 0})
    assert result["value"] == 11, f"Expected 11, got {result['value']}"
    print("✅ Basic graph functionality works")

def test_checkpointer_functionality():
    """Test checkpointer functionality to ensure state saving works."""
    from langgraph.graph.state import StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from typing import TypedDict
    
    class State(TypedDict):
        value: int
    
    def add_one(state: State) -> State:
        return {"value": state["value"] + 1}
    
    workflow = StateGraph(State)
    workflow.add_node("add_one", add_one)
    workflow.set_entry_point("add_one")
    workflow.set_finish_point("add_one")
    
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": "test_checkpoint"}}
    result = app.invoke({"value": 0}, config)
    assert result["value"] == 1, f"Expected 1, got {result['value']}"
    
    # Verify state was saved
    state = app.get_state(config)
    assert state.values["value"] == 1, f"Expected saved state value 1, got {state.values['value']}"
    print("✅ Checkpointer functionality works")

def test_streaming_functionality():
    """Test streaming functionality to ensure streaming works."""
    from langgraph.graph.state import StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from typing import TypedDict
    
    class State(TypedDict):
        value: int
        steps: list[str]
    
    def step_a(state: State) -> State:
        return {"value": state["value"] + 1, "steps": state["steps"] + ["step_a"]}
    
    def step_b(state: State) -> State:
        return {"value": state["value"] + 10, "steps": state["steps"] + ["step_b"]}
    
    workflow = StateGraph(State)
    workflow.add_node("step_a", step_a)
    workflow.add_node("step_b", step_b)
    workflow.set_entry_point("step_a")
    workflow.add_edge("step_a", "step_b")
    workflow.set_finish_point("step_b")
    
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": "test_streaming"}}
    chunks = list(app.stream({"value": 0, "steps": []}, config))
    
    assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
    assert "step_a" in chunks[0], "First chunk should contain step_a"
    assert "step_b" in chunks[1], "Second chunk should contain step_b"
    print("✅ Streaming functionality works")

def test_single_interrupt_functionality():
    """Test single interrupt functionality to ensure basic interrupts work."""
    from langgraph.graph.state import StateGraph
    from langgraph.checkpoint.memory import MemorySaver
    from typing import TypedDict
    
    class State(TypedDict):
        value: int
        steps: list[str]
    
    def step_a(state: State) -> State:
        return {"value": state["value"] + 1, "steps": state["steps"] + ["step_a"]}
    
    def step_b(state: State) -> State:
        return {"value": state["value"] + 10, "steps": state["steps"] + ["step_b"]}
    
    workflow = StateGraph(State)
    workflow.add_node("step_a", step_a)
    workflow.add_node("step_b", step_b)
    workflow.set_entry_point("step_a")
    workflow.add_edge("step_a", "step_b")
    workflow.set_finish_point("step_b")
    
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer, interrupt_after=["step_a"])
    
    config = {"configurable": {"thread_id": "test_single_interrupt"}}
    
    # First run - should interrupt after step_a
    chunks = list(app.stream({"value": 0, "steps": []}, config))
    assert len(chunks) == 1, f"Expected 1 chunk (interrupted), got {len(chunks)}"
    assert "step_a" in chunks[0], "Should have executed step_a"
    
    # Verify state at interrupt
    state = app.get_state(config)
    assert state.values["value"] == 1, f"Expected value 1 at interrupt, got {state.values['value']}"
    assert state.next == ("step_b",), f"Expected next to be step_b, got {state.next}"
    
    # Resume execution
    chunks = list(app.stream(None, config))
    assert len(chunks) == 1, f"Expected 1 chunk (resume), got {len(chunks)}"
    assert "step_b" in chunks[0], "Should have executed step_b"
    
    # Verify final state
    state = app.get_state(config)
    assert state.values["value"] == 11, f"Expected final value 11, got {state.values['value']}"
    assert state.next == (), f"Expected execution to be complete, got {state.next}"
    print("✅ Single interrupt functionality works")

def main():
    """Run comprehensive tests to verify the fix doesn't break existing functionality."""
    print("Running comprehensive tests to verify the fix doesn't break existing functionality...")
    print("=" * 80)
    
    tests = [
        ("Basic Graph Functionality", test_basic_graph_functionality),
        ("Checkpointer Functionality", test_checkpointer_functionality),
        ("Streaming Functionality", test_streaming_functionality),
        ("Single Interrupt Functionality", test_single_interrupt_functionality),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning {test_name}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            traceback.print_exc()
            failed += 1
    
    # Also run our new test to confirm the fix works
    try:
        print(f"\nRunning Multiple Interrupts After Resume Test...")
        from tests.test_pregel import test_multiple_interrupts_after_resume
        test_multiple_interrupts_after_resume()
        print("✅ Multiple Interrupts After Resume Test works")
        passed += 1
    except Exception as e:
        print(f"❌ Multiple Interrupts After Resume Test FAILED: {e}")
        traceback.print_exc()
        failed += 1
    
    print("\n" + "=" * 80)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed! The fix for multiple interruptions has been successfully implemented without breaking existing functionality.")
        print("\nKey functionality verified:")
        print("- ✅ Basic graph execution")
        print("- ✅ Checkpointer state management")
        print("- ✅ Streaming functionality")
        print("- ✅ Single interrupt functionality")
        print("- ✅ Multiple interrupts after resume (our fix)")
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
