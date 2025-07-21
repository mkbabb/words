"""Comprehensive backwards compatibility tests for API changes.

This test suite ensures that all recent changes maintain full backwards
compatibility with existing API clients. It tests:
1. All existing endpoints work without streaming/state tracking
2. Response schemas match exactly (no required fields added)
3. Existing API clients continue to work
4. Performance is not degraded
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from floridify.api.models.responses import LookupResponse, SearchResponse


class TestBackwardsCompatibility:
    """Test suite for ensuring backwards compatibility."""
    
    def test_lookup_without_streaming(self, client: TestClient) -> None:
        """Test that regular lookup works exactly as before without streaming."""
        # Test basic lookup
        response = client.get("/api/v1/lookup/happy")
        assert response.status_code == 200
        
        # Validate response structure matches original schema
        data = response.json()
        
        # Required fields from original API
        assert "word" in data
        assert "pronunciation" in data
        assert "definitions" in data
        assert "last_updated" in data
        
        # Ensure no new required fields were added
        try:
            LookupResponse(**data)
        except ValidationError as e:
            pytest.fail(f"Response validation failed: {e}")
        
        # Verify pronunciation structure
        pronunciation = data["pronunciation"]
        assert "phonetic" in pronunciation
        assert isinstance(pronunciation["phonetic"], str)
        
        # Verify definitions structure
        definitions = data["definitions"]
        assert isinstance(definitions, list)
        assert len(definitions) > 0
        
        for definition in definitions:
            # Original required fields
            assert "word_type" in definition
            assert "definition" in definition
            assert "synonyms" in definition
            assert "examples" in definition
            
            # Check types
            assert isinstance(definition["word_type"], str)
            assert isinstance(definition["definition"], str)
            assert isinstance(definition["synonyms"], list)
            assert isinstance(definition["examples"], dict)
    
    def test_search_without_streaming(self, client: TestClient) -> None:
        """Test that regular search works exactly as before without streaming."""
        # Test basic search
        response = client.get("/api/v1/search?q=happy")
        assert response.status_code == 200
        
        # Validate response structure matches original schema
        data = response.json()
        
        # Required fields from original API
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        
        # Ensure no new required fields were added
        try:
            SearchResponse(**data)
        except ValidationError as e:
            pytest.fail(f"Response validation failed: {e}")
        
        # Verify results structure
        results = data["results"]
        assert isinstance(results, list)
        
        for result in results:
            # Original required fields
            assert "word" in result
            assert "score" in result
            assert "method" in result
            assert "is_phrase" in result
            
            # Check types
            assert isinstance(result["word"], str)
            assert isinstance(result["score"], float)
            assert isinstance(result["method"], str)
            assert isinstance(result["is_phrase"], bool)
            
            # Validate score range
            assert 0.0 <= result["score"] <= 1.0
    
    def test_all_query_parameters_work(self, client: TestClient) -> None:
        """Test that all original query parameters still work correctly."""
        # Test lookup with all parameters
        response = client.get(
            "/api/v1/lookup/test"
            "?force_refresh=true"
            "&providers=wiktionary"
            "&providers=dictionary_com"
            "&no_ai=true"
        )
        assert response.status_code in [200, 404]
        
        # Test search with all parameters
        response = client.get(
            "/api/v1/search"
            "?q=test"
            "&method=hybrid"
            "&max_results=50"
            "&min_score=0.5"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 50
        assert all(r["score"] >= 0.5 for r in data["results"])
    
    def test_force_refresh_functionality(self, client: TestClient) -> None:
        """Test that force_refresh parameter still works correctly."""
        word = "algorithm"
        
        # First request without force_refresh
        response1 = client.get(f"/api/v1/lookup/{word}")
        
        # Second request with force_refresh
        response2 = client.get(f"/api/v1/lookup/{word}?force_refresh=true")
        
        # Both should return same structure
        if response1.status_code == 200:
            assert response2.status_code == 200
            
            data1 = response1.json()
            data2 = response2.json()
            
            # Structure should be identical
            assert set(data1.keys()) == set(data2.keys())
            assert data1["word"] == data2["word"]
    
    def test_no_ai_mode(self, client: TestClient) -> None:
        """Test that no_ai parameter still works correctly."""
        # Test with AI
        response_with_ai = client.get("/api/v1/lookup/happy?no_ai=false")
        
        # Test without AI
        response_no_ai = client.get("/api/v1/lookup/happy?no_ai=true")
        
        # Both should work (might return different results)
        assert response_with_ai.status_code in [200, 404]
        assert response_no_ai.status_code in [200, 404]
        
        # If both found, structure should be the same
        if response_with_ai.status_code == 200 and response_no_ai.status_code == 200:
            data_with_ai = response_with_ai.json()
            data_no_ai = response_no_ai.json()
            
            # Same top-level structure
            assert set(data_with_ai.keys()) == set(data_no_ai.keys())
    
    def test_all_search_methods(self, client: TestClient) -> None:
        """Test that all search methods still work correctly."""
        methods = ["exact", "fuzzy", "semantic", "hybrid"]
        
        for method in methods:
            response = client.get(f"/api/v1/search?q=test&method={method}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["query"] == "test"
            assert isinstance(data["results"], list)
            
            # Results should use appropriate method
            if data["results"] and method != "hybrid":
                # In hybrid mode, different methods might be used
                for result in data["results"]:
                    if method != "hybrid":
                        assert result["method"] in [method, "exact", "fuzzy", "semantic"]
    
    def test_error_responses_unchanged(self, client: TestClient) -> None:
        """Test that error responses remain unchanged."""
        # Test 404 response
        response = client.get("/api/v1/lookup/xyzqwerty12345")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)
        
        # Test 422 validation error
        response = client.get("/api/v1/search?q=")  # Empty query
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
    
    def test_response_headers_unchanged(self, client: TestClient) -> None:
        """Test that response headers remain unchanged."""
        response = client.get("/api/v1/lookup/test")
        
        # Original headers should still be present
        assert "X-Process-Time" in response.headers
        assert "X-Request-ID" in response.headers
        assert "Content-Type" in response.headers
        
        # Validate header formats
        process_time = int(response.headers["X-Process-Time"])
        assert process_time >= 0
        
        # Content type should be JSON for regular endpoints
        assert response.headers["Content-Type"] == "application/json"
    
    def test_concurrent_compatibility(self, client: TestClient) -> None:
        """Test that concurrent requests work as before."""
        def make_request(endpoint: str) -> dict[str, Any]:
            if "lookup" in endpoint:
                response = client.get(endpoint)
            else:
                response = client.get(endpoint)
            return {
                "endpoint": endpoint,
                "status": response.status_code,
                "headers": dict(response.headers),
            }
        
        # Mix of different endpoints
        endpoints = [
            "/api/v1/lookup/happy",
            "/api/v1/search?q=test",
            "/api/v1/lookup/algorithm?force_refresh=true",
            "/api/v1/search?q=cogn&method=fuzzy",
            "/api/v1/lookup/beautiful?no_ai=true",
        ]
        
        # Execute concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(make_request, endpoints))
        
        # All should complete successfully
        for result in results:
            assert result["status"] in [200, 404]
            assert "X-Process-Time" in result["headers"]
            assert "X-Request-ID" in result["headers"]


class TestPerformanceBenchmark:
    """Performance regression tests to ensure no degradation."""
    
    def test_lookup_performance_baseline(self, client: TestClient) -> None:
        """Test that lookup performance hasn't degraded."""
        words = ["happy", "algorithm", "beautiful", "computer", "science"]
        timings = []
        
        for word in words:
            start = time.perf_counter()
            response = client.get(f"/api/v1/lookup/{word}")
            elapsed = time.perf_counter() - start
            
            if response.status_code == 200:
                timings.append(elapsed)
        
        if timings:
            avg_time = sum(timings) / len(timings)
            # Average lookup should complete within 500ms
            assert avg_time < 0.5, f"Average lookup time {avg_time:.3f}s exceeds threshold"
    
    def test_search_performance_baseline(self, client: TestClient) -> None:
        """Test that search performance hasn't degraded."""
        queries = ["test", "happ", "alg", "beautiful", "comp"]
        timings = []
        
        for query in queries:
            start = time.perf_counter()
            response = client.get(f"/api/v1/search?q={query}")
            elapsed = time.perf_counter() - start
            
            assert response.status_code == 200
            timings.append(elapsed)
        
        avg_time = sum(timings) / len(timings)
        # Average search should complete within 200ms
        assert avg_time < 0.2, f"Average search time {avg_time:.3f}s exceeds threshold"
    
    def test_cached_performance(self, client: TestClient) -> None:
        """Test that caching still works effectively."""
        word = "caching_test"
        
        # First request (cache miss)
        start1 = time.perf_counter()
        response1 = client.get(f"/api/v1/lookup/{word}")
        time1 = time.perf_counter() - start1
        
        # Second request (should be cached)
        start2 = time.perf_counter()
        response2 = client.get(f"/api/v1/lookup/{word}")
        time2 = time.perf_counter() - start2
        
        # Both should return same status
        assert response1.status_code == response2.status_code
        
        # Cached request should be significantly faster (if found)
        if response1.status_code == 200:
            # Cached should be at least 50% faster
            assert time2 < time1 * 0.5, f"Cache not effective: {time2:.3f}s vs {time1:.3f}s"


