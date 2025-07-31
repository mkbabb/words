#!/usr/bin/env python3
"""
Comprehensive testing script with UV integration and multiple test execution modes.
Supports unit tests, integration tests, performance benchmarks, and CI/CD workflows.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd: list[str], description: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"🔄 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start_time
    
    if result.returncode == 0:
        print(f"✅ {description} completed in {duration:.2f}s")
    else:
        print(f"❌ {description} failed in {duration:.2f}s")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()}")
        if check:
            sys.exit(1)
    
    return result


def run_linting() -> bool:
    """Run code quality checks."""
    print("\n📝 Running code quality checks...")
    
    success = True
    
    # Ruff linting
    result = run_command(
        ["uv", "run", "ruff", "check", "src/", "tests/"],
        "Running Ruff linter",
        check=False
    )
    if result.returncode != 0:
        success = False
    
    # Ruff formatting check
    result = run_command(
        ["uv", "run", "ruff", "format", "--check", "src/", "tests/"],
        "Checking code formatting",
        check=False
    )
    if result.returncode != 0:
        success = False
    
    # MyPy type checking
    result = run_command(
        ["uv", "run", "mypy", "src/floridify"],
        "Running MyPy type checker",
        check=False
    )
    if result.returncode != 0:
        success = False
    
    return success


def run_unit_tests(verbose: bool = False, coverage: bool = True) -> bool:
    """Run unit tests."""
    print("\n🔬 Running unit tests...")
    
    cmd = ["uv", "run", "pytest", "tests/unit/", "tests/api/"]
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    
    if coverage:
        cmd.extend([
            "--cov=src/floridify",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=80"
        ])
    
    # Skip slow and benchmark tests
    cmd.extend(["-m", "not slow and not benchmark"])
    
    result = run_command(cmd, "Unit tests", check=False)
    return result.returncode == 0


def run_integration_tests(verbose: bool = False) -> bool:
    """Run integration tests."""
    print("\n🔗 Running integration tests...")
    
    cmd = ["uv", "run", "pytest", "tests/integration/"]
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    
    # Skip benchmark tests
    cmd.extend(["-m", "not benchmark"])
    
    result = run_command(cmd, "Integration tests", check=False)
    return result.returncode == 0


def run_performance_tests(verbose: bool = False) -> bool:
    """Run performance benchmarks."""
    print("\n⚡ Running performance benchmarks...")
    
    cmd = [
        "uv", "run", "pytest", "tests/performance/",
        "--benchmark-only",
        "--benchmark-sort=mean",
        "--benchmark-columns=min,max,mean,stddev,rounds,iterations"
    ]
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    
    result = run_command(cmd, "Performance benchmarks", check=False)
    return result.returncode == 0


def run_specific_tests(test_path: str, verbose: bool = False) -> bool:
    """Run specific test file or directory."""
    print(f"\n🎯 Running specific tests: {test_path}")
    
    cmd = ["uv", "run", "pytest", test_path]
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    
    result = run_command(cmd, f"Tests in {test_path}", check=False)
    return result.returncode == 0


def run_quick_tests() -> bool:
    """Run quick smoke tests."""
    print("\n🚀 Running quick smoke tests...")
    
    cmd = [
        "uv", "run", "pytest",
        "tests/",
        "-m", "not slow and not benchmark and not integration",
        "--maxfail=5",
        "-x"  # Stop on first failure
    ]
    
    result = run_command(cmd, "Quick smoke tests", check=False)
    return result.returncode == 0


def run_all_tests(verbose: bool = False, coverage: bool = True) -> bool:
    """Run comprehensive test suite."""
    print("\n🧪 Running comprehensive test suite...")
    
    cmd = ["uv", "run", "pytest", "tests/"]
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    
    if coverage:
        cmd.extend([
            "--cov=src/floridify",
            "--cov-report=term-missing:skip-covered",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-fail-under=80"
        ])
    
    # Include all tests except benchmarks (run separately)
    cmd.extend(["-m", "not benchmark"])
    
    result = run_command(cmd, "Comprehensive test suite", check=False)
    return result.returncode == 0


def check_dependencies() -> bool:
    """Check that all dependencies are properly installed."""
    print("\n📦 Checking dependencies...")
    
    # Check UV installation
    result = run_command(["uv", "--version"], "Checking UV installation", check=False)
    if result.returncode != 0:
        print("❌ UV not found. Please install UV first.")
        return False
    
    # Sync dependencies
    result = run_command(
        ["uv", "sync", "--dev"],
        "Syncing dependencies",
        check=False
    )
    if result.returncode != 0:
        print("❌ Failed to sync dependencies.")
        return False
    
    return True


def generate_test_report() -> None:
    """Generate comprehensive test report."""
    print("\n📊 Generating test report...")
    
    # Run tests with detailed reporting
    cmd = [
        "uv", "run", "pytest", "tests/",
        "--html=reports/test-report.html",
        "--self-contained-html",
        "--cov=src/floridify",
        "--cov-report=html:reports/coverage",
        "--cov-report=xml:reports/coverage.xml",
        "--junit-xml=reports/junit.xml",
        "-m", "not benchmark"
    ]
    
    # Create reports directory
    Path("reports").mkdir(exist_ok=True)
    
    run_command(cmd, "Generating test report", check=False)
    
    print("\n📋 Test report generated:")
    print("   📄 HTML report: reports/test-report.html")
    print("   📊 Coverage report: reports/coverage/index.html")
    print("   📈 Coverage XML: reports/coverage.xml")
    print("   🔧 JUnit XML: reports/junit.xml")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner with UV integration")
    
    # Test modes
    parser.add_argument("--lint", action="store_true", help="Run code quality checks")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance benchmarks")
    parser.add_argument("--quick", action="store_true", help="Run quick smoke tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    
    # Test targeting
    parser.add_argument("--path", type=str, help="Run specific test file or directory")
    
    # Options  
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--no-deps", action="store_true", help="Skip dependency check")
    
    args = parser.parse_args()
    
    # If no specific mode selected, run all tests
    if not any([args.lint, args.unit, args.integration, args.performance, args.quick, args.path, args.report]):
        args.all = True
    
    success = True
    
    # Check dependencies unless skipped
    if not args.no_deps:
        if not check_dependencies():
            sys.exit(1)
    
    # Run linting if requested or if running all
    if args.lint or args.all:
        if not run_linting():
            success = False
    
    # Run specific test path
    if args.path:
        if not run_specific_tests(args.path, args.verbose):
            success = False
    
    # Run quick tests
    elif args.quick:
        if not run_quick_tests():
            success = False
    
    # Run unit tests
    elif args.unit:
        if not run_unit_tests(args.verbose, not args.no_coverage):
            success = False
    
    # Run integration tests
    elif args.integration:
        if not run_integration_tests(args.verbose):
            success = False
    
    # Run performance tests
    elif args.performance:
        if not run_performance_tests(args.verbose):
            success = False
    
    # Run all tests
    elif args.all:
        if not run_all_tests(args.verbose, not args.no_coverage):
            success = False
        
        # Also run performance tests separately
        if not run_performance_tests(args.verbose):
            print("⚠️  Performance tests failed, but continuing...")
    
    # Generate report
    if args.report:
        generate_test_report()
    
    # Final result
    if success:
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()