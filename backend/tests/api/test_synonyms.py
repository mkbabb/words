"""Comprehensive tests for synonyms endpoint with performance benchmarking."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_benchmark.fixture import BenchmarkFixture

from .test_data import PERFORMANCE_THRESHOLDS, TEST_WORDS


class TestSynonymsEndpoint:
    """Comprehensive tests for the synonyms endpoint."""
    
    def test_synonyms_basic(self, client: TestClient) -> None:
        """Test basic synonyms functionality."""
        response = client.get("/api/v1/synonyms/happy")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "word" in data
        assert "synonyms" in data
        assert "total_synonyms" in data
        assert "semantic_time_ms" in data
        
        assert data["word"] == "happy"
        assert isinstance(data["synonyms"], list)
        assert isinstance(data["total_synonyms"], int)
        assert isinstance(data["semantic_time_ms"], int | float)
        
        # Check synonym structure if any exist
        for synonym in data["synonyms"]:
            assert "word" in synonym
            assert "score" in synonym
            assert isinstance(synonym["word"], str)
            assert isinstance(synonym["score"], int | float)
            assert 0.0 <= synonym["score"] <= 1.0
    
    def test_synonyms_with_max_results(self, client: TestClient) -> None:
        """Test synonyms with max_results parameter."""
        response = client.get("/api/v1/synonyms/happy?max_results=3")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["synonyms"]) <= 3
    
    def test_synonyms_invalid_max_results(self, client: TestClient) -> None:
        """Test synonyms with invalid max_results."""
        response = client.get("/api/v1/synonyms/happy?max_results=25")
        
        assert response.status_code == 422  # Validation error
    
    def test_synonyms_excludes_original_word(self, client: TestClient) -> None:
        """Test that synonyms don't include the original word."""
        word = "happy"
        response = client.get(f"/api/v1/synonyms/{word}")
        
        assert response.status_code == 200
        
        data = response.json()
        synonym_words = [syn["word"].lower() for syn in data["synonyms"]]
        assert word.lower() not in synonym_words
    
    @pytest.mark.parametrize("word", ["happy", "sad", "big", "small", "beautiful", "intelligent"])
    def test_synonyms_multiple_words(self, client: TestClient, word: str) -> None:
        """Test synonyms with multiple different words."""
        response = client.get(f"/api/v1/synonyms/{word}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["word"] == word
        assert isinstance(data["synonyms"], list)
    
    def test_synonyms_response_headers(self, client: TestClient) -> None:
        """Test synonyms endpoint includes proper response headers."""
        response = client.get("/api/v1/synonyms/test")
        
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        assert "X-Request-ID" in response.headers
    
    def test_synonyms_min_score_filtering(self, client: TestClient) -> None:
        """Test minimum score filtering for synonyms."""
        response = client.get("/api/v1/synonyms/happy?min_score=0.8")
        
        assert response.status_code == 200
        
        data = response.json()
        # All synonyms should meet minimum score threshold
        for synonym in data["synonyms"]:
            assert synonym["score"] >= 0.8
    
    def test_synonyms_score_ordering(self, client: TestClient) -> None:
        """Test that synonyms are ordered by score (highest first)."""
        response = client.get("/api/v1/synonyms/happy?max_results=10")
        
        if response.status_code == 200:
            data = response.json()
            scores = [syn["score"] for syn in data["synonyms"]]
            
            # Should be in descending order
            assert scores == sorted(scores, reverse=True)
    
    def test_synonyms_nonexistent_word(self, client: TestClient) -> None:
        """Test synonyms for non-existent word."""
        response = client.get("/api/v1/synonyms/xyzqwerty123")
        
        # Should return empty results rather than error
        assert response.status_code == 200
        data = response.json()
        assert data["synonyms"] == []
        assert data["total_synonyms"] == 0
    
    def test_synonyms_case_handling(self, client: TestClient) -> None:
        """Test case handling in synonyms endpoint."""
        # Test different cases
        response1 = client.get("/api/v1/synonyms/happy")
        response2 = client.get("/api/v1/synonyms/HAPPY")
        response3 = client.get("/api/v1/synonyms/Happy")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        # All should return synonyms for the same normalized word
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()
        
        # Word should be normalized to lowercase
        assert data1["word"] == "happy"
        assert data2["word"] == "happy"
        assert data3["word"] == "happy"
    
    @pytest.mark.parametrize("word", TEST_WORDS[:10])
    def test_synonyms_test_bank(self, client: TestClient, word: str) -> None:
        """Test synonyms with words from our test bank."""
        response = client.get(f"/api/v1/synonyms/{word}")
        
        # Should handle all test words gracefully
        assert response.status_code == 200
        
        data = response.json()
        assert data["word"] == word
        assert isinstance(data["synonyms"], list)
        assert isinstance(data["total_synonyms"], int)
        assert data["total_synonyms"] >= 0
        assert data["semantic_time_ms"] >= 0
    
    def test_synonyms_complex_words(self, client: TestClient) -> None:
        """Test synonyms with complex/rare words."""
        complex_words = ["serendipity", "ephemeral", "ubiquitous", "perspicacious"]
        
        for word in complex_words:
            response = client.get(f"/api/v1/synonyms/{word}")
            
            assert response.status_code == 200
            
            data = response.json()
            assert data["word"] == word
            # Complex words might have fewer synonyms
            assert isinstance(data["synonyms"], list)
    
    def test_synonyms_special_characters(self, client: TestClient) -> None:
        """Test synonyms with special characters."""
        # Test hyphenated words
        response = client.get("/api/v1/synonyms/vis-à-vis")
        assert response.status_code == 200
        
        # Test accented characters
        response = client.get("/api/v1/synonyms/café")
        assert response.status_code == 200
        
        # Test phrases (URL encoded)
        response = client.get("/api/v1/synonyms/bon%20vivant")
        assert response.status_code == 200


class TestSynonymsPerformance:
    """Performance benchmarking for synonyms endpoint."""
    
    def test_synonyms_performance_cached(
        self, client: TestClient, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark cached synonyms performance."""
        # Warm up cache
        client.get("/api/v1/synonyms/happy")
        
        def get_synonyms_cached() -> Any:
            response = client.get("/api/v1/synonyms/happy")
            assert response.status_code == 200
            return response
        
        # Run benchmark
        result = benchmark(get_synonyms_cached)
        
        # Extract timing from response if available
        if hasattr(result, 'json'):
            data = result.json()
            if "semantic_time_ms" in data:
                semantic_time = data["semantic_time_ms"]
                assert semantic_time < PERFORMANCE_THRESHOLDS["synonyms"]["cached"]
    
    def test_synonyms_performance_uncached(
        self, client: TestClient, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark uncached synonyms performance."""
        def get_synonyms_uncached() -> Any:
            # Use different words to avoid cache hits
            import random
            word = random.choice(["algorithm", "paradigm", "metamorphosis", "serendipity"])
            response = client.get(f"/api/v1/synonyms/{word}")
            return response
        
        # Run benchmark
        benchmark(get_synonyms_uncached)
        
        # Performance assertion would be based on actual response timing
    
    @pytest.mark.parametrize("word", TEST_WORDS[:5])
    def test_synonyms_batch_performance(
        self, client: TestClient, word: str
    ) -> None:
        """Test synonyms performance across multiple words."""
        start_time = time.perf_counter()
        response = client.get(f"/api/v1/synonyms/{word}")
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        assert response.status_code == 200
        
        # Log performance for analysis
        data = response.json()
        print(f"Synonyms '{word}': {elapsed_ms:.2f}ms, "
              f"{data['total_synonyms']} synonyms, "
              f"semantic time: {data['semantic_time_ms']}ms")
        
        # General performance bound
        assert elapsed_ms < 1000  # Should complete within 1 second
    
    def test_synonyms_performance_by_word_length(
        self, client: TestClient
    ) -> None:
        """Compare performance by word length."""
        test_cases = [
            ("short", "cat"),
            ("medium", "beautiful"),
            ("long", "serendipity"),
            ("very_long", "sesquipedalian"),
        ]
        
        timings = {}
        for category, word in test_cases:
            start_time = time.perf_counter()
            response = client.get(f"/api/v1/synonyms/{word}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            assert response.status_code == 200
            timings[category] = elapsed_ms
            
            data = response.json()
            print(f"Synonyms '{word}' ({category}): {elapsed_ms:.2f}ms, "
                  f"{data['total_synonyms']} synonyms")
        
        # Longer words might take slightly longer but should still be reasonable
        for category, timing in timings.items():
            assert timing < 500  # All should complete within 500ms


class TestSynonymsEdgeCases:
    """Edge case testing for synonyms endpoint."""
    
    def test_synonyms_validation_errors(self, client: TestClient) -> None:
        """Test various validation error scenarios."""
        # Invalid min_score
        response = client.get("/api/v1/synonyms/happy?min_score=2.0")
        assert response.status_code == 422
        
        # Invalid max_results
        response = client.get("/api/v1/synonyms/happy?max_results=1000")
        assert response.status_code == 422
        
        # Negative min_score
        response = client.get("/api/v1/synonyms/happy?min_score=-0.5")
        assert response.status_code == 422
    
    def test_synonyms_empty_word(self, client: TestClient) -> None:
        """Test synonyms with empty word."""
        response = client.get("/api/v1/synonyms/")
        assert response.status_code == 404  # Path not found
    
    def test_synonyms_very_long_word(self, client: TestClient) -> None:
        """Test synonyms with extremely long word."""
        long_word = "a" * 100
        response = client.get(f"/api/v1/synonyms/{long_word}")
        assert response.status_code in [200, 422]  # Should handle gracefully
    
    def test_synonyms_unicode_word(self, client: TestClient) -> None:
        """Test synonyms with Unicode characters."""
        response = client.get("/api/v1/synonyms/café")
        assert response.status_code == 200
        
        response = client.get("/api/v1/synonyms/naïve")
        assert response.status_code == 200
    
    def test_synonyms_concurrent_requests(self, client: TestClient) -> None:
        """Test handling of concurrent synonym requests."""
        import concurrent.futures
        
        def get_synonyms(word: str) -> int:
            response = client.get(f"/api/v1/synonyms/{word}")
            return response.status_code
        
        words = ["happy", "sad", "beautiful", "intelligent", "algorithm"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_synonyms, word) for word in words]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should complete successfully
        assert all(status == 200 for status in results)
    
    def test_synonyms_special_query_patterns(self, client: TestClient) -> None:
        """Test synonyms with special query patterns."""
        special_words = [
            "test@#$%",    # Special characters
            "test*",       # Wildcard-like
            "test?",       # Question mark
            "test!",       # Exclamation
            "test123",     # Alphanumeric
        ]
        
        for word in special_words:
            response = client.get(f"/api/v1/synonyms/{word}")
            # Should handle gracefully
            assert response.status_code in [200, 422]
    
    def test_synonyms_max_results_boundary(self, client: TestClient) -> None:
        """Test max_results at boundary values."""
        # Test minimum valid value
        response = client.get("/api/v1/synonyms/happy?max_results=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["synonyms"]) <= 1
        
        # Test maximum valid value
        response = client.get("/api/v1/synonyms/happy?max_results=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["synonyms"]) <= 20
    
    def test_synonyms_min_score_boundary(self, client: TestClient) -> None:
        """Test min_score at boundary values."""
        # Test minimum valid value
        response = client.get("/api/v1/synonyms/happy?min_score=0.0")
        assert response.status_code == 200
        
        # Test maximum valid value
        response = client.get("/api/v1/synonyms/happy?min_score=1.0")
        assert response.status_code == 200
        
        # Very high score might return no results
        data = response.json()
        for synonym in data["synonyms"]:
            assert synonym["score"] >= 1.0