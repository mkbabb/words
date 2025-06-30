#!/usr/bin/env python3
"""Script to systematically fix tautological tests and align them with actual codebase."""

import subprocess
import sys
from pathlib import Path


def run_pytest(test_path: str) -> tuple[int, str]:
    """Run pytest on a specific test file and return exit code and output."""
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", test_path, "--tb=short", "-v"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Test timed out"
    except Exception as e:
        return 1, f"Error running test: {e}"


def analyze_test_file(test_file: Path) -> dict:
    """Analyze a test file for common tautological patterns."""
    content = test_file.read_text()
    
    analysis = {
        "file": str(test_file),
        "total_lines": len(content.splitlines()),
        "has_mock_imports": "from unittest.mock import" in content,
        "mock_patch_count": content.count("@patch(") + content.count("with patch("),
        "async_mock_count": content.count("AsyncMock"),
        "magic_mock_count": content.count("MagicMock"),
        "has_real_imports": any(
            "from src.floridify" in line and "mock" not in line.lower()
            for line in content.splitlines()
        ),
        "test_count": content.count("def test_"),
    }
    
    return analysis


def main():
    """Main function to analyze and fix tests."""
    test_dir = Path("tests/cli")
    test_files = list(test_dir.glob("test_*.py"))
    
    print("=== Test Analysis Report ===")
    print(f"Found {len(test_files)} CLI test files")
    print()
    
    for test_file in test_files:
        if test_file.name == "test_lookup_integration.py":
            continue  # Skip our known good integration tests
            
        print(f"Analyzing {test_file.name}...")
        analysis = analyze_test_file(test_file)
        
        print(f"  Tests: {analysis['test_count']}")
        print(f"  Mocks: {analysis['mock_patch_count']} patches, "
              f"{analysis['async_mock_count']} AsyncMocks, "
              f"{analysis['magic_mock_count']} MagicMocks")
        print(f"  Real imports: {analysis['has_real_imports']}")
        
        # Run the tests
        exit_code, output = run_pytest(str(test_file))
        if exit_code == 0:
            print(f"  Status: ✅ PASSING")
        else:
            print(f"  Status: ❌ FAILING")
            # Extract key error info
            lines = output.splitlines()
            error_lines = [line for line in lines if "Error:" in line or "assert" in line.lower()]
            if error_lines:
                print(f"  Key errors: {error_lines[0][:80]}...")
        
        print()


if __name__ == "__main__":
    main()