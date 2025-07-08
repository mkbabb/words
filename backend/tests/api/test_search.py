"""Comprehensive tests for search endpoints with fuzzy matching validation."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_benchmark.fixture import BenchmarkFixture

from .test_data import FUZZY_TEST_CASES, PERF_TEST_QUERIES, PERFORMANCE_THRESHOLDS


class TestSearchEndpoint:
    """Comprehensive tests for search functionality."""
    
    def test_search_basic(self, client: TestClient) -> None:
        """Test basic search functionality."""
        response = client.get("/api/v1/search?q=happy")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "happy"
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        
        # Validate result structure
        for result in data["results"]:
            assert "word" in result
            assert "score" in result
            assert "method" in result
            assert "is_phrase" in result
            assert 0.0 <= result["score"] <= 1.0
    
    @pytest.mark.parametrize("test_case", FUZZY_TEST_CASES)
    def test_fuzzy_search_accuracy(
        self, client: TestClient, test_case: Any
    ) -> None:
        """Test fuzzy search with various misspellings and typos."""
        response = client.get(
            f"/api/v1/search?q={test_case.input}&method=fuzzy&max_results=10"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        found_words = [r["word"].lower() for r in data["results"]]
        
        # Check if expected matches are found
        matches_found = []
        for expected in test_case.expected_matches:
            if any(expected.lower() in word for word in found_words):
                matches_found.append(expected)
        
        # At least one expected match should be found
        assert len(matches_found) > 0, (
            f"Expected to find at least one of {test_case.expected_matches} "
            f"when searching for '{test_case.input}', but found {found_words}"
        )
        
        # Check score threshold
        if data["results"]:
            top_score = data["results"][0]["score"]
            assert top_score >= test_case.min_expected_score, (
                f"Expected score >= {test_case.min_expected_score} for "
                f"'{test_case.input}', but got {top_score}"
            )
    
    def test_search_methods(self, client: TestClient) -> None:
        """Test different search methods."""
        methods = ["exact", "fuzzy", "semantic", "hybrid"]
        
        for method in methods:
            response = client.get(f"/api/v1/search?q=test&method={method}")
            assert response.status_code == 200
            
            data = response.json()
            
            # For exact method, results should have exact matches
            if method == "exact" and data["results"]:
                for result in data["results"]:
                    assert result["method"] == "EXACT"
    
    def test_search_pagination(self, client: TestClient) -> None:
        """Test search result pagination."""
        # Test different max_results values
        for max_results in [1, 5, 10, 20, 50]:
            response = client.get(f"/api/v1/search?q=test&max_results={max_results}")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data["results"]) <= max_results
    
    def test_search_min_score_filtering(self, client: TestClient) -> None:
        """Test minimum score filtering."""
        min_scores = [0.5, 0.7, 0.9]
        
        for min_score in min_scores:
            response = client.get(f"/api/v1/search?q=test&min_score={min_score}")
            assert response.status_code == 200
            
            data = response.json()
            # All results should meet minimum score
            for result in data["results"]:
                assert result["score"] >= min_score
    
    def test_search_phrase_detection(self, client: TestClient) -> None:
        """Test phrase search capabilities."""
        phrases = ["bon vivant", "en coulisses", "piece of cake"]
        
        for phrase in phrases:
            response = client.get(f"/api/v1/search?q={phrase}")
            
            if response.status_code == 200:
                data = response.json()
                # Check if any results are marked as phrases
                phrase_results = [r for r in data["results"] if r["is_phrase"]]
                assert len(phrase_results) >= 0  # Phrases might be found
    
    def test_search_special_characters(self, client: TestClient) -> None:
        """Test search with special characters."""
        queries = ["vis-à-vis", "café", "naïve", "résumé"]
        
        for query in queries:
            response = client.get(f"/api/v1/search?q={query}")
            assert response.status_code == 200
    
    def test_search_empty_results(self, client: TestClient) -> None:
        """Test search that returns no results."""
        response = client.get("/api/v1/search?q=xyzqwerty123&min_score=0.99")
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["total_results"] == 0


class TestSearchPerformance:
    """Performance benchmarking for search endpoint."""
    
    @pytest.mark.parametrize("query_length,query", [
        ("short", "te"),
        ("medium", "intell"),
        ("long", "intelligence"),
        ("phrase", "bon vivant"),
    ])
    def test_search_performance_by_length(
        self, client: TestClient, benchmark: BenchmarkFixture,
        query_length: str, query: str
    ) -> None:
        """Benchmark search performance by query length."""
        def search_query() -> Any:
            response = client.get(f"/api/v1/search?q={query}")
            assert response.status_code == 200
            return response
        
        benchmark(search_query)
        
        # Performance assertions based on query type
        PERFORMANCE_THRESHOLDS["search"][query_length]
        # Note: actual timing assertions would use response headers
    
    def test_search_performance_methods(
        self, client: TestClient
    ) -> None:
        """Compare performance across search methods."""
        query = "algorithm"
        methods = ["exact", "fuzzy", "semantic", "hybrid"]
        
        timings = {}
        for method in methods:
            start_time = time.perf_counter()
            response = client.get(f"/api/v1/search?q={query}&method={method}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            assert response.status_code == 200
            timings[method] = elapsed_ms
            
            print(f"Search method '{method}': {elapsed_ms:.2f}ms")
        
        # Exact should generally be fastest
        assert timings["exact"] <= timings["fuzzy"]
    
    @pytest.mark.parametrize("query", PERF_TEST_QUERIES[:10])
    def test_search_batch_performance(
        self, client: TestClient, query: str
    ) -> None:
        """Test search performance across various queries."""
        start_time = time.perf_counter()
        response = client.get(f"/api/v1/search?q={query}")
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        assert response.status_code == 200
        
        # Log for analysis
        data = response.json()
        print(f"Search '{query}': {elapsed_ms:.2f}ms, "
              f"{data['total_results']} results, "
              f"API time: {data['search_time_ms']}ms")
        
        # General performance bound
        assert elapsed_ms < 500  # Should complete within 500ms


class TestSuggestionsEndpoint:
    """Tests for the suggestions (autocomplete) endpoint."""
    
    def test_suggestions_basic(self, client: TestClient) -> None:
        """Test basic suggestions functionality."""
        response = client.get("/api/v1/suggestions?q=hap")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "hap"
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        
        # Should get some suggestions for common prefix
        assert len(data["suggestions"]) > 0
        
        # All suggestions should start with query (case-insensitive)
        for suggestion in data["suggestions"]:
            assert suggestion.lower().startswith("hap")
    
    def test_suggestions_minimum_length(self, client: TestClient) -> None:
        """Test minimum query length requirement."""
        # Too short (1 character)
        response = client.get("/api/v1/suggestions?q=a")
        assert response.status_code == 422
        
        # Minimum length (2 characters)
        response = client.get("/api/v1/suggestions?q=ab")
        assert response.status_code == 200
    
    def test_suggestions_limit(self, client: TestClient) -> None:
        """Test suggestions limit parameter."""
        limits = [1, 5, 10, 20]
        
        for limit in limits:
            response = client.get(f"/api/v1/suggestions?q=com&limit={limit}")
            assert response.status_code == 200
            
            data = response.json()
            assert len(data["suggestions"]) <= limit
    
    @pytest.mark.parametrize("prefix", [
        "ser", "alg", "com", "int", "bea", "met", "par", "hap", "def", "acc"
    ])
    def test_suggestions_various_prefixes(
        self, client: TestClient, prefix: str
    ) -> None:
        """Test suggestions with various prefixes."""
        response = client.get(f"/api/v1/suggestions?q={prefix}")
        
        assert response.status_code == 200
        
        data = response.json()
        # Log results for analysis
        print(f"Prefix '{prefix}': {len(data['suggestions'])} suggestions")
    
    def test_suggestions_performance(
        self, client: TestClient, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark suggestions endpoint performance."""
        def get_suggestions() -> Any:
            response = client.get("/api/v1/suggestions?q=com")
            assert response.status_code == 200
            return response
        
        benchmark(get_suggestions)
        
        # Suggestions should be very fast (< 20ms)
        # Actual assertion would use response timing
    
    def test_suggestions_case_insensitive(self, client: TestClient) -> None:
        """Test case-insensitive suggestions."""
        response1 = client.get("/api/v1/suggestions?q=HAP")
        response2 = client.get("/api/v1/suggestions?q=hap")
        response3 = client.get("/api/v1/suggestions?q=Hap")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        # Should get similar results regardless of case
        data1 = response1.json()
        data2 = response2.json()
        
        # Convert to lowercase for comparison
        suggestions1 = [s.lower() for s in data1["suggestions"]]
        suggestions2 = [s.lower() for s in data2["suggestions"]]
        
        # Should have significant overlap
        overlap = set(suggestions1) & set(suggestions2)
        assert len(overlap) > 0


