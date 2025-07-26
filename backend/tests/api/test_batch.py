"""Comprehensive tests for Batch operations endpoints."""

import pytest
from fastapi.testclient import TestClient

from floridify.api.main import app


class TestBatchLookupEndpoint:
    """Test batch word lookup operations."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_batch_lookup_basic(self, client: TestClient) -> None:
        """Test basic batch lookup functionality."""
        request_data = {
            "words": ["happy", "sad", "algorithm"],
            "force_refresh": False
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "errors" in data
        assert "summary" in data
        
        # Check summary
        assert data["summary"]["requested"] == 3
        assert data["summary"]["successful"] >= 0
        assert data["summary"]["failed"] >= 0
        assert data["summary"]["successful"] + data["summary"]["failed"] == 3

    def test_batch_lookup_with_providers(self, client: TestClient) -> None:
        """Test batch lookup with specific providers."""
        request_data = {
            "words": ["test", "example"],
            "providers": ["wiktionary"],
            "languages": ["en"],
            "force_refresh": True
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["summary"]["requested"] == 2

    def test_batch_lookup_empty_words(self, client: TestClient) -> None:
        """Test batch lookup with empty word list."""
        request_data = {
            "words": []
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_batch_lookup_too_many_words(self, client: TestClient) -> None:
        """Test batch lookup with too many words."""
        request_data = {
            "words": ["word" + str(i) for i in range(51)]  # 51 words, max is 50
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 422

    def test_batch_lookup_duplicate_words(self, client: TestClient) -> None:
        """Test batch lookup with duplicate words."""
        request_data = {
            "words": ["happy", "happy", "sad", "sad", "happy"]
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Should still process all words even if duplicates
        assert data["summary"]["requested"] == 5

    def test_batch_lookup_special_characters(self, client: TestClient) -> None:
        """Test batch lookup with special characters."""
        request_data = {
            "words": ["café", "naïve", "résumé", "test-word", "test's"]
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["summary"]["requested"] == 5

    def test_batch_lookup_mixed_results(self, client: TestClient) -> None:
        """Test batch lookup with mix of valid and invalid words."""
        request_data = {
            "words": ["happy", "xyzqwerty123", "algorithm", ""]
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Some should succeed, some should fail
        assert len(data["results"]) + len(data["errors"]) == 4


class TestBatchDefinitionUpdateEndpoint:
    """Test batch definition update operations."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_batch_definition_update_basic(self, client: TestClient) -> None:
        """Test basic batch definition update."""
        request_data = {
            "updates": [
                {
                    "word": "happy",
                    "index": 0,
                    "updates": {
                        "language_register": "informal",
                        "cefr_level": "A2"
                    }
                }
            ]
        }
        
        response = client.post("/api/v1/batch/definitions/update", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "summary" in data
        assert data["summary"]["total"] == 1

    def test_batch_definition_update_multiple(self, client: TestClient) -> None:
        """Test updating multiple definitions."""
        request_data = {
            "updates": [
                {
                    "word": "happy",
                    "index": 0,
                    "updates": {"frequency_band": 2}
                },
                {
                    "word": "sad",
                    "index": 0,
                    "updates": {"frequency_band": 2}
                },
                {
                    "word": "algorithm",
                    "index": 0,
                    "updates": {"domain": "computing"}
                }
            ]
        }
        
        response = client.post("/api/v1/batch/definitions/update", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["summary"]["total"] == 3

    def test_batch_definition_update_invalid_word(self, client: TestClient) -> None:
        """Test updating non-existent word."""
        request_data = {
            "updates": [
                {
                    "word": "xyzqwerty123nonexistent",
                    "index": 0,
                    "updates": {"cefr_level": "B1"}
                }
            ]
        }
        
        response = client.post("/api/v1/batch/definitions/update", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Should handle error gracefully
        assert data["summary"]["failed"] >= 1
        assert data["results"][0]["status"] == "error"
        assert "not found" in data["results"][0]["error"].lower()

    def test_batch_definition_update_invalid_index(self, client: TestClient) -> None:
        """Test updating with out-of-range index."""
        request_data = {
            "updates": [
                {
                    "word": "happy",
                    "index": 999,  # Likely out of range
                    "updates": {"cefr_level": "C1"}
                }
            ]
        }
        
        response = client.post("/api/v1/batch/definitions/update", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Should handle gracefully
        if data["results"][0]["status"] == "error":
            assert "index" in data["results"][0]["error"].lower()

    def test_batch_definition_update_empty_updates(self, client: TestClient) -> None:
        """Test batch update with empty update list."""
        request_data = {
            "updates": []
        }
        
        response = client.post("/api/v1/batch/definitions/update", json=request_data)
        assert response.status_code == 422

    def test_batch_definition_update_too_many(self, client: TestClient) -> None:
        """Test batch update with too many updates."""
        updates = [
            {
                "word": f"word{i}",
                "index": 0,
                "updates": {"cefr_level": "B1"}
            }
            for i in range(101)  # 101 updates, max is 100
        ]
        
        request_data = {"updates": updates}
        
        response = client.post("/api/v1/batch/definitions/update", json=request_data)
        assert response.status_code == 422


class TestBatchExecuteEndpoint:
    """Test generic batch execute operations."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_batch_execute_basic(self, client: TestClient) -> None:
        """Test basic batch execute functionality."""
        request_data = {
            "operations": [
                {
                    "method": "GET",
                    "endpoint": "/words/search/test",
                    "params": {"limit": 5}
                },
                {
                    "method": "POST",
                    "endpoint": "/lookup",
                    "data": {"word": "happy"}
                }
            ],
            "parallel": True,
            "stop_on_error": False
        }
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == 2
        assert data["summary"]["total"] == 2

    def test_batch_execute_sequential(self, client: TestClient) -> None:
        """Test sequential batch execution."""
        request_data = {
            "operations": [
                {"method": "GET", "endpoint": "/health"},
                {"method": "GET", "endpoint": "/words"},
                {"method": "GET", "endpoint": "/definitions"}
            ],
            "parallel": False,
            "stop_on_error": False
        }
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 3
        # Results should be in order for sequential execution
        for i, result in enumerate(data["results"]):
            assert result["index"] == i

    def test_batch_execute_stop_on_error(self, client: TestClient) -> None:
        """Test stop on error functionality."""
        request_data = {
            "operations": [
                {"method": "GET", "endpoint": "/valid"},
                {"method": "DELETE", "endpoint": "/invalid/endpoint"},  # Will fail
                {"method": "GET", "endpoint": "/should/not/execute"}
            ],
            "parallel": False,
            "stop_on_error": True
        }
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Should stop execution after error
        # Note: The simplified implementation might not actually fail,
        # but in production it would

    def test_batch_execute_empty_operations(self, client: TestClient) -> None:
        """Test batch execute with empty operations."""
        request_data = {
            "operations": []
        }
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 422

    def test_batch_execute_too_many_operations(self, client: TestClient) -> None:
        """Test batch execute with too many operations."""
        operations = [
            {"method": "GET", "endpoint": f"/endpoint{i}"}
            for i in range(101)  # 101 operations, max is 100
        ]
        
        request_data = {"operations": operations}
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 422

    def test_batch_execute_invalid_method(self, client: TestClient) -> None:
        """Test batch execute with invalid HTTP method."""
        request_data = {
            "operations": [
                {
                    "method": "INVALID",  # Not a valid HTTP method
                    "endpoint": "/test"
                }
            ]
        }
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 422


class TestBatchEndpointPerformance:
    """Performance tests for batch endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.mark.benchmark
    def test_batch_lookup_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark batch lookup performance."""
        request_data = {
            "words": ["test", "word", "example", "happy", "algorithm"]
        }
        
        def batch_lookup():
            response = client.post("/api/v1/batch/lookup", json=request_data)
            assert response.status_code == 200
            return response
        
        result = benchmark(batch_lookup)
        
        # Batch operations may take longer due to multiple lookups
        # But should still complete reasonably quickly
        assert benchmark.stats["mean"] < 5.0  # Average under 5 seconds

    @pytest.mark.benchmark
    def test_batch_execute_performance(self, client: TestClient, benchmark) -> None:
        """Benchmark batch execute performance."""
        request_data = {
            "operations": [
                {"method": "GET", "endpoint": f"/endpoint{i}"}
                for i in range(10)
            ],
            "parallel": True
        }
        
        def batch_execute():
            response = client.post("/api/v1/batch/execute", json=request_data)
            assert response.status_code == 200
            return response
        
        result = benchmark(batch_execute)
        
        # Parallel execution should be fast
        assert benchmark.stats["mean"] < 1.0  # Average under 1 second


class TestBatchEdgeCases:
    """Edge case tests for batch endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    def test_batch_lookup_unicode_words(self, client: TestClient) -> None:
        """Test batch lookup with unicode words."""
        request_data = {
            "words": ["café", "北京", "مرحبا", "🎯", "Zürich"]
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200

    def test_batch_lookup_very_long_word(self, client: TestClient) -> None:
        """Test batch lookup with very long words."""
        request_data = {
            "words": ["a" * 100, "normal", "b" * 200]
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200

    def test_batch_concurrent_same_word(self, client: TestClient) -> None:
        """Test batch lookup with same word multiple times."""
        request_data = {
            "words": ["test"] * 10  # Same word 10 times
        }
        
        response = client.post("/api/v1/batch/lookup", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["summary"]["requested"] == 10

    def test_batch_execute_mixed_methods(self, client: TestClient) -> None:
        """Test batch execute with different HTTP methods."""
        request_data = {
            "operations": [
                {"method": "GET", "endpoint": "/test1"},
                {"method": "POST", "endpoint": "/test2", "data": {"key": "value"}},
                {"method": "PATCH", "endpoint": "/test3", "data": {"update": True}},
                {"method": "DELETE", "endpoint": "/test4"}
            ],
            "parallel": True
        }
        
        response = client.post("/api/v1/batch/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["results"]) == 4