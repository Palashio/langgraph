#!/usr/bin/env python3
"""Simple syntax and basic code quality checker for modified files."""

import ast
import sys
from pathlib import Path

def check_file_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        print(f"✓ {file_path}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path}: Error - {e}")
        return False

def basic_style_check(file_path):
    """Basic style checks."""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Check for trailing whitespace
            if line.rstrip() != line.rstrip('\n'):
                issues.append(f"Line {i}: Trailing whitespace")
            
            # Check for very long lines (over 100 chars as a soft limit)
            if len(line.rstrip()) > 100:
                issues.append(f"Line {i}: Long line ({len(line.rstrip())} chars)")
        
        if issues:
            print(f"⚠ {file_path}: Style issues found:")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(issues) > 5:
                print(f"  ... and {len(issues) - 5} more issues")
        else:
            print(f"✓ {file_path}: Basic style OK")
            
    except Exception as e:
        print(f"✗ {file_path}: Error checking style - {e}")

def main():
    """Check the modified files."""
    files_to_check = [
        "/home/daytona/langgraph/libs/langgraph/langgraph/graph/graph.py",
        "/home/daytona/langgraph/libs/langgraph/tests/test_pregel.py"
    ]
    
    print("Checking syntax and basic code quality for modified files...")
    print("=" * 60)
    
    all_good = True
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            print(f"\nChecking: {file_path}")
            syntax_ok = check_file_syntax(file_path)
            if syntax_ok:
                basic_style_check(file_path)
            all_good = all_good and syntax_ok
        else:
            print(f"✗ File not found: {file_path}")
            all_good = False
    
    print("\n" + "=" * 60)
    if all_good:
        print("✓ All checks passed!")
        return 0
    else:
        print("✗ Some issues found")
        return 1

if __name__ == "__main__":
    sys.exit(main())
