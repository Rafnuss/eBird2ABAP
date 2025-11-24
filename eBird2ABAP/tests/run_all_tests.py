#!/usr/bin/env python
"""
Run all pentad module tests.

This script runs all test files in the tests directory and provides
a summary of results.
"""

import sys
import subprocess
from pathlib import Path

# Test files to run (in order)
TEST_FILES = [
    'test_pentad_conversions.py',
    'test_pentad_polygons.py',
    'test_pentad_bounds.py',
]

def run_test(test_file):
    """Run a single test file and return success status."""
    print("\n" + "=" * 80)
    print(f"Running {test_file}...")
    print("=" * 80)
    
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=Path(__file__).parent,
        capture_output=False
    )
    
    return result.returncode == 0

def main():
    """Run all tests and report results."""
    print("\n" + "=" * 80)
    print("PENTAD MODULE - RUNNING ALL TESTS")
    print("=" * 80)
    
    results = {}
    
    for test_file in TEST_FILES:
        success = run_test(test_file)
        results[test_file] = success
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for test_file, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status:12} {test_file}")
        if not success:
            all_passed = False
    
    print("=" * 80)
    
    if all_passed:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓\n")
        return 0
    else:
        print("\n✗✗✗ SOME TESTS FAILED ✗✗✗\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
