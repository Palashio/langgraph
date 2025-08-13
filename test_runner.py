#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/daytona/langgraph/libs/langgraph')

# Set environment variable to disable colors for cleaner output
os.environ['NO_COLOR'] = '1'

try:
    from tests.test_pregel import test_multiple_interrupts_after_resume
    print("Running test_multiple_interrupts_after_resume...")
    test_multiple_interrupts_after_resume()
    print("✅ test_multiple_interrupts_after_resume PASSED")
except Exception as e:
    print(f"❌ test_multiple_interrupts_after_resume FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("All tests completed successfully!")