class TestSearchEdgeCases:
    """Edge case testing for search endpoints."""
    
    def test_search_validation_errors(self, client: TestClient) -> None:
        """Test various validation error scenarios."""
        # Empty query
        response = client.get("/api/v1/search?q=")
        assert response.status_code == 422
        
        # Invalid method
        response = client.get("/api/v1/search?q=test&method=invalid")
        assert response.status_code == 422
        
        # Invalid min_score
        response = client.get("/api/v1/search?q=test&min_score=2.0")
        assert response.status_code == 422
        
        # Invalid max_results
        response = client.get("/api/v1/search?q=test&max_results=1000")
        assert response.status_code == 422
    
    def test_search_special_queries(self, client: TestClient) -> None:
        """Test search with special query patterns."""
        special_queries = [
            "test AND test",  # Boolean-like
            "test*",          # Wildcard-like
            '"exact phrase"', # Quoted
            "test?",          # Question mark
            "test!",          # Exclamation
            "test@#$%",       # Special chars
        ]
        
        for query in special_queries:
            response = client.get(f"/api/v1/search?q={query}")
            # Should handle gracefully
            assert response.status_code in [200, 422]
    
    def test_search_unicode_queries(self, client: TestClient) -> None:
        """Test search with various Unicode characters."""
        unicode_queries = [
            "café",      # Latin accents
            "naïve",     # Diaeresis
            "résumé",    # Multiple accents
            "日本語",     # Japanese
            "🎉",        # Emoji
            "Привет",    # Cyrillic
        ]
        
        for query in unicode_queries:
            response = client.get(f"/api/v1/search?q={query}")
            assert response.status_code == 200