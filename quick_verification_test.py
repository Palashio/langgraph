#!/usr/bin/env python3
"""Quick verification test for _get_type_hints_safe function after formatting."""

import sys
import os
from typing import get_type_hints

# Add the langgraph module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'libs', 'langgraph'))

from langgraph.graph.graph import _get_type_hints_safe


class ChooseAnalyzer:
    """Test callable class instance."""
    
    def __call__(self, data: dict) -> str:
        return "analyzer"


def regular_function(data: dict) -> str:
    """Test regular function."""
    return "function"


def test_get_type_hints_safe():
    """Test the _get_type_hints_safe function with different scenarios."""
    
    print("Testing _get_type_hints_safe function...")
    
    # Test 1: Regular function
    print("\n1. Testing with regular function:")
    try:
        hints = _get_type_hints_safe(regular_function)
        print(f"   Success: {hints}")
        assert 'return' in hints
        assert hints['return'] == str
        print("   ✓ Regular function test passed")
    except Exception as e:
        print(f"   ✗ Regular function test failed: {e}")
        return False
    
    # Test 2: Callable class instance
    print("\n2. Testing with callable class instance:")
    try:
        analyzer = ChooseAnalyzer()
        hints = _get_type_hints_safe(analyzer)
        print(f"   Success: {hints}")
        assert 'return' in hints
        assert hints['return'] == str
        print("   ✓ Callable instance test passed")
    except Exception as e:
        print(f"   ✗ Callable instance test failed: {e}")
        return False
    
    # Test 3: Object without type hints
    print("\n3. Testing with object without type hints:")
    try:
        hints = _get_type_hints_safe(lambda x: x)
        print(f"   Success: {hints}")
        assert isinstance(hints, dict)
        print("   ✓ No type hints test passed")
    except Exception as e:
        print(f"   ✗ No type hints test failed: {e}")
        return False
    
    # Test 4: Compare with original get_type_hints behavior
    print("\n4. Comparing with original get_type_hints:")
    try:
        analyzer = ChooseAnalyzer()
        
        # This should raise TypeError with original get_type_hints
        try:
            original_hints = get_type_hints(analyzer)
            print(f"   Unexpected: get_type_hints worked: {original_hints}")
        except TypeError:
            print("   Expected: get_type_hints raised TypeError for callable instance")
        
        # Our safe version should work
        safe_hints = _get_type_hints_safe(analyzer)
        print(f"   Success: _get_type_hints_safe worked: {safe_hints}")
        print("   ✓ Comparison test passed")
    except Exception as e:
        print(f"   ✗ Comparison test failed: {e}")
        return False
    
    print("\n✅ All tests passed! The _get_type_hints_safe function is working correctly.")
    return True


if __name__ == "__main__":
    success = test_get_type_hints_safe()
    sys.exit(0 if success else 1)