class TestStreamingEndpoints:
    """Test that streaming endpoints don't interfere with regular endpoints."""
    
    def test_streaming_endpoints_separate(self, client: TestClient) -> None:
        """Test that streaming endpoints are separate from regular ones."""
        # Regular endpoints should work normally
        response = client.get("/api/v1/lookup/test")
        assert response.status_code in [200, 404]
        assert response.headers["Content-Type"] == "application/json"
        
        response = client.get("/api/v1/search?q=test")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        
        # Streaming endpoints should be different paths
        response = client.get("/api/v1/lookup/test/stream")
        # Should exist but return SSE content type
        if response.status_code == 200:
            assert response.headers["Content-Type"] == "text/event-stream"
        
        response = client.get("/api/v1/search/stream?q=test")
        if response.status_code == 200:
            assert response.headers["Content-Type"] == "text/event-stream"
    
    def test_streaming_doesnt_affect_regular(self, client: TestClient) -> None:
        """Test that using streaming endpoints doesn't affect regular ones."""
        # Make streaming request
        stream_response = client.get("/api/v1/lookup/happy/stream", stream=True)
        
        # Regular endpoint should still work normally
        regular_response = client.get("/api/v1/lookup/happy")
        assert regular_response.status_code == 200
        assert regular_response.headers["Content-Type"] == "application/json"
        
        # Close streaming connection
        stream_response.close()
        
        # Validate regular response structure
        data = regular_response.json()
        assert all(key in data for key in ["word", "pronunciation", "definitions", "last_updated"])


