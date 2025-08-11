#!/usr/bin/env python3
"""
Script to run the specific test for the callable class instance fix.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

def run_test():
    """Run the specific test to verify the fix."""
    try:
        # Import the test function
        from tests.test_pregel import test_callable_in_conditional_edges_with_no_path_map
        
        print("Running test_callable_in_conditional_edges_with_no_path_map...")
        
        # Execute the test
        test_callable_in_conditional_edges_with_no_path_map()
        
        print("✅ Test passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing the fix for TypeError in add_conditional_edges...")
    print("=" * 60)
    
    success = run_test()
    
    print("=" * 60)
    if success:
        print("🎉 The fix is working correctly!")
        sys.exit(0)
    else:
        print("💥 The fix needs more work.")
        sys.exit(1)
