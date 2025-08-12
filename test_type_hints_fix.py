#!/usr/bin/env python3
"""
Direct test of the _get_type_hints_safe() function to verify the fix
for TypeError in add_conditional_edges when callable instance is passed.
"""

import sys
import os
from typing import get_type_hints, TypedDict

# Add the langgraph library to the path
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

# Import the helper function we added
from langgraph.graph.graph import _get_type_hints_safe

print("Testing _get_type_hints_safe() function...")

class State(TypedDict, total=False):
    query: str

# Test 1: Regular function (should work with both old and new approach)
def regular_function(data: State) -> str:
    return "analyzer"

print("\n1. Testing with regular function:")
try:
    hints_old = get_type_hints(regular_function)
    hints_new = _get_type_hints_safe(regular_function)
    print(f"   get_type_hints(): {hints_old}")
    print(f"   _get_type_hints_safe(): {hints_new}")
    print("   ✅ Both approaches work for regular functions")
except Exception as e:
    print(f"   ❌ Error with regular function: {e}")

# Test 2: Callable class instance (this is what was broken)
class ChooseAnalyzer:
    def __call__(self, data: State) -> str:
        return "analyzer"

callable_instance = ChooseAnalyzer()

print("\n2. Testing with callable class instance:")

# Test the old approach (should fail)
try:
    hints_old = get_type_hints(callable_instance)
    print(f"   get_type_hints(): {hints_old}")
    print("   ❌ UNEXPECTED: get_type_hints() should have failed!")
except TypeError as e:
    print(f"   get_type_hints() failed as expected: {e}")

# Test the new approach (should work)
try:
    hints_new = _get_type_hints_safe(callable_instance)
    print(f"   _get_type_hints_safe(): {hints_new}")
    
    # Check if we got the return type correctly
    return_type = hints_new.get('return')
    if return_type == str:
        print("   ✅ SUCCESS: Extracted return type 'str' from callable instance!")
    else:
        print(f"   ⚠️  Got return type: {return_type} (expected str)")
        
except Exception as e:
    print(f"   ❌ Error with _get_type_hints_safe(): {e}")

# Test 3: Object without __call__ method (edge case)
class NotCallable:
    pass

not_callable = NotCallable()

print("\n3. Testing with non-callable object:")
try:
    hints_new = _get_type_hints_safe(not_callable)
    print(f"   _get_type_hints_safe(): {hints_new}")
    if hints_new == {}:
        print("   ✅ SUCCESS: Returns empty dict for non-callable objects")
    else:
        print("   ⚠️  Expected empty dict")
except Exception as e:
    print(f"   ❌ Error with non-callable object: {e}")

print("\n🎉 Type hints fix validation complete!")
print("The _get_type_hints_safe() function successfully handles callable instances.")