class TestAPIClientSimulation:
    """Simulate various API client behaviors to ensure compatibility."""
    
    def test_legacy_client_behavior(self, client: TestClient) -> None:
        """Simulate a legacy client that expects exact response format."""
        # Legacy client making sequential requests
        words_to_lookup = ["happy", "sad", "algorithm"]
        results = []
        
        for word in words_to_lookup:
            response = client.get(f"/api/v1/lookup/{word}")
            if response.status_code == 200:
                data = response.json()
                # Legacy client expects these exact fields
                result = {
                    "word": data["word"],
                    "phonetic": data["pronunciation"]["phonetic"],
                    "definitions": [
                        {
                            "type": d["word_type"],
                            "meaning": d["definition"],
                            "synonyms": d["synonyms"]
                        }
                        for d in data["definitions"]
                    ]
                }
                results.append(result)
        
        # Should successfully process at least some words
        assert len(results) > 0
    
    def test_mobile_client_behavior(self, client: TestClient) -> None:
        """Simulate a mobile client with specific requirements."""
        # Mobile client with timeout and retry behavior
        max_retries = 3
        timeout_ms = 1000
        
        for attempt in range(max_retries):
            start = time.perf_counter()
            response = client.get("/api/v1/search?q=test&max_results=10")
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200 and elapsed_ms < timeout_ms:
                data = response.json()
                # Mobile client needs compact results
                assert len(data["results"]) <= 10
                assert data["search_time_ms"] < timeout_ms
                break
        else:
            pytest.fail("Mobile client simulation failed after retries")
    
    def test_web_app_client_behavior(self, client: TestClient) -> None:
        """Simulate a web application client behavior."""
        # Web app making parallel requests
        import concurrent.futures
        
        def fetch_definition(word: str) -> dict[str, Any] | None:
            response = client.get(f"/api/v1/lookup/{word}")
            if response.status_code == 200:
                return response.json()
            return None
        
        def search_words(query: str) -> dict[str, Any]:
            response = client.get(f"/api/v1/search?q={query}")
            return response.json()
        
        # Simulate user typing and searching
        search_queries = ["h", "ha", "hap", "happ", "happy"]
        search_results = []
        
        for query in search_queries:
            result = search_words(query)
            search_results.append(result)
        
        # All searches should succeed
        assert all(r["query"] == q for r, q in zip(search_results, search_queries))
        
        # Then fetch full definitions for top results
        if search_results[-1]["results"]:
            top_words = [r["word"] for r in search_results[-1]["results"][:3]]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                definitions = list(executor.map(fetch_definition, top_words))
            
            # Should get at least some definitions
            assert any(d is not None for d in definitions)


