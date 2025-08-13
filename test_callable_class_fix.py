#!/usr/bin/env python3
"""
Test script to verify the fix for TypeError in add_conditional_edges 
when callable class instances are passed without path_map.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

from langgraph.graph import Graph
from typing import Literal

def test_callable_class_instance():
    """Test that callable class instances work without path_map."""
    print("Testing callable class instance...")
    
    class CallableClass:
        def __call__(self, state) -> Literal['option1', 'option2']:
            return 'option1'
    
    # Create graph and nodes
    graph = Graph()
    graph.add_node('start', lambda x: x)
    graph.add_node('option1', lambda x: x)
    graph.add_node('option2', lambda x: x)
    
    callable_instance = CallableClass()
    
    try:
        # This should NOT raise TypeError with the fix
        graph.add_conditional_edges('start', callable_instance)
        print("✅ SUCCESS: Callable class instance works without TypeError")
        return True
    except TypeError as e:
        print(f"❌ FAILED: TypeError still occurs: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def test_regular_function():
    """Test that regular functions still work as expected."""
    print("Testing regular function...")
    
    def regular_function(state) -> Literal['path1', 'path2']:
        return 'path1'
    
    # Create graph and nodes
    graph = Graph()
    graph.add_node('start', lambda x: x)
    graph.add_node('path1', lambda x: x)
    graph.add_node('path2', lambda x: x)
    
    try:
        # This should work as before
        graph.add_conditional_edges('start', regular_function)
        print("✅ SUCCESS: Regular function still works")
        return True
    except Exception as e:
        print(f"❌ FAILED: Regular function broken: {e}")
        return False

def test_callable_class_with_path_map():
    """Test that callable class instances work with explicit path_map."""
    print("Testing callable class instance with explicit path_map...")
    
    class CallableClass:
        def __call__(self, state):
            return 'option1'
    
    # Create graph and nodes
    graph = Graph()
    graph.add_node('start', lambda x: x)
    graph.add_node('node1', lambda x: x)
    graph.add_node('node2', lambda x: x)
    
    callable_instance = CallableClass()
    path_map = {'option1': 'node1', 'option2': 'node2'}
    
    try:
        # This should work with explicit path_map
        graph.add_conditional_edges('start', callable_instance, path_map)
        print("✅ SUCCESS: Callable class instance works with explicit path_map")
        return True
    except Exception as e:
        print(f"❌ FAILED: Callable class with path_map failed: {e}")
        return False

def test_lambda_function():
    """Test that lambda functions still work."""
    print("Testing lambda function...")
    
    # Create graph and nodes
    graph = Graph()
    graph.add_node('start', lambda x: x)
    graph.add_node('next', lambda x: x)
    
    try:
        # This should work with lambda
        graph.add_conditional_edges('start', lambda state: 'next', ['next'])
        print("✅ SUCCESS: Lambda function still works")
        return True
    except Exception as e:
        print(f"❌ FAILED: Lambda function broken: {e}")
        return False

def main():
    """Run all tests and report results."""
    print("=" * 60)
    print("Testing fix for TypeError in add_conditional_edges")
    print("=" * 60)
    
    tests = [
        test_callable_class_instance,
        test_regular_function,
        test_callable_class_with_path_map,
        test_lambda_function
    ]
    
    results = []
    for test in tests:
        print()
        result = test()
        results.append(result)
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("The fix is working correctly!")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
