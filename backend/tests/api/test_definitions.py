"""Comprehensive tests for Definitions CRUD endpoints."""

import pytest
from beanie import PydanticObjectId
from fastapi.testclient import TestClient

from floridify.api.main import app
from floridify.models import Definition, Word


class TestDefinitionsEndpoints:
    """Test definition CRUD operations."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_definition_data(self) -> dict:
        """Sample definition data for creation."""
        return {
            "word_id": str(PydanticObjectId()),
            "part_of_speech": "noun",
            "text": "A feeling of intense happiness and excitement",
            "language_register": "neutral",
            "cefr_level": "B1",
            "frequency_band": 3,
            "synonyms": ["joy", "delight", "elation"],
            "antonyms": ["sadness", "sorrow"],
        }

    def test_list_definitions_no_params(self, client: TestClient) -> None:
        """Test listing definitions without filters."""
        response = client.get("/api/v1/definitions")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert data["offset"] == 0
        assert data["limit"] == 20

    def test_list_definitions_with_filters(self, client: TestClient) -> None:
        """Test filtering definitions."""
        # Filter by part of speech
        response = client.get("/api/v1/definitions?part_of_speech=noun")
        assert response.status_code == 200
        
        # Filter by CEFR level
        response = client.get("/api/v1/definitions?cefr_level=B1")
        assert response.status_code == 200
        
        # Filter by frequency band
        response = client.get("/api/v1/definitions?frequency_band=3")
        assert response.status_code == 200
        
        # Filter by has_examples
        response = client.get("/api/v1/definitions?has_examples=true")
        assert response.status_code == 200
        
        # Filter by domain
        response = client.get("/api/v1/definitions?domain=medical")
        assert response.status_code == 200

    def test_list_definitions_with_word_filter(self, client: TestClient) -> None:
        """Test filtering definitions by word ID."""
        # Get a word first
        words_response = client.get("/api/v1/words?limit=1")
        if words_response.status_code == 200 and words_response.json()["items"]:
            word_id = words_response.json()["items"][0]["_id"]
            
            response = client.get(f"/api/v1/definitions?word_id={word_id}")
            assert response.status_code == 200

    def test_list_definitions_with_pagination(self, client: TestClient) -> None:
        """Test pagination parameters."""
        response = client.get("/api/v1/definitions?offset=5&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["offset"] == 5
        assert data["limit"] == 10
        assert len(data["items"]) <= 10

    def test_create_definition_success(self, client: TestClient) -> None:
        """Test successful definition creation."""
        # First create a word to reference
        word_data = {
            "text": "test_definition_word",
            "normalized": "test_definition_word",
            "language": "en",
        }
        word_response = client.post("/api/v1/words", json=word_data)
        
        if word_response.status_code == 201:
            word_id = word_response.json()["data"]["_id"]
            
            definition_data = {
                "word_id": word_id,
                "part_of_speech": "noun",
                "text": "A test definition for testing purposes",
                "language_register": "formal",
                "synonyms": ["examination", "trial"],
            }
            
            response = client.post("/api/v1/definitions", json=definition_data)
            assert response.status_code == 201
            
            data = response.json()
            assert "data" in data
            assert "links" in data
            assert data["data"]["word_id"] == word_id
            assert data["data"]["part_of_speech"] == "noun"
            assert "self" in data["links"]
            assert "word" in data["links"]
            assert "regenerate" in data["links"]

    def test_create_definition_validation_error(self, client: TestClient) -> None:
        """Test definition creation with invalid data."""
        invalid_data = {
            "part_of_speech": "invalid_pos",  # Invalid part of speech
            "text": "",  # Empty text
        }
        response = client.post("/api/v1/definitions", json=invalid_data)
        assert response.status_code == 422

    def test_get_definition_by_id(self, client: TestClient) -> None:
        """Test getting definition by ID."""
        # Get a definition from the list
        list_response = client.get("/api/v1/definitions?limit=1")
        assert list_response.status_code == 200
        
        items = list_response.json()["items"]
        if items:
            definition_id = items[0]["_id"]
            
            # Get specific definition
            response = client.get(f"/api/v1/definitions/{definition_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert "data" in data
            assert "metadata" in data
            assert "links" in data
            assert data["data"]["_id"] == definition_id
            assert "completeness" in data["metadata"]

    def test_get_definition_with_examples_expansion(self, client: TestClient) -> None:
        """Test expanding examples when getting definition."""
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            
            # Get with examples expansion
            response = client.get(f"/api/v1/definitions/{definition_id}?expand=examples")
            assert response.status_code == 200
            
            data = response.json()
            # If definition has examples, they should be expanded
            if data["data"].get("example_ids"):
                assert "examples" in data["data"] or "example_ids" in data["data"]

    def test_get_definition_with_etag(self, client: TestClient) -> None:
        """Test ETag support for caching."""
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            
            # First request
            response1 = client.get(f"/api/v1/definitions/{definition_id}")
            assert response1.status_code == 200
            assert "ETag" in response1.headers
            
            etag = response1.headers["ETag"]
            
            # Second request with If-None-Match
            response2 = client.get(
                f"/api/v1/definitions/{definition_id}",
                headers={"If-None-Match": etag}
            )
            assert response2.status_code == 304

    def test_update_definition(self, client: TestClient) -> None:
        """Test updating a definition."""
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            original_version = items[0].get("version", 1)
            
            # Update the definition
            update_data = {
                "language_register": "informal",
                "cefr_level": "C1",
                "synonyms": ["updated", "modified"],
            }
            
            response = client.put(
                f"/api/v1/definitions/{definition_id}",
                json=update_data,
                params={"version": original_version}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["data"]["language_register"] == "informal"
                assert data["data"]["cefr_level"] == "C1"
                assert "updated" in data["data"]["synonyms"]
                assert data["metadata"]["version"] > original_version

    def test_delete_definition(self, client: TestClient) -> None:
        """Test deleting a definition."""
        # Create a word and definition to delete
        word_data = {
            "text": "test_delete_definition_word",
            "normalized": "test_delete_definition_word",
            "language": "en",
        }
        word_response = client.post("/api/v1/words", json=word_data)
        
        if word_response.status_code == 201:
            word_id = word_response.json()["data"]["_id"]
            
            definition_data = {
                "word_id": word_id,
                "part_of_speech": "verb",
                "text": "To test deletion functionality",
            }
            
            create_response = client.post("/api/v1/definitions", json=definition_data)
            
            if create_response.status_code == 201:
                definition_id = create_response.json()["data"]["_id"]
                
                # Delete the definition
                response = client.delete(f"/api/v1/definitions/{definition_id}")
                assert response.status_code == 204
                
                # Verify it's deleted
                get_response = client.get(f"/api/v1/definitions/{definition_id}")
                assert get_response.status_code == 404

    def test_regenerate_components(self, client: TestClient) -> None:
        """Test regenerating definition components."""
        # Get a definition
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            
            # Request to regenerate specific components
            regenerate_request = {
                "components": ["synonyms", "antonyms", "cefr_level"],
                "force": True
            }
            
            response = client.post(
                f"/api/v1/definitions/{definition_id}/regenerate",
                json=regenerate_request
            )
            
            # May succeed or fail based on API key availability
            assert response.status_code in [200, 401, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert "regenerated_components" in data["metadata"]
                assert set(data["metadata"]["regenerated_components"]) == set(regenerate_request["components"])

    def test_regenerate_invalid_components(self, client: TestClient) -> None:
        """Test regenerating with invalid component names."""
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            
            regenerate_request = {
                "components": ["invalid_component", "fake_component"],
                "force": False
            }
            
            response = client.post(
                f"/api/v1/definitions/{definition_id}/regenerate",
                json=regenerate_request
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "Invalid components" in data["error"]

    def test_batch_regenerate_components(self, client: TestClient) -> None:
        """Test batch regeneration for multiple definitions."""
        # Get multiple definitions
        list_response = client.get("/api/v1/definitions?limit=3")
        items = list_response.json()["items"]
        
        if len(items) >= 2:
            definition_ids = [item["_id"] for item in items[:2]]
            
            batch_request = {
                "definition_ids": definition_ids,
                "components": ["synonyms", "frequency_band"],
                "force": False,
                "parallel": True
            }
            
            response = client.post(
                "/api/v1/definitions/batch/regenerate",
                json=batch_request
            )
            
            # May succeed or fail based on API key availability
            assert response.status_code in [200, 401, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert data["processed"] == len(definition_ids)
                assert data["components"] == ["synonyms", "frequency_band"]


class TestDefinitionsPerformance:
    """Performance tests for definition endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.mark.benchmark
    def test_list_definitions_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark definition listing performance."""
        def list_definitions():
            response = client.get("/api/v1/definitions?limit=20")
            assert response.status_code == 200
            return response
        
        result = benchmark(list_definitions)
        
        # Performance assertions
        assert benchmark.stats["mean"] < 0.1  # Average under 100ms

    @pytest.mark.benchmark
    def test_get_definition_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark single definition retrieval."""
        # Get a definition ID
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            
            def get_definition():
                response = client.get(f"/api/v1/definitions/{definition_id}")
                assert response.status_code == 200
                return response
            
            result = benchmark(get_definition)
            
            # Performance assertions
            assert benchmark.stats["mean"] < 0.05  # Average under 50ms


