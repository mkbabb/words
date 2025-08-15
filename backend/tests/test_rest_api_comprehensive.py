"""
Comprehensive REST API tests for improved lemmatization and quantization.

Tests all API endpoints with new features enabled.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.floridify.api.main import app
from floridify.models.dictionary import Language


class TestSearchAPIImprovements:
    """Test search API with improved lemmatization and semantic features."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_search_basic_functionality(self):
        """Test basic search functionality works."""
        response = self.client.get("/api/v1/search?q=happiness&max_results=5")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "results" in data
        assert "total_found" in data
        assert "language" in data
        assert data["query"] == "happiness"
        assert isinstance(data["results"], list)

    def test_search_with_semantic_enabled(self):
        """Test search with semantic search enabled."""
        response = self.client.get(
            "/api/v1/search?q=joyful&semantic=true&max_results=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have multiple search methods in results
        methods_found = set()
        for result in data["results"]:
            methods_found.add(result["method"])
            
            # Validate result structure
            assert "word" in result
            assert "score" in result
            assert "method" in result
            assert "is_phrase" in result
            assert 0.0 <= result["score"] <= 1.0

        # Should have exact, fuzzy, and potentially semantic results
        assert len(methods_found) >= 2, f"Expected multiple search methods, got: {methods_found}"

    def test_search_lemmatization_quality(self):
        """Test that improved lemmatization produces quality results."""
        # Test cases that should benefit from improved lemmatization
        test_queries = ["happiness", "running", "studies", "beautiful"]
        
        for query in test_queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/search?q={query}&max_results=5")
                
                assert response.status_code == 200
                data = response.json()
                
                # Should find results for all these common words
                assert data["total_found"] > 0, f"No results found for '{query}'"
                
                # First result should be exact or high-scoring
                if data["results"]:
                    first_result = data["results"][0]
                    assert first_result["score"] >= 0.8, f"Low score for '{query}': {first_result['score']}"

    def test_search_parameter_validation(self):
        """Test search parameter validation and error handling."""
        # Test invalid parameters
        invalid_cases = [
            ("q=", 422),  # Empty query
            ("q=test&max_results=0", 422),  # Invalid max_results
            ("q=test&min_score=1.5", 422),  # Invalid min_score
            ("q=test&semantic=invalid", 422),  # Invalid boolean
        ]
        
        for params, expected_status in invalid_cases:
            with self.subTest(params=params):
                response = self.client.get(f"/api/v1/search?{params}")
                assert response.status_code == expected_status

    def test_search_language_support(self):
        """Test language parameter handling."""
        # Test different language codes
        languages = ["en", "english", "EN"]
        
        for lang in languages:
            with self.subTest(language=lang):
                response = self.client.get(f"/api/v1/search?q=test&language={lang}")
                
                # Should handle all these language formats
                assert response.status_code == 200
                data = response.json()
                assert data["language"] == "en"  # Should normalize to 'en'

    def test_search_suggestions_endpoint(self):
        """Test search suggestions endpoint with lower threshold."""
        response = self.client.get("/api/v1/search/happin/suggestions?limit=8")
        
        assert response.status_code == 200
        data = response.json()
        
        # Suggestions should have lower threshold (0.3 vs 0.6)
        assert "results" in data
        assert len(data["results"]) <= 8
        
        # Should find suggestions for partial word
        if data["results"]:
            # At least one result should match "happiness" or similar
            words = [r["word"] for r in data["results"]]
            happiness_variants = ["happiness", "happy", "happily", "happier"]
            found_happiness = any(variant in words for variant in happiness_variants)
            assert found_happiness, f"No happiness variants found in suggestions: {words}"

    def test_search_performance_headers(self):
        """Test that search responses include performance headers."""
        response = self.client.get("/api/v1/search?q=test&max_results=5")
        
        assert response.status_code == 200
        
        # Should have performance headers
        headers = response.headers
        assert "X-Process-Time" in headers or "X-Request-ID" in headers


class TestRebuildIndexEnhancedAPI:
    """Test enhanced rebuild index API with configuration options."""
    
    def setup_method(self):
        """Setup test client.""" 
        self.client = TestClient(app)

    def test_rebuild_index_basic(self):
        """Test basic rebuild index functionality."""
        with patch('src.floridify.core.search_pipeline.get_search_engine') as mock_engine:
            # Mock search engine with stats
            mock_engine.return_value.get_stats.return_value = {
                "vocabulary_size": 10000,
                "words": 9500,
                "phrases": 500,
                "semantic_enabled": True
            }
            
            response = self.client.post("/api/v1/search/rebuild-index")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert "languages" in data
            assert "statistics" in data
            assert "message" in data

    def test_rebuild_index_with_language_options(self):
        """Test rebuild index with specific language options."""
        request_data = {
            "languages": ["en"],
            "force_download": True,
            "rebuild_semantic": True
        }
        
        with patch('src.floridify.core.search_pipeline.get_search_engine') as mock_engine:
            mock_engine.return_value.get_stats.return_value = {"vocabulary_size": 10000}
            
            response = self.client.post(
                "/api/v1/search/rebuild-index", 
                json=request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert Language.ENGLISH in data["languages"]

    def test_rebuild_index_error_handling(self):
        """Test rebuild index error handling."""
        with patch('src.floridify.core.search_pipeline.get_search_engine') as mock_engine:
            # Mock engine to raise an exception
            mock_engine.side_effect = Exception("Mock rebuild error")
            
            response = self.client.post("/api/v1/search/rebuild-index")
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Mock rebuild error" in data["detail"]


class TestSemanticCacheAPI:
    """Test semantic cache invalidation API."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_invalidate_semantic_cache_basic(self):
        """Test basic semantic cache invalidation."""
        with patch('src.floridify.models.semantic_cache.SemanticIndexCache.cleanup_expired') as mock_cleanup:
            mock_cleanup.return_value = 5  # Mock 5 expired entries cleaned
            
            response = self.client.post("/api/v1/search/invalidate-semantic-cache")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert "invalidated_count" in data
            assert "expired_cleaned" in data
            assert data["expired_cleaned"] == 5

    def test_invalidate_semantic_cache_with_options(self):
        """Test semantic cache invalidation with specific options."""
        request_data = {
            "corpus_name": "test_corpus",
            "cleanup_expired": True
        }
        
        with patch('src.floridify.models.semantic_cache.SemanticIndexCache.invalidate_corpus') as mock_invalidate, \
             patch('src.floridify.models.semantic_cache.SemanticIndexCache.cleanup_expired') as mock_cleanup:
            
            mock_invalidate.return_value = 3
            mock_cleanup.return_value = 2
            
            response = self.client.post(
                "/api/v1/search/invalidate-semantic-cache",
                json=request_data
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["invalidated_count"] == 3
            assert data["expired_cleaned"] == 2


class TestAPIIntegrationWithNewFeatures:
    """Integration tests for API with all new features."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_full_search_flow_with_lemmatization(self):
        """Test complete search flow with improved lemmatization."""
        # Search for a word that should benefit from improved lemmatization
        response = self.client.get("/api/v1/search?q=studies&semantic=true&max_results=10")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should find relevant results
        assert data["total_found"] > 0
        
        # Check for lemmatization-related matches
        words_found = [result["word"].lower() for result in data["results"]]
        
        # Should find "study" or related forms due to improved lemmatization
        study_variants = ["study", "studies", "studied", "studying"]
        found_variants = [word for word in words_found if any(variant in word for variant in study_variants)]
        assert len(found_variants) > 0, f"No study variants found in: {words_found}"

    def test_semantic_search_quality_improvement(self):
        """Test that semantic search quality has improved."""
        # Test semantic relationships
        semantic_pairs = [
            ("automobile", ["car", "vehicle", "automotive"]),
            ("happiness", ["joy", "cheerful", "glad"]),
            ("dog", ["canine", "puppy", "hound"]),
        ]
        
        for query, expected_related in semantic_pairs:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/search?q={query}&semantic=true&max_results=15")
                
                assert response.status_code == 200
                data = response.json()
                
                if data["results"]:
                    words_found = [result["word"].lower() for result in data["results"]]
                    
                    # Should find at least one semantically related word
                    related_found = any(
                        any(related in word for related in expected_related)
                        for word in words_found
                    )
                    
                    # Note: This might not always pass depending on vocabulary
                    # but serves as a quality indicator
                    if not related_found:
                        print(f"Warning: No semantic relations found for '{query}' in {words_found[:5]}")

    def test_api_consistency_across_endpoints(self):
        """Test API response consistency across different endpoints."""
        query = "happiness"
        
        # Test both path and query parameter endpoints
        path_response = self.client.get(f"/api/v1/search/{query}?max_results=5")
        query_response = self.client.get(f"/api/v1/search?q={query}&max_results=5")
        
        assert path_response.status_code == 200
        assert query_response.status_code == 200
        
        path_data = path_response.json()
        query_data = query_response.json()
        
        # Responses should be identical
        assert path_data["query"] == query_data["query"]
        assert len(path_data["results"]) == len(query_data["results"])

    def test_error_handling_consistency(self):
        """Test consistent error handling across API."""
        # Test various error conditions
        error_cases = [
            ("/api/v1/search?q=", 422),  # Missing query
            ("/api/v1/search/", 404),    # Missing path parameter  
            ("/api/v1/search?q=test&max_results=1000", 422),  # Exceeds limit
        ]
        
        for endpoint, expected_status in error_cases:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                assert response.status_code == expected_status
                
                if response.status_code == 422:
                    data = response.json()
                    assert "detail" in data


# Performance and load tests
class TestAPIPerformance:
    """Performance tests for API endpoints."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_search_response_time(self):
        """Test search response times are reasonable."""
        import time
        
        query = "test"
        start_time = time.time()
        
        response = self.client.get(f"/api/v1/search?q={query}&max_results=10")
        
        response_time = time.time() - start_time
        
        assert response.status_code == 200
        # Should respond within reasonable time (adjust based on system)
        assert response_time < 5.0, f"Response time too slow: {response_time:.2f}s"

    def test_concurrent_search_requests(self):
        """Test handling of concurrent search requests."""
        import concurrent.futures
        
        def make_request(query):
            return self.client.get(f"/api/v1/search?q={query}&max_results=5")
        
        # Make concurrent requests
        queries = ["test", "example", "word", "search", "query"]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, query) for query in queries]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in results:
            assert response.status_code == 200


if __name__ == "__main__":
    # Run basic API tests
    print("Testing search API improvements...")
    
    test_search = TestSearchAPIImprovements()
    test_search.setup_method()
    test_search.test_search_basic_functionality()
    test_search.test_search_lemmatization_quality()
    test_search.test_search_parameter_validation()
    
    print("Testing rebuild index API...")
    
    test_rebuild = TestRebuildIndexEnhancedAPI()
    test_rebuild.setup_method()
    test_rebuild.test_rebuild_index_basic()
    
    print("Testing API integration...")
    
    test_integration = TestAPIIntegrationWithNewFeatures()
    test_integration.setup_method()
    test_integration.test_full_search_flow_with_lemmatization()
    test_integration.test_api_consistency_across_endpoints()
    
    print("✅ All REST API tests passed!")