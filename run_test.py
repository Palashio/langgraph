#!/usr/bin/env python3
"""
Test runner to execute the specific test case for callable class instances
"""
import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

# Import the test function
from tests.test_pregel import test_callable_in_conditional_edges_with_no_path_map

def main():
    """Run the specific test case"""
    try:
        print("Running test_callable_in_conditional_edges_with_no_path_map...")
        test_callable_in_conditional_edges_with_no_path_map()
        print("✅ test_callable_in_conditional_edges_with_no_path_map PASSED")
        print("🎉 The fix successfully resolves the TypeError for callable class instances!")
        return True
    except Exception as e:
        print(f"❌ test_callable_in_conditional_edges_with_no_path_map FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
