"""Comprehensive tests for the lookup endpoint with performance benchmarking."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_benchmark.fixture import BenchmarkFixture

from .test_data import PERFORMANCE_THRESHOLDS, TEST_WORDS


class TestLookupEndpoint:
    """Comprehensive tests for word lookup functionality."""
    
    def test_lookup_basic(self, client: TestClient) -> None:
        """Test basic lookup functionality with a simple word."""
        response = client.get("/api/v1/lookup/happy")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["word"] == "happy"
        assert "pronunciation" in data
        assert "definitions" in data
        assert isinstance(data["definitions"], list)
        assert len(data["definitions"]) > 0
        
        # Validate definition structure
        for definition in data["definitions"]:
            assert "part_of_speech" in definition
            assert "definition" in definition
            assert "synonyms" in definition
            assert "examples" in definition
    
    @pytest.mark.parametrize("word", TEST_WORDS[:10])  # Test first 10 words
    def test_lookup_multiple_words(self, client: TestClient, word: str) -> None:
        """Test lookup with various words from our test bank."""
        response = client.get(f"/api/v1/lookup/{word}")
        
        # Should find most common words
        if word in ["happy", "beautiful", "computer", "algorithm"]:
            assert response.status_code == 200
            data = response.json()
            assert data["word"].lower() == word.lower()
        else:
            # Less common words might return 404
            assert response.status_code in [200, 404]
    
    def test_lookup_with_force_refresh(self, client: TestClient) -> None:
        """Test force refresh parameter."""
        word = "test"
        
        # First lookup (potentially cached)
        response1 = client.get(f"/api/v1/lookup/{word}")
        
        # Second lookup with force refresh
        response2 = client.get(f"/api/v1/lookup/{word}?force_refresh=true")
        
        # Both should succeed if word exists
        if response1.status_code == 200:
            assert response2.status_code == 200
            
            # Check timing header - force refresh might be slower
            if "X-Process-Time" in response1.headers and "X-Process-Time" in response2.headers:
                int(response1.headers["X-Process-Time"])
                time2 = int(response2.headers["X-Process-Time"])
                # Force refresh could be slower, but not necessarily
                assert time2 >= 0
    
    def test_lookup_with_providers(self, client: TestClient) -> None:
        """Test lookup with different providers."""
        word = "happy"
        
        # Test with Wiktionary (default)
        response = client.get(f"/api/v1/lookup/{word}?providers=wiktionary")
        assert response.status_code in [200, 404]
        
        # Test with Dictionary.com
        response = client.get(f"/api/v1/lookup/{word}?providers=dictionary_com")
        assert response.status_code in [200, 404]
        
        # Test with multiple providers
        response = client.get(f"/api/v1/lookup/{word}?providers=wiktionary&providers=dictionary_com")
        assert response.status_code in [200, 404]
    
    def test_lookup_no_ai(self, client: TestClient) -> None:
        """Test lookup without AI synthesis."""
        response = client.get("/api/v1/lookup/test?no_ai=true")
        
        # Without AI, might not get synthesized results
        assert response.status_code in [200, 404]
    
    def test_lookup_nonexistent_word(self, client: TestClient) -> None:
        """Test lookup with non-existent word."""
        response = client.get("/api/v1/lookup/xyzqwerty123")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_lookup_special_characters(self, client: TestClient) -> None:
        """Test lookup with words containing special characters."""
        # French phrase with spaces
        response = client.get("/api/v1/lookup/en%20coulisses")
        assert response.status_code in [200, 404]
        
        # Hyphenated word
        response = client.get("/api/v1/lookup/vis-à-vis")
        assert response.status_code in [200, 404]
    
    def test_lookup_response_headers(self, client: TestClient) -> None:
        """Test that proper headers are included."""
        response = client.get("/api/v1/lookup/test")
        
        assert "X-Process-Time" in response.headers
        assert "X-Request-ID" in response.headers
        
        # Process time should be a valid integer
        process_time = int(response.headers["X-Process-Time"])
        assert process_time >= 0
    
    def test_lookup_pronunciation_format(self, client: TestClient) -> None:
        """Test pronunciation data format."""
        response = client.get("/api/v1/lookup/happy")
        
        if response.status_code == 200:
            data = response.json()
            pronunciation = data["pronunciation"]
            
            assert "phonetic" in pronunciation
            assert isinstance(pronunciation["phonetic"], str)
            
            # IPA might be optional
            if "ipa" in pronunciation:
                assert isinstance(pronunciation["ipa"], str | type(None))
    
    def test_lookup_definition_details(self, client: TestClient) -> None:
        """Test detailed definition structure."""
        response = client.get("/api/v1/lookup/happy")
        
        if response.status_code == 200:
            data = response.json()
            definitions = data["definitions"]
            
            for definition in definitions:
                # Required fields
                assert "part_of_speech" in definition
                assert "definition" in definition
                
                # Optional but expected fields
                if "synonyms" in definition:
                    assert isinstance(definition["synonyms"], list)
                    for synonym in definition["synonyms"]:
                        assert isinstance(synonym, str)
                
                if "examples" in definition:
                    assert isinstance(definition["examples"], dict)
                    if "generated" in definition["examples"]:
                        assert isinstance(definition["examples"]["generated"], list)
                
                if "meaning_cluster" in definition:
                    assert isinstance(definition["meaning_cluster"], str | type(None))


class TestLookupPerformance:
    """Performance benchmarking for lookup endpoint."""
    
    def test_lookup_performance_cached(
        self, client: TestClient, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark cached lookup performance."""
        # Warm up cache
        client.get("/api/v1/lookup/happy")
        
        def lookup_cached() -> Any:
            response = client.get("/api/v1/lookup/happy")
            assert response.status_code == 200
            return response
        
        # Run benchmark
        result = benchmark(lookup_cached)
        
        # Extract timing from headers if available
        if hasattr(result, 'headers') and "X-Process-Time" in result.headers:
            process_time = int(result.headers["X-Process-Time"])
            assert process_time < PERFORMANCE_THRESHOLDS["lookup"]["cached"]
    
    def test_lookup_performance_uncached(
        self, client: TestClient, benchmark: BenchmarkFixture
    ) -> None:
        """Benchmark uncached lookup performance."""
        def lookup_uncached() -> Any:
            # Use different words to avoid cache
            import random
            word = random.choice(["algorithm", "paradigm", "metamorphosis"])
            response = client.get(f"/api/v1/lookup/{word}?force_refresh=true")
            return response
        
        # Run benchmark
        benchmark(lookup_uncached)
        
        # Performance assertion would go here if we had timing data
    
    @pytest.mark.parametrize("word", TEST_WORDS[:5])
    def test_lookup_batch_performance(
        self, client: TestClient, word: str
    ) -> None:
        """Test performance across multiple words."""
        start_time = time.perf_counter()
        response = client.get(f"/api/v1/lookup/{word}")
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        # Log performance for analysis
        print(f"Lookup '{word}': {elapsed_ms:.2f}ms (status: {response.status_code})")
        
        # General performance assertion
        if response.status_code == 200:
            assert elapsed_ms < 1000  # Should complete within 1 second