def test_documentation_examples(client: TestClient) -> None:
    """Test that all examples from API documentation still work."""
    # Example from lookup endpoint docs
    response = client.get("/api/v1/lookup/serendipity?providers=wiktionary&force_refresh=false")
    assert response.status_code in [200, 404]
    
    # Example from search endpoint docs  
    response = client.get("/api/v1/search?q=cogn&method=hybrid&max_results=10&min_score=0.7")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "cogn"
    assert len(data["results"]) <= 10
    assert all(r["score"] >= 0.7 for r in data["results"])


def test_no_breaking_changes_summary(client: TestClient) -> None:
    """Summary test to ensure no breaking changes were introduced."""
    breaking_changes = []
    
    # Test 1: Response schemas
    try:
        response = client.get("/api/v1/lookup/test")
        if response.status_code == 200:
            LookupResponse(**response.json())
    except Exception as e:
        breaking_changes.append(f"Lookup response schema changed: {e}")
    
    try:
        response = client.get("/api/v1/search?q=test")
        if response.status_code == 200:
            SearchResponse(**response.json())
    except Exception as e:
        breaking_changes.append(f"Search response schema changed: {e}")
    
    # Test 2: Required parameters
    response = client.get("/api/v1/lookup/test")
    if response.status_code not in [200, 404]:
        breaking_changes.append(f"Lookup endpoint behavior changed: {response.status_code}")
    
    response = client.get("/api/v1/search?q=test")
    if response.status_code != 200:
        breaking_changes.append(f"Search endpoint behavior changed: {response.status_code}")
    
    # Test 3: Default behaviors
    response1 = client.get("/api/v1/lookup/happy")
    response2 = client.get("/api/v1/lookup/happy?force_refresh=false&providers=wiktionary&no_ai=false")
    if response1.status_code == 200 and response2.status_code == 200:
        # Default parameters should give same result
        if response1.json()["word"] != response2.json()["word"]:
            breaking_changes.append("Default parameter behavior changed")
    
    # Report any breaking changes
    if breaking_changes:
        pytest.fail("Breaking changes detected:\n" + "\n".join(breaking_changes))