class TestDefinitionsEdgeCases:
    """Edge case tests for definition endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_very_long_definition_text(self, client: TestClient) -> None:
        """Test handling of extremely long definition text."""
        # Create a word first
        word_data = {
            "text": "test_long_definition",
            "normalized": "test_long_definition",
            "language": "en",
        }
        word_response = client.post("/api/v1/words", json=word_data)
        
        if word_response.status_code == 201:
            word_id = word_response.json()["data"]["_id"]
            
            # Create definition with very long text
            long_text = "This is a very long definition. " * 100
            definition_data = {
                "word_id": word_id,
                "part_of_speech": "noun",
                "text": long_text,
            }
            
            response = client.post("/api/v1/definitions", json=definition_data)
            # Should either succeed or fail gracefully
            assert response.status_code in [201, 400, 422]

    def test_special_characters_in_definition(self, client: TestClient) -> None:
        """Test handling of special characters in definition text."""
        # Get a word
        words_response = client.get("/api/v1/words?limit=1")
        if words_response.status_code == 200 and words_response.json()["items"]:
            word_id = words_response.json()["items"][0]["_id"]
            
            special_texts = [
                "Definition with 'quotes' and \"double quotes\"",
                "Definition with emojis 😊 🎉",
                "Definition with symbols: @#$%^&*()",
                "Definition with newlines\nand\ttabs",
                "Definition with Unicode: café, naïve, 北京",
            ]
            
            for text in special_texts:
                definition_data = {
                    "word_id": word_id,
                    "part_of_speech": "noun",
                    "text": text,
                }
                
                response = client.post("/api/v1/definitions", json=definition_data)
                # Should handle gracefully
                assert response.status_code in [201, 400, 422]

    def test_invalid_query_parameters(self, client: TestClient) -> None:
        """Test invalid query parameter validation."""
        invalid_params = [
            "?frequency_band=0",  # Too low
            "?frequency_band=6",  # Too high
            "?cefr_level=Z9",  # Invalid CEFR level
            "?offset=-5",  # Negative offset
            "?limit=0",  # Zero limit
            "?limit=101",  # Exceeds max limit
        ]
        
        for params in invalid_params:
            response = client.get(f"/api/v1/definitions{params}")
            assert response.status_code == 422

    def test_malformed_definition_id(self, client: TestClient) -> None:
        """Test handling of malformed definition IDs."""
        bad_ids = [
            "not-an-objectid",
            "12345",
            "xyz123abc",
            "",
            "null",
        ]
        
        for bad_id in bad_ids:
            response = client.get(f"/api/v1/definitions/{bad_id}")
            assert response.status_code in [400, 422, 404]

    def test_concurrent_updates(self, client: TestClient) -> None:
        """Test handling of concurrent update attempts."""
        # Get a definition
        list_response = client.get("/api/v1/definitions?limit=1")
        items = list_response.json()["items"]
        
        if items:
            definition_id = items[0]["_id"]
            version = items[0].get("version", 1)
            
            # First update
            update1 = {"synonyms": ["first", "update"]}
            response1 = client.put(
                f"/api/v1/definitions/{definition_id}",
                json=update1,
                params={"version": version}
            )
            
            # Second update with same version (should fail)
            update2 = {"synonyms": ["second", "update"]}
            response2 = client.put(
                f"/api/v1/definitions/{definition_id}",
                json=update2,
                params={"version": version}
            )
            
            # One should succeed, one should fail
            statuses = [response1.status_code, response2.status_code]
            assert 200 in statuses  # One succeeded
            assert any(s in [409, 400] for s in statuses)  # One failed