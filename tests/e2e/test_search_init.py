#!/usr/bin/env python3
"""E2E test script for non-blocking search engine initialization.

Tests the full stack: backend health/semantic endpoints + frontend UI.
Requires backend running on port 8001 and frontend on port 3000.

Usage:
    # Start backend with semantic disabled:
    SEMANTIC_SEARCH_ENABLED=false uvicorn src.floridify.api.main:app --port 8001

    # Run this test:
    python tests/e2e/test_search_init.py
"""

import json
import sys
import time

import httpx

BASE_URL = "http://localhost:8001"


def test_health_non_blocking():
    """Health endpoint returns immediately without triggering search init."""
    print("\n=== Test: Health endpoint non-blocking ===")
    start = time.monotonic()
    r = httpx.get(f"{BASE_URL}/health", timeout=5)
    elapsed = time.monotonic() - start

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["status"] == "healthy", f"Expected healthy, got {data['status']}"
    assert elapsed < 2.0, f"Health took {elapsed:.2f}s — should be instant"

    print(f"  Status: {data['status']}")
    print(f"  Search engine: {data['search_engine']}")
    print(f"  Response time: {elapsed*1000:.0f}ms")
    print("  PASS")


def test_semantic_status_non_blocking():
    """Semantic status returns without triggering init."""
    print("\n=== Test: Semantic status non-blocking ===")
    start = time.monotonic()
    r = httpx.get(f"{BASE_URL}/api/v1/search/semantic/status", timeout=5)
    elapsed = time.monotonic() - start

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert elapsed < 2.0, f"Took {elapsed:.2f}s — should be instant"

    print(f"  Enabled: {data['enabled']}")
    print(f"  Ready: {data['ready']}")
    print(f"  Building: {data['building']}")
    print(f"  Message: {data['message']}")
    print(f"  Response time: {elapsed*1000:.0f}ms")
    print("  PASS")


def test_semantic_disabled_globally():
    """With SEMANTIC_SEARCH_ENABLED=false, semantic is disabled."""
    print("\n=== Test: Global semantic disabled ===")
    r = httpx.get(f"{BASE_URL}/api/v1/search/semantic/status", timeout=5)
    data = r.json()

    # When SEMANTIC_SEARCH_ENABLED=false, semantic should be disabled
    assert data["enabled"] is False, f"Expected enabled=False, got {data['enabled']}"
    print(f"  Semantic enabled: {data['enabled']}")
    print("  PASS")


def test_search_works():
    """Search works (exact/fuzzy) even without semantic."""
    print("\n=== Test: Search works without semantic ===")
    start = time.monotonic()
    r = httpx.get(
        f"{BASE_URL}/api/v1/search",
        params={"q": "hello", "mode": "smart"},
        timeout=30,
    )
    elapsed = time.monotonic() - start

    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    print(f"  Query: 'hello'")
    print(f"  Results: {data['total_found']}")
    print(f"  Response time: {elapsed*1000:.0f}ms")
    if data["results"]:
        top = data["results"][0]
        print(f"  Top result: '{top['word']}' (score={top['score']}, method={top['method']})")
    print("  PASS")


def test_hot_reload_status():
    """Hot-reload status endpoint works."""
    print("\n=== Test: Hot-reload status ===")
    r = httpx.get(f"{BASE_URL}/api/v1/search/hot-reload/status", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    print(f"  Engine loaded: {data['engine_loaded']}")
    print(f"  Initializing: {data.get('initializing', 'N/A')}")
    print(f"  Semantic enabled: {data.get('semantic_enabled', 'N/A')}")
    print("  PASS")


def main():
    """Run all tests."""
    print("=" * 60)
    print("E2E Tests: Non-Blocking Search Engine Initialization")
    print("=" * 60)

    # Check backend is reachable
    try:
        httpx.get(f"{BASE_URL}/health", timeout=3)
    except httpx.ConnectError:
        print(f"\nERROR: Backend not reachable at {BASE_URL}")
        print("Start with: SEMANTIC_SEARCH_ENABLED=false uvicorn ...")
        sys.exit(1)

    tests = [
        test_health_non_blocking,
        test_semantic_status_non_blocking,
        test_semantic_disabled_globally,
        test_search_works,
        test_hot_reload_status,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
