"""Simple test case to reproduce the multiple interruptions issue.

This test demonstrates the bug where subsequent interruptions are ignored
after resuming execution with input=None.
"""

from langgraph.channels.last_value import LastValue
from langgraph.checkpoint.memory import MemorySaver
from langgraph.pregel import Channel, Pregel


def test_multiple_interruptions_bug():
    """Demonstrates the multiple interruptions bug."""
    
    # Simple functions for testing
    def add_one(x: int) -> int:
        return x + 1
    
    def add_ten(x: int) -> int:
        return x + 10
    
    def add_hundred(x: int) -> int:
        return x + 100
    
    # Create nodes following the existing test pattern
    one = Channel.subscribe_to("input") | add_one | Channel.write_to("output_one")
    two = Channel.subscribe_to("output_one") | add_ten | Channel.write_to("output_two")
    three = Channel.subscribe_to("output_two") | add_hundred | Channel.write_to("output")
    
    # Create app with interrupts after first two nodes
    # Following the exact pattern from test_invoke_two_processes_in_out_interrupt
    memory = MemorySaver()
    app = Pregel(
        nodes={"one": one, "two": two, "three": three},
        channels={
            "input": LastValue(int),
            "output_one": LastValue(int),
            "output_two": LastValue(int),
            "output": LastValue(int),
        },
        input_channels="input",
        output_channels="output",
        checkpointer=memory,
        interrupt_after_nodes=["one", "two"],
    )
    
    config = {"configurable": {"thread_id": "test"}}
    
    print("=== Testing Multiple Interruptions Bug ===")
    
    # Step 1: Start execution, should interrupt after 'one'
    print("Step 1: Starting execution with input=1")
    result1 = app.invoke(1, config)
    print(f"Result: {result1}")
    
    if result1 is not None:
        print("ERROR: Expected None (interrupted), but got result")
        return False
    
    # Check intermediate state
    checkpoint = memory.get(config)
    print(f"After step 1 - output_one: {checkpoint['channel_values'].get('output_one')}")
    
    # Step 2: Resume with None, should interrupt after 'two'
    print("\nStep 2: Resuming with input=None")
    result2 = app.invoke(None, config)
    print(f"Result: {result2}")
    
    if result2 is None:
        print("SUCCESS: Second interruption worked!")
        checkpoint = memory.get(config)
        print(f"After step 2 - output_two: {checkpoint['channel_values'].get('output_two')}")
        
        # Step 3: Final resume
        print("\nStep 3: Final resume")
        result3 = app.invoke(None, config)
        print(f"Final result: {result3}")
        return True
    else:
        print("BUG REPRODUCED: Second interruption was ignored!")
        print(f"Expected: None (interrupted), Got: {result2}")
        print("The execution continued to completion instead of interrupting after 'two'")
        return False


if __name__ == "__main__":
    try:
        success = test_multiple_interruptions_bug()
        if success:
            print("\n✅ Test passed - multiple interruptions work correctly")
        else:
            print("\n❌ Test failed - demonstrates the multiple interruptions bug")
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        import traceback
        traceback.print_exc()

