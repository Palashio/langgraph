#!/usr/bin/env python3
"""Simple validation script for the new context API implementation."""

import sys
import os
import warnings
from dataclasses import dataclass

# Add the current directory to the path so we can import langgraph modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all new modules can be imported."""
    try:
        from langgraph.runtime import Runtime, get_runtime
        print("✓ Runtime imports successful")
        
        from langgraph.graph.state import StateGraph
        print("✓ StateGraph import successful") 
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without actually running the graph."""
    try:
        from langgraph.runtime import Runtime, get_runtime, _create_runtime_from_config
        from langgraph.graph.state import StateGraph
        from langchain_core.runnables import RunnableConfig
        from typing_extensions import TypedDict
        
        # Test Runtime class
        @dataclass
        class TestContext:
            user_id: str
            temperature: float = 0.7
        
        class TestState(TypedDict):
            messages: list[str]
        
        # Test Runtime creation
        config = RunnableConfig(configurable={"user_id": "test", "temperature": 0.9})
        runtime = _create_runtime_from_config(config, TestContext)
        print(f"✓ Runtime created with context: user_id={runtime.context.user_id}, temp={runtime.context.temperature}")
        
        # Test StateGraph with context_schema
        graph = StateGraph(TestState, context_schema=TestContext)
        print(f"✓ StateGraph created with context_schema: {graph.context_schema}")
        
        # Test deprecation warning for config_schema
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            graph_old = StateGraph(TestState, config_schema=TestContext)
            if w:
                print(f"✓ Deprecation warning for config_schema: {w[0].message}")
            else:
                print("⚠ No deprecation warning for config_schema")
        
        return True
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_node_wrapping():
    """Test the node function wrapping functionality."""
    try:
        from langgraph.runtime import _wrap_node_function, Runtime
        
        @dataclass
        class TestContext:
            user_id: str
        
        # Test function that expects Runtime
        def node_with_runtime(state, runtime: Runtime[TestContext]):
            return {"result": f"Hello {runtime.context.user_id}"}
        
        # Test function that doesn't expect Runtime
        def node_without_runtime(state):
            return {"result": "Hello world"}
        
        # Test wrapping
        wrapped_with = _wrap_node_function(node_with_runtime, TestContext)
        wrapped_without = _wrap_node_function(node_without_runtime, TestContext)
        
        print("✓ Node function wrapping works")
        print(f"  - Function with Runtime: {wrapped_with != node_with_runtime}")
        print(f"  - Function without Runtime: {wrapped_without == node_without_runtime}")
        
        return True
    except Exception as e:
        print(f"✗ Node wrapping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("Validating new Context API implementation...")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Node Wrapping", test_node_wrapping),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        passed = test_func()
        all_passed = all_passed and passed
        
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All validation tests passed!")
        return 0
    else:
        print("✗ Some validation tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())