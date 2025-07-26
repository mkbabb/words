"""Comprehensive tests for Words CRUD endpoints."""

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from .test_data import TEST_WORDS


class TestWordsEndpoints:
    """Test word CRUD operations."""

    @pytest.fixture
    def test_word_data(self) -> dict:
        """Sample word data for creation."""
        return {
            "text": "serendipity",
            "normalized": "serendipity",
            "language": "en",
            "offensive_flag": False,
            "first_known_use": "1754",
        }

    def test_list_words_no_params(self, client: TestClient) -> None:
        """Test listing words without filters."""
        response = client.get("/api/v1/words")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert data["offset"] == 0
        assert data["limit"] == 20

    def test_list_words_with_pagination(self, client: TestClient) -> None:
        """Test pagination parameters."""
        response = client.get("/api/v1/words?offset=10&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["offset"] == 10
        assert data["limit"] == 5
        assert len(data["items"]) <= 5

    def test_list_words_with_filters(self, client: TestClient) -> None:
        """Test filtering words."""
        # Filter by language
        response = client.get("/api/v1/words?language=en")
        assert response.status_code == 200
        
        # Filter by text pattern
        response = client.get("/api/v1/words?text_pattern=test")
        assert response.status_code == 200
        
        # Filter by offensive flag
        response = client.get("/api/v1/words?offensive_flag=false")
        assert response.status_code == 200

    def test_list_words_with_sorting(self, client: TestClient) -> None:
        """Test sorting parameters."""
        response = client.get("/api/v1/words?sort_by=text&sort_order=desc")
        assert response.status_code == 200
        
        data = response.json()
        items = data["items"]
        if len(items) > 1:
            # Verify descending order
            for i in range(len(items) - 1):
                assert items[i]["text"] >= items[i + 1]["text"]

    def test_create_word_success(self, client: TestClient, test_word_data: dict) -> None:
        """Test successful word creation."""
        response = client.post("/api/v1/words", json=test_word_data)
        
        if response.status_code == 409:
            # Word already exists, which is fine
            data = response.json()
            assert "error" in data
            assert "Word already exists" in data["error"]
        else:
            assert response.status_code == 201
            data = response.json()
            assert "data" in data
            assert "links" in data
            assert data["data"]["text"] == test_word_data["text"]
            assert data["data"]["language"] == test_word_data["language"]

    def test_create_word_validation_error(self, client: TestClient) -> None:
        """Test word creation with invalid data."""
        invalid_data = {
            "text": "",  # Empty text should fail
            "language": "invalid_lang",
        }
        response = client.post("/api/v1/words", json=invalid_data)
        assert response.status_code == 422

    def test_create_word_duplicate(self, client: TestClient) -> None:
        """Test creating duplicate word."""
        word_data = {
            "text": "test_duplicate_word",
            "normalized": "test_duplicate_word",
            "language": "en",
        }
        
        # Create first word
        response1 = client.post("/api/v1/words", json=word_data)
        if response1.status_code == 201:
            # Try to create duplicate
            response2 = client.post("/api/v1/words", json=word_data)
            assert response2.status_code == 409
            data = response2.json()
            assert "Word already exists" in data["error"]

    def test_get_word_by_id(self, client: TestClient) -> None:
        """Test getting word by ID."""
        # First, get a word from the list
        list_response = client.get("/api/v1/words?limit=1")
        assert list_response.status_code == 200
        
        items = list_response.json()["items"]
        if items:
            word_id = items[0]["_id"]
            
            # Get specific word
            response = client.get(f"/api/v1/words/{word_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert "data" in data
            assert "metadata" in data
            assert "links" in data
            assert data["data"]["_id"] == word_id

    def test_get_word_not_found(self, client: TestClient) -> None:
        """Test getting non-existent word."""
        fake_id = str(PydanticObjectId())
        response = client.get(f"/api/v1/words/{fake_id}")
        assert response.status_code == 404

    def test_get_word_with_etag(self, client: TestClient) -> None:
        """Test ETag support for caching."""
        # Get a word
        list_response = client.get("/api/v1/words?limit=1")
        items = list_response.json()["items"]
        
        if items:
            word_id = items[0]["_id"]
            
            # First request
            response1 = client.get(f"/api/v1/words/{word_id}")
            assert response1.status_code == 200
            assert "ETag" in response1.headers
            
            etag = response1.headers["ETag"]
            
            # Second request with If-None-Match
            response2 = client.get(
                f"/api/v1/words/{word_id}",
                headers={"If-None-Match": etag}
            )
            assert response2.status_code == 304  # Not Modified

    def test_get_word_with_field_selection(self, client: TestClient) -> None:
        """Test field selection parameters."""
        list_response = client.get("/api/v1/words?limit=1")
        items = list_response.json()["items"]
        
        if items:
            word_id = items[0]["_id"]
            
            # Include specific fields
            response = client.get(f"/api/v1/words/{word_id}?include=text,language")
            assert response.status_code == 200
            
            # Exclude fields
            response = client.get(f"/api/v1/words/{word_id}?exclude=created_at,updated_at")
            assert response.status_code == 200

    def test_update_word(self, client: TestClient) -> None:
        """Test updating a word."""
        # Get a word to update
        list_response = client.get("/api/v1/words?limit=1")
        items = list_response.json()["items"]
        
        if items:
            word_id = items[0]["_id"]
            original_version = items[0].get("version", 1)
            
            # Update the word
            update_data = {
                "offensive_flag": True,
                "first_known_use": "1800",
            }
            
            response = client.put(
                f"/api/v1/words/{word_id}",
                json=update_data,
                params={"version": original_version}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["data"]["offensive_flag"] == True
                assert data["data"]["first_known_use"] == "1800"
                assert data["metadata"]["version"] > original_version

    def test_update_word_version_conflict(self, client: TestClient) -> None:
        """Test optimistic locking with version conflict."""
        list_response = client.get("/api/v1/words?limit=1")
        items = list_response.json()["items"]
        
        if items:
            word_id = items[0]["_id"]
            
            # Try to update with wrong version
            update_data = {"offensive_flag": True}
            response = client.put(
                f"/api/v1/words/{word_id}",
                json=update_data,
                params={"version": 999999}  # Wrong version
            )
            
            # Should fail with conflict
            assert response.status_code in [409, 400]

    def test_delete_word(self, client: TestClient) -> None:
        """Test deleting a word."""
        # Create a word to delete
        word_data = {
            "text": "test_delete_word",
            "normalized": "test_delete_word",
            "language": "en",
        }
        
        create_response = client.post("/api/v1/words", json=word_data)
        
        if create_response.status_code == 201:
            word_id = create_response.json()["data"]["_id"]
            
            # Delete the word
            response = client.delete(f"/api/v1/words/{word_id}")
            assert response.status_code == 204
            
            # Verify it's deleted
            get_response = client.get(f"/api/v1/words/{word_id}")
            assert get_response.status_code == 404

    def test_delete_word_with_cascade(self, client: TestClient) -> None:
        """Test cascading delete."""
        # Create a word to delete
        word_data = {
            "text": "test_cascade_delete",
            "normalized": "test_cascade_delete",
            "language": "en",
        }
        
        create_response = client.post("/api/v1/words", json=word_data)
        
        if create_response.status_code == 201:
            word_id = create_response.json()["data"]["_id"]
            
            # Delete with cascade
            response = client.delete(f"/api/v1/words/{word_id}?cascade=true")
            assert response.status_code == 204

    def test_search_words(self, client: TestClient) -> None:
        """Test word search functionality."""
        # Search for common words
        response = client.get("/api/v1/words/search/test")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_search_words_with_language(self, client: TestClient) -> None:
        """Test search with language filter."""
        response = client.get("/api/v1/words/search/test?language=en")
        assert response.status_code == 200
        
        data = response.json()
        # All results should be in English
        for item in data["items"]:
            assert item.get("language") == "en"

    def test_search_words_with_limit(self, client: TestClient) -> None:
        """Test search with result limit."""
        response = client.get("/api/v1/words/search/test?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["limit"] == 5

    @pytest.mark.parametrize("invalid_param", [
        "?limit=0",  # Too small
        "?limit=51",  # Too large
        "?offset=-1",  # Negative offset
        "?sort_order=invalid",  # Invalid sort order
    ])
    def test_invalid_query_parameters(self, client: TestClient, invalid_param: str) -> None:
        """Test invalid query parameter validation."""
        response = client.get(f"/api/v1/words{invalid_param}")
        assert response.status_code == 422


class TestWordsPerformance:
    """Performance tests for word endpoints."""

    @pytest.mark.benchmark
    def test_list_words_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark word listing performance."""
        def list_words():
            response = client.get("/api/v1/words?limit=20")
            assert response.status_code == 200
            return response
        
        result = benchmark(list_words)
        
        # Performance assertions
        assert benchmark.stats["mean"] < 0.1  # Average under 100ms

    @pytest.mark.benchmark
    def test_search_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark search performance."""
        def search_words():
            response = client.get("/api/v1/words/search/test")
            assert response.status_code == 200
            return response
        
        result = benchmark(search_words)
        
        # Performance assertions
        assert benchmark.stats["mean"] < 0.2  # Average under 200ms


class TestWordsEdgeCases:
    """Edge case tests for word endpoints."""

    def test_unicode_word_handling(self, client: TestClient) -> None:
        """Test handling of Unicode characters."""
        unicode_words = [
            "café",
            "naïve",
            "Zürich",
            "北京",  # Beijing in Chinese
            "مرحبا",  # Hello in Arabic
            "🎯",  # Emoji
        ]
        
        for word in unicode_words:
            response = client.get(f"/api/v1/words/search/{word}")
            assert response.status_code == 200

    def test_special_characters_in_search(self, client: TestClient) -> None:
        """Test special character handling in search."""
        special_queries = [
            "test-word",
            "test_word",
            "test.word",
            "test's",
            "test&word",
            "test+word",
        ]
        
        for query in special_queries:
            response = client.get(f"/api/v1/words/search/{query}")
            assert response.status_code == 200

    def test_very_long_word(self, client: TestClient) -> None:
        """Test handling of extremely long words."""
        long_word = "a" * 100
        
        # Search
        response = client.get(f"/api/v1/words/search/{long_word}")
        assert response.status_code == 200
        
        # Create
        word_data = {
            "text": long_word,
            "normalized": long_word.lower(),
            "language": "en",
        }
        response = client.post("/api/v1/words", json=word_data)
        # Should either succeed or fail gracefully
        assert response.status_code in [201, 400, 409, 422]

    def test_empty_search_query(self, client: TestClient) -> None:
        """Test empty search query handling."""
        response = client.get("/api/v1/words/search/")
        # Should redirect or return error
        assert response.status_code in [307, 404, 422]

    def test_malformed_object_id(self, client: TestClient) -> None:
        """Test handling of malformed object IDs."""
        bad_ids = [
            "not-an-id",
            "12345",
            "xyz123",
            "",
        ]
        
        for bad_id in bad_ids:
            response = client.get(f"/api/v1/words/{bad_id}")
            assert response.status_code in [400, 422, 404]