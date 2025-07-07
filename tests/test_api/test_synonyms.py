"""Tests for synonyms endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestSynonymsEndpoint:
    """Tests for the synonyms endpoint."""
    
    def test_synonyms_basic(self, client: TestClient, sample_word: str) -> None:
        """Test basic synonyms functionality."""
        response = client.get(f"/api/v1/synonyms/{sample_word}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "word" in data
        assert "synonyms" in data
        
        assert data["word"] == sample_word
        assert isinstance(data["synonyms"], list)
        
        # Check synonym structure if any exist
        for synonym in data["synonyms"]:
            assert "word" in synonym
            assert "score" in synonym
            assert isinstance(synonym["word"], str)
            assert isinstance(synonym["score"], (int, float))
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
    
    @pytest.mark.parametrize("word", ["happy", "sad", "big", "small"])
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