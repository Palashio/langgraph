#!/usr/bin/env python3
"""Simple syntax checker for the modified file."""

import ast
import sys

def check_syntax(file_path):
    """Check Python syntax of a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        print(f"✅ Syntax check passed for {file_path}")
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking {file_path}: {e}")
        return False

def main():
    """Check syntax of the modified graph.py file."""
    file_path = "/home/daytona/langgraph/libs/langgraph/langgraph/graph/graph.py"
    
    print("Running basic code quality checks...")
    print("=" * 50)
    
    success = check_syntax(file_path)
    
    if success:
        print("\n✅ All basic code quality checks passed!")
        print("Note: Full linting/formatting requires Poetry environment setup")
        print("which failed due to Python 3.13 compatibility issues.")
    else:
        print("\n❌ Code quality checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