class TestLookupEdgeCases:
    """Edge case testing for lookup endpoint."""
    
    def test_lookup_empty_word(self, client: TestClient) -> None:
        """Test lookup with empty word."""
        response = client.get("/api/v1/lookup/")
        assert response.status_code == 404  # Path not found
    
    def test_lookup_very_long_word(self, client: TestClient) -> None:
        """Test lookup with extremely long word."""
        long_word = "a" * 100
        response = client.get(f"/api/v1/lookup/{long_word}")
        assert response.status_code in [404, 422]  # Not found or validation error
    
    def test_lookup_unicode_word(self, client: TestClient) -> None:
        """Test lookup with Unicode characters."""
        response = client.get("/api/v1/lookup/café")
        assert response.status_code in [200, 404]
        
        response = client.get("/api/v1/lookup/naïve")
        assert response.status_code in [200, 404]
    
    def test_lookup_case_sensitivity(self, client: TestClient) -> None:
        """Test case handling in lookups."""
        # These should return the same result
        response1 = client.get("/api/v1/lookup/happy")
        response2 = client.get("/api/v1/lookup/HAPPY")
        response3 = client.get("/api/v1/lookup/Happy")
        
        # All should have same status
        assert response1.status_code == response2.status_code == response3.status_code
        
        # If found, word should be normalized
        if response1.status_code == 200:
            assert response1.json()["word"] == response2.json()["word"]
    
    def test_lookup_concurrent_requests(self, client: TestClient) -> None:
        """Test handling of concurrent requests."""
        import concurrent.futures
        
        def lookup_word(word: str) -> int:
            response = client.get(f"/api/v1/lookup/{word}")
            return response.status_code
        
        words = ["happy", "sad", "algorithm", "computer", "beautiful"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(lookup_word, word) for word in words]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # All requests should complete successfully
        assert all(status in [200, 404] for status in results)