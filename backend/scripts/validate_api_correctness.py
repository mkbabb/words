#!/usr/bin/env python3
"""
Validate search correctness via API testing.
Tests actual API responses to ensure optimizations maintain correctness.
"""

import asyncio
import sys
import time
from collections import defaultdict

import httpx


BASE_URL = "http://localhost:8000"


async def test_search_correctness():
    """Test search API endpoints for correctness."""

    print("=" * 80)
    print("SEARCH API CORRECTNESS VALIDATION")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check health
        print("\n🔍 Checking backend health...")
        health = await client.get(f"{BASE_URL}/health")
        health_data = health.json()
        print(f"   Status: {health_data['status']}")
        print(f"   Services: {health_data['services']}")

        # Test cases with expected behavior
        test_cases = [
            {
                "query": "test",
                "search_type": "exact",
                "description": "Exact match",
                "expect_results": True,
            },
            {
                "query": "happy",
                "search_type": "semantic",
                "description": "Semantic search for emotion word",
                "expect_results": True,
                "validate_semantic": True,
            },
            {
                "query": "tset",  # misspelling of "test"
                "search_type": "fuzzy",
                "description": "Fuzzy match for misspelling",
                "expect_results": True,
            },
            {
                "query": "exampel",  # misspelling
                "search_type": "combined",
                "description": "Combined search with misspelling",
                "expect_results": True,
            },
        ]

        print("\n" + "=" * 80)
        print("RUNNING CORRECTNESS TESTS")
        print("=" * 80)

        passed = 0
        failed = 0
        results_summary = []

        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            search_type = test_case["search_type"]
            description = test_case["description"]
            expect_results = test_case.get("expect_results", True)

            print(f"\n[{i}/{len(test_cases)}] {description}")
            print(f"   Query: '{query}' | Type: {search_type}")

            start = time.perf_counter()
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/search/{query}",
                    params={
                        "search_type": search_type,
                        "max_results": 10,
                    },
                )
                latency_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    print(f"   ✅ Status: 200 | Latency: {latency_ms:.2f}ms")
                    print(f"   Results: {len(results)} found")

                    if results:
                        top_3 = [r.get("word", r.get("text", "N/A")) for r in results[:3]]
                        print(f"   Top 3: {top_3}")

                    # Validate expectations
                    if expect_results and not results:
                        print(f"   ❌ FAIL: Expected results but got none")
                        failed += 1
                        results_summary.append({
                            "test": description,
                            "status": "FAIL",
                            "reason": "No results when expected"
                        })
                    elif not expect_results and results:
                        print(f"   ⚠️  WARNING: Got results when none expected")
                        passed += 1  # Not a hard fail
                    else:
                        print(f"   ✅ PASS")
                        passed += 1
                        results_summary.append({
                            "test": description,
                            "status": "PASS",
                            "latency_ms": latency_ms,
                            "results_count": len(results)
                        })

                    # Additional semantic validation
                    if test_case.get("validate_semantic") and results:
                        # For "happy" we expect emotion-related words
                        emotion_words = {"happy", "sad", "joy", "joyful", "pleased", "glad", "cheerful"}
                        found_words = {r.get("word", "").lower() for r in results[:5]}
                        overlap = emotion_words.intersection(found_words)
                        if overlap:
                            print(f"   ✅ Semantic validation: Found emotion words {overlap}")
                        else:
                            print(f"   ⚠️  Semantic validation: No emotion words in top 5")

                else:
                    print(f"   ❌ FAIL: HTTP {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                    failed += 1
                    results_summary.append({
                        "test": description,
                        "status": "FAIL",
                        "reason": f"HTTP {response.status_code}"
                    })

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                failed += 1
                results_summary.append({
                    "test": description,
                    "status": "ERROR",
                    "reason": str(e)
                })

        # Summary
        print("\n" + "=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print(f"✅ Passed: {passed}/{len(test_cases)}")
        print(f"❌ Failed: {failed}/{len(test_cases)}")

        if failed > 0:
            print("\n⚠️  FAILED TESTS:")
            for result in results_summary:
                if result["status"] in ["FAIL", "ERROR"]:
                    print(f"   - {result['test']}: {result.get('reason', 'Unknown')}")

        return failed == 0


async def test_performance_regression():
    """Test that optimizations don't cause performance regression."""

    print("\n" + "=" * 80)
    print("PERFORMANCE REGRESSION CHECK")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Warm up
        print("\n🔥 Warming up cache...")
        for _ in range(3):
            await client.get(f"{BASE_URL}/api/v1/search/test?max_results=5")

        # Benchmark different search types
        search_types = ["exact", "fuzzy", "semantic", "combined"]
        queries = ["test", "happy", "example", "word"]

        latencies = defaultdict(list)

        print("\n📊 Running performance measurements...")
        for search_type in search_types:
            print(f"\n   Testing {search_type} search...")
            for query in queries:
                start = time.perf_counter()
                response = await client.get(
                    f"{BASE_URL}/api/v1/search/{query}",
                    params={"search_type": search_type, "max_results": 10},
                )
                latency_ms = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    latencies[search_type].append(latency_ms)

        # Report latencies
        print("\n📈 Latency Report:")
        regression_detected = False
        for search_type, times in latencies.items():
            if not times:
                continue
            mean = sum(times) / len(times)
            p95 = sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]

            print(f"\n   {search_type.upper()}:")
            print(f"      Mean: {mean:.2f}ms")
            print(f"      P95:  {p95:.2f}ms")

            # Check for obvious regressions
            # Semantic should be < 100ms with optimizations
            # Exact/fuzzy should be < 50ms
            if search_type == "semantic" and p95 > 100:
                print(f"      ⚠️  WARNING: Semantic P95 > 100ms (got {p95:.2f}ms)")
                regression_detected = True
            elif search_type in ["exact", "fuzzy"] and p95 > 50:
                print(f"      ⚠️  WARNING: {search_type} P95 > 50ms (got {p95:.2f}ms)")
                regression_detected = True
            else:
                print(f"      ✅ Within expected range")

        return not regression_detected


async def test_cache_functionality():
    """Test that caching is working correctly."""

    print("\n" + "=" * 80)
    print("CACHE FUNCTIONALITY CHECK")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0) as client:
        query = "test"

        # First request (cold)
        print("\n🥶 Cold request...")
        start = time.perf_counter()
        response1 = await client.get(f"{BASE_URL}/api/v1/search/{query}?max_results=10")
        latency1_ms = (time.perf_counter() - start) * 1000
        print(f"   Latency: {latency1_ms:.2f}ms")

        # Second request (should be cached)
        print("\n🔥 Cached request...")
        start = time.perf_counter()
        response2 = await client.get(f"{BASE_URL}/api/v1/search/{query}?max_results=10")
        latency2_ms = (time.perf_counter() - start) * 1000
        print(f"   Latency: {latency2_ms:.2f}ms")

        # Check results are consistent
        if response1.json() == response2.json():
            print(f"   ✅ Results consistent")
        else:
            print(f"   ❌ Results differ between requests!")
            return False

        # Cached should be faster (though MongoDB might cache too)
        if latency2_ms < latency1_ms * 1.5:  # Allow some variance
            speedup = (latency1_ms - latency2_ms) / latency1_ms * 100
            print(f"   ✅ Cached request faster or similar ({speedup:+.1f}% difference)")
        else:
            print(f"   ⚠️  Cached request slower ({latency2_ms:.2f}ms vs {latency1_ms:.2f}ms)")

        return True


if __name__ == "__main__":
    async def main():
        try:
            # Run all tests
            correctness_ok = await test_search_correctness()
            performance_ok = await test_performance_regression()
            cache_ok = await test_cache_functionality()

            print("\n" + "=" * 80)
            print("FINAL VALIDATION RESULTS")
            print("=" * 80)
            print(f"✅ Search Correctness: {'PASS' if correctness_ok else 'FAIL'}")
            print(f"✅ Performance Check: {'PASS' if performance_ok else 'WARNING'}")
            print(f"✅ Cache Functionality: {'PASS' if cache_ok else 'FAIL'}")

            if correctness_ok and cache_ok:
                print("\n✅ ALL CRITICAL VALIDATIONS PASSED")
                if not performance_ok:
                    print("⚠️  Performance warnings detected but not blocking")
                sys.exit(0)
            else:
                print("\n❌ VALIDATION FAILED")
                sys.exit(1)

        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    asyncio.run(main())
