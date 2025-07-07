"""Tests for search endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestSearchEndpoint:
    """Tests for the search endpoint."""
    
    def test_search_basic(self, client: TestClient, sample_search_query: str) -> None:
        """Test basic search functionality."""
        response = client.get(f"/api/v1/search?q={sample_search_query}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        
        assert data["query"] == sample_search_query
        assert isinstance(data["results"], list)
        assert isinstance(data["total_results"], int)
        assert isinstance(data["search_time_ms"], int)
        assert data["total_results"] >= 0
        assert data["search_time_ms"] >= 0
    
    def test_search_with_parameters(self, client: TestClient) -> None:
        """Test search with various parameters."""
        response = client.get(
            "/api/v1/search?q=test&method=exact&max_results=5&min_score=0.8"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) <= 5
        assert data["query"] == "test"
    
    def test_search_invalid_method(self, client: TestClient) -> None:
        """Test search with invalid method parameter."""
        response = client.get("/api/v1/search?q=test&method=invalid")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_empty_query(self, client: TestClient) -> None:
        """Test search with empty query."""
        response = client.get("/api/v1/search?q=")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_long_query(self, client: TestClient) -> None:
        """Test search with overly long query."""
        long_query = "a" * 101  # Exceeds 100 character limit
        response = client.get(f"/api/v1/search?q={long_query}")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_result_structure(self, client: TestClient) -> None:
        """Test structure of search results."""
        response = client.get("/api/v1/search?q=test&max_results=1")
        
        assert response.status_code == 200
        
        data = response.json()
        if data["results"]:
            result = data["results"][0]
            assert "word" in result
            assert "score" in result
            assert "method" in result
            assert "is_phrase" in result
            
            assert isinstance(result["word"], str)
            assert isinstance(result["score"], (int, float))
            assert isinstance(result["method"], str)
            assert isinstance(result["is_phrase"], bool)
            assert 0.0 <= result["score"] <= 1.0


class TestSuggestionsEndpoint:
    """Tests for the suggestions endpoint."""
    
    def test_suggestions_basic(self, client: TestClient) -> None:
        """Test basic suggestions functionality."""
        response = client.get("/api/v1/suggestions?q=te")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "query" in data
        assert "suggestions" in data
        
        assert data["query"] == "te"
        assert isinstance(data["suggestions"], list)
        
        # All suggestions should be strings
        for suggestion in data["suggestions"]:
            assert isinstance(suggestion, str)
    
    def test_suggestions_with_limit(self, client: TestClient) -> None:
        """Test suggestions with limit parameter."""
        response = client.get("/api/v1/suggestions?q=te&limit=3")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["suggestions"]) <= 3
    
    def test_suggestions_short_query(self, client: TestClient) -> None:
        """Test suggestions with too short query."""
        response = client.get("/api/v1/suggestions?q=a")
        
        assert response.status_code == 422  # Validation error
    
    def test_suggestions_long_query(self, client: TestClient) -> None:
        """Test suggestions with overly long query."""
        long_query = "a" * 51  # Exceeds 50 character limit
        response = client.get(f"/api/v1/suggestions?q={long_query}")
        
        assert response.status_code == 422  # Validation error
    
    def test_suggestions_invalid_limit(self, client: TestClient) -> None:
        """Test suggestions with invalid limit."""
        response = client.get("/api/v1/suggestions?q=te&limit=25")
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.parametrize("query", ["te", "ser", "cog"])
    def test_suggestions_multiple_queries(self, client: TestClient, query: str) -> None:
        """Test suggestions with multiple different queries."""
        response = client.get(f"/api/v1/suggestions?q={query}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == query
        assert isinstance(data["suggestions"], list)