#!/usr/bin/env python3
"""Simple test runner for the callable class fix test."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

from tests.test_callable_class_fix import (
    test_add_conditional_edges_with_callable_class_instance,
    test_add_conditional_edges_with_callable_class_instance_no_path_map
)

if __name__ == "__main__":
    try:
        print("Running test 1: test_add_conditional_edges_with_callable_class_instance")
        test_add_conditional_edges_with_callable_class_instance()
        print("✓ Test 1 passed")
        
        print("Running test 2: test_add_conditional_edges_with_callable_class_instance_no_path_map")
        test_add_conditional_edges_with_callable_class_instance_no_path_map()
        print("✓ Test 2 passed")
        
        print("✓ All tests passed! The fix for callable class instances works correctly.")
    except Exception as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)
