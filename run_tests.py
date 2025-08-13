#!/usr/bin/env python3
import sys
import os
import importlib.util
import traceback

# Set environment variable to disable colors for cleaner output
os.environ['NO_COLOR'] = '1'

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

def run_test_function(module_name, test_func_name):
    """Run a specific test function from a module."""
    try:
        spec = importlib.util.spec_from_file_location(
            module_name, 
            f'/home/daytona/langgraph/libs/langgraph/tests/{module_name}.py'
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        test_func = getattr(module, test_func_name)
        print(f"Running {test_func_name}...")
        test_func()
        print(f"✅ {test_func_name} PASSED")
        return True
    except Exception as e:
        print(f"❌ {test_func_name} FAILED: {e}")
        traceback.print_exc()
        return False

def main():
    """Run key tests to verify the fix doesn't break existing functionality."""
    print("Running key tests to verify the fix doesn't break existing functionality...")
    
    # First, run our new test to confirm the fix works
    success = run_test_function('test_pregel', 'test_multiple_interrupts_after_resume')
    
    # Try to run a few basic tests from the test_pregel module
    basic_tests = [
        'test_graph_validation',
        'test_invoke_single_process_in_out',
        'test_invoke_single_process_in_write_kwargs_out',
    ]
    
    for test_name in basic_tests:
        try:
            if run_test_function('test_pregel', test_name):
                success = success and True
            else:
                success = False
        except AttributeError:
            print(f"⚠️  Test {test_name} not found, skipping...")
            continue
    
    if success:
        print("\n🎉 All tested functionality appears to be working correctly!")
        print("The fix for multiple interruptions has been successfully implemented without breaking existing functionality.")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
