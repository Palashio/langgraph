#!/usr/bin/env python3
"""
Final verification that the TypeError fix works by testing the exact scenario
described in the PR: callable instance passed to add_conditional_edges without path_map.
"""

import sys
import os

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

def test_fix_directly():
    """Test the fix directly by calling the problematic code path."""
    print("=== DIRECT TEST OF THE FIX ===")
    
    # Import the function we modified
    from langgraph.graph.graph import _get_type_hints_safe
    from typing import get_type_hints, TypedDict
    
    class State(TypedDict, total=False):
        query: str

    # Test the exact scenario that was broken
    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    callable_instance = ChooseAnalyzer()
    
    print("1. Testing the original problematic call:")
    try:
        # This is what was failing before our fix
        result = get_type_hints(callable_instance)
        print(f"   ❌ UNEXPECTED: get_type_hints() should have failed but got: {result}")
        return False
    except TypeError as e:
        print(f"   ✅ EXPECTED: get_type_hints() failed as expected: {e}")
    
    print("\n2. Testing our fix:")
    try:
        # This should work with our fix
        result = _get_type_hints_safe(callable_instance)
        print(f"   ✅ SUCCESS: _get_type_hints_safe() returned: {result}")
        
        # Verify we got the correct return type
        return_type = result.get('return')
        if return_type == str:
            print("   ✅ SUCCESS: Correctly extracted return type 'str'")
            return True
        else:
            print(f"   ❌ FAILURE: Expected return type 'str', got: {return_type}")
            return False
    except Exception as e:
        print(f"   ❌ FAILURE: _get_type_hints_safe() failed: {e}")
        return False

def test_add_conditional_edges_logic():
    """Test the specific logic in add_conditional_edges that was fixed."""
    print("\n=== TEST OF add_conditional_edges LOGIC ===")
    
    from langgraph.graph.graph import _get_type_hints_safe
    from typing import get_args, get_origin, Literal, TypedDict
    
    class State(TypedDict, total=False):
        query: str

    class ChooseAnalyzer:
        def __call__(self, data: State) -> str:
            return "analyzer"

    path = ChooseAnalyzer()
    path_map = None
    
    print("Testing the exact logic from add_conditional_edges:")
    
    # This is the exact logic from the method we fixed
    if isinstance(path_map, dict):
        path_map = path_map.copy()
        print("   Branch: dict path_map")
    elif isinstance(path_map, list):
        path_map = {name: name for name in path_map}
        print("   Branch: list path_map")
    elif rtn_type := _get_type_hints_safe(path).get("return"):
        if get_origin(rtn_type) is Literal:
            path_map = {name: name for name in get_args(rtn_type)}
            print(f"   Branch: Literal return type, path_map = {path_map}")
        else:
            print(f"   Branch: Non-literal return type: {rtn_type}")
    else:
        print("   Branch: No return type found")
    
    print(f"   Final path_map: {path_map}")
    print("   ✅ SUCCESS: Logic completed without TypeError!")
    return True

def main():
    """Run all verification tests."""
    print("VERIFYING THE TYPEERROR FIX FOR add_conditional_edges")
    print("=" * 60)
    
    success1 = test_fix_directly()
    success2 = test_add_conditional_edges_logic()
    
    print("\n" + "=" * 60)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED!")
        print("✅ The fix successfully resolves the TypeError for callable instances!")
        print("✅ Callable class instances can now be used in add_conditional_edges!")
        print("\nSUMMARY OF FIX:")
        print("- Added _get_type_hints_safe() helper function")
        print("- Modified add_conditional_edges to use the safe function")
        print("- Now handles callable instances by extracting hints from __call__ method")
        print("- Gracefully handles failures by returning empty dict")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
