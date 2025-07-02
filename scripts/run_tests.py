#!/usr/bin/env python3
"""Test runner script for Floridify test suite."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔍 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout.strip():
                print(f"Output:\n{result.stdout}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"Error:\n{result.stderr}")
            if result.stdout.strip():
                print(f"Output:\n{result.stdout}")
            return False
            
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run test suite with different categories."""
    print("🧪 Floridify Test Suite Runner")
    print("=" * 50)
    
    results = []
    
    # Unit tests (fast)
    results.append(run_command(
        ["uv", "run", "python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        "Unit Tests"
    ))
    
    # Quality tests (search algorithms)
    results.append(run_command(
        ["uv", "run", "python", "-m", "pytest", "tests/quality/", "-v", "--tb=short"],
        "Quality Tests (Search Algorithms)"
    ))
    
    # Integration tests (may require external services)
    results.append(run_command(
        ["uv", "run", "python", "-m", "pytest", "tests/integration/", "-v", "--tb=short", "-x"],
        "Integration Tests"
    ))
    
    # Type checking
    results.append(run_command(
        ["uv", "run", "mypy", "src/floridify/", "--strict"],
        "Type Checking"
    ))
    
    # Linting
    results.append(run_command(
        ["uv", "run", "ruff", "check", "src/", "tests/"],
        "Code Linting"
    ))
    
    # Coverage report (optional)
    coverage_success = run_command(
        ["uv", "run", "python", "-m", "pytest", "tests/unit/", "tests/quality/", 
         "--cov=src/floridify", "--cov-report=term-missing", "--cov-report=html"],
        "Coverage Report"
    )
    results.append(coverage_success)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    test_categories = [
        "Unit Tests",
        "Quality Tests", 
        "Integration Tests",
        "Type Checking",
        "Code Linting",
        "Coverage Report"
    ]
    
    for i, (category, success) in enumerate(zip(test_categories, results)):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{category:20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()