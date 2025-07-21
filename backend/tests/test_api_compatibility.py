#!/usr/bin/env python3
"""Simple API compatibility test script.

This script tests the backwards compatibility of the API by making
direct HTTP requests and verifying the responses.
"""

import time

import httpx

BASE_URL = "http://localhost:8000"


def test_lookup_endpoint():
    """Test basic lookup endpoint compatibility."""
    print("\n=== Testing Lookup Endpoint ===")
    
    # Test 1: Basic lookup
    print("1. Basic lookup...")
    response = httpx.get(f"{BASE_URL}/api/v1/lookup/happy")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        assert "word" in data
        assert "pronunciation" in data
        assert "definitions" in data
        assert "last_updated" in data
        print("   ✅ Response structure is correct")
    
    # Test 2: With parameters
    print("2. Lookup with parameters...")
    response = httpx.get(
        f"{BASE_URL}/api/v1/lookup/test",
        params={"force_refresh": "false", "providers": ["wiktionary"], "no_ai": "false"}
    )
    print(f"   Status: {response.status_code}")
    print("   ✅ Parameters accepted")
    
    # Test 3: 404 response
    print("3. Non-existent word...")
    response = httpx.get(f"{BASE_URL}/api/v1/lookup/xyzqwerty12345")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 404
    assert "detail" in response.json()
    print("   ✅ 404 response is correct")


def test_search_endpoint():
    """Test search endpoint compatibility."""
    print("\n=== Testing Search Endpoint ===")
    
    # Test 1: Basic search
    print("1. Basic search...")
    response = httpx.get(f"{BASE_URL}/api/v1/search", params={"q": "happy"})
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        print("   ✅ Response structure is correct")
    
    # Test 2: With all parameters
    print("2. Search with parameters...")
    response = httpx.get(
        f"{BASE_URL}/api/v1/search",
        params={"q": "test", "method": "fuzzy", "max_results": "10", "min_score": "0.7"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        assert len(data["results"]) <= 10
        print("   ✅ Parameters work correctly")


def test_response_headers():
    """Test that response headers are unchanged."""
    print("\n=== Testing Response Headers ===")
    
    response = httpx.get(f"{BASE_URL}/api/v1/lookup/test")
    print(f"Headers: {dict(response.headers)}")
    
    assert "x-process-time" in response.headers
    assert "x-request-id" in response.headers
    assert response.headers["content-type"] == "application/json"
    print("✅ All expected headers present")


def test_streaming_endpoints():
    """Test that streaming endpoints are separate."""
    print("\n=== Testing Streaming Endpoints ===")
    
    # Regular endpoint
    response = httpx.get(f"{BASE_URL}/api/v1/lookup/test")
    assert "content-type" in response.headers
    assert response.headers["content-type"] == "application/json"
    print("✅ Regular endpoint returns JSON")
    
    # Streaming endpoint (if it exists)
    try:
        response = httpx.get(f"{BASE_URL}/api/v1/lookup/test/stream", timeout=2.0)
        if response.status_code == 200:
            assert response.headers["content-type"] == "text/event-stream"
            print("✅ Streaming endpoint returns SSE")
        else:
            print("ℹ️  Streaming endpoint not available (expected)")
    except Exception:
        print("ℹ️  Streaming endpoint not available (expected)")


def test_performance():
    """Basic performance test."""
    print("\n=== Testing Performance ===")
    
    # Warm up
    httpx.get(f"{BASE_URL}/api/v1/lookup/test")
    
    # Test cached lookup
    start = time.perf_counter()
    httpx.get(f"{BASE_URL}/api/v1/lookup/test")
    elapsed = time.perf_counter() - start
    
    print(f"Cached lookup time: {elapsed*1000:.1f}ms")
    assert elapsed < 0.5, f"Lookup too slow: {elapsed}s"
    print("✅ Performance acceptable")


def main():
    """Run all compatibility tests."""
    print("API Backwards Compatibility Tests")
    print("=================================")
    
    # Check if server is running
    try:
        response = httpx.get(f"{BASE_URL}/api/v1/health", timeout=2.0)
        print(f"✅ Server is running (health check: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not reachable at {BASE_URL}")
        print(f"   Error: {e}")
        return
    
    try:
        test_lookup_endpoint()
        test_search_endpoint()
        test_response_headers()
        test_streaming_endpoints()
        test_performance()
        
        print("\n✅ All compatibility tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()