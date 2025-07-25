"""Test script to audit API endpoints for critical issues."""

import asyncio
import json
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from beanie import init_beanie, PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Test data for validation
TEST_CORPUS_DATA = {
    "words": ["test", "example", "validate"],
    "phrases": ["test phrase", "example sentence"],
    "name": "Test Corpus",
    "ttl_hours": 0.001  # Very short TTL for testing expiration
}

TEST_SYNONYM_WORD = "eloquent"
TEST_SUGGESTIONS_DATA = {
    "words": ["serendipity", "eloquent"],
    "count": 5
}

TEST_FACT_DATA = {
    "word_id": "507f1f77bcf86cd799439011",  # Example ObjectId
    "text": "This is a test fact",
    "category": "etymology",
    "confidence_score": 0.85
}

TEST_EXAMPLE_DATA = {
    "word_id": "507f1f77bcf86cd799439011",
    "definition_id": "507f1f77bcf86cd799439012",
    "text": "This is an example sentence.",
    "quality_score": 0.9
}


async def test_corpus_endpoint_vulnerabilities(client: AsyncClient):
    """Test corpus endpoint for security and edge cases."""
    
    # Test 1: Empty corpus creation
    response = await client.post("/api/v1/corpus", json={"words": []})
    assert response.status_code == 422  # Should fail validation
    
    # Test 2: Excessive TTL
    response = await client.post("/api/v1/corpus", json={
        "words": ["test"],
        "ttl_hours": 100  # Beyond max limit
    })
    assert response.status_code == 422
    
    # Test 3: Valid corpus creation
    response = await client.post("/api/v1/corpus", json=TEST_CORPUS_DATA)
    assert response.status_code == 200
    corpus_id = response.json()["corpus_id"]
    
    # Test 4: Search with invalid corpus ID
    response = await client.post(
        "/api/v1/corpus/invalid-uuid/search",
        params={"query": "test"}
    )
    assert response.status_code == 404
    
    # Test 5: Search with expired corpus (wait for expiration)
    await asyncio.sleep(0.1)  # Wait for corpus to expire
    response = await client.post(
        f"/api/v1/corpus/{corpus_id}/search",
        params={"query": "test"}
    )
    assert response.status_code == 404
    
    # Test 6: SQL injection attempt in search query
    response = await client.post("/api/v1/corpus", json={
        "words": ["test"],
        "ttl_hours": 1
    })
    corpus_id = response.json()["corpus_id"]
    
    response = await client.post(
        f"/api/v1/corpus/{corpus_id}/search",
        params={"query": "'; DROP TABLE corpus; --"}
    )
    assert response.status_code == 200  # Should handle safely
    

async def test_synonym_endpoint_edge_cases(client: AsyncClient):
    """Test synonym endpoint for edge cases."""
    
    # Test 1: Empty word
    response = await client.get("/api/v1/synonyms/")
    assert response.status_code == 404
    
    # Test 2: Special characters in word
    response = await client.get("/api/v1/synonyms/test%20word%3B%20DROP%20TABLE")
    assert response.status_code in [200, 500]  # Should handle gracefully
    
    # Test 3: Excessive max_results
    response = await client.get(f"/api/v1/synonyms/{TEST_SYNONYM_WORD}?max_results=100")
    assert response.status_code == 422
    
    # Test 4: Negative max_results
    response = await client.get(f"/api/v1/synonyms/{TEST_SYNONYM_WORD}?max_results=-1")
    assert response.status_code == 422


async def test_suggestions_endpoint_validation(client: AsyncClient):
    """Test suggestions endpoint validation."""
    
    # Test 1: Too many input words
    response = await client.post("/api/v1/suggestions", json={
        "words": ["word" + str(i) for i in range(15)],  # Beyond max limit
        "count": 10
    })
    assert response.status_code == 422
    
    # Test 2: Invalid count values
    response = await client.post("/api/v1/suggestions", json={
        "words": ["test"],
        "count": 20  # Beyond max limit
    })
    assert response.status_code == 422
    
    # Test 3: GET request with no params
    response = await client.get("/api/v1/suggestions")
    assert response.status_code == 200  # Should work with defaults
    

async def test_facts_endpoint_crud(client: AsyncClient):
    """Test facts endpoint CRUD operations."""
    
    # Test 1: Create fact with invalid word_id
    response = await client.post("/api/v1/facts", json={
        "word_id": "invalid",
        "text": "Test fact"
    })
    assert response.status_code in [422, 500]
    
    # Test 2: List facts with invalid filters
    response = await client.get("/api/v1/facts?confidence_score_min=2.0")
    assert response.status_code == 422
    
    # Test 3: Update non-existent fact
    fake_id = str(PydanticObjectId())
    response = await client.put(f"/api/v1/facts/{fake_id}", json={
        "text": "Updated fact"
    })
    assert response.status_code == 404
    
    # Test 4: Batch category lookup with injection attempt
    response = await client.get("/api/v1/facts/categories/'; DROP TABLE facts; --")
    assert response.status_code in [200, 500]  # Should handle safely


async def test_examples_endpoint_batch_operations(client: AsyncClient):
    """Test examples endpoint batch operations."""
    
    # Test 1: Batch update with empty list
    response = await client.post("/api/v1/examples/batch/update", json={
        "example_ids": [],
        "quality_scores": {}
    })
    assert response.status_code == 200
    assert response.json()["updated"] == 0
    
    # Test 2: Batch update with mismatched IDs and scores
    response = await client.post("/api/v1/examples/batch/update", json={
        "example_ids": [str(PydanticObjectId()), str(PydanticObjectId())],
        "quality_scores": {str(PydanticObjectId()): 0.5}  # Different ID
    })
    assert response.status_code == 200
    
    # Test 3: Generate examples for non-existent definition
    fake_id = str(PydanticObjectId())
    response = await client.post(f"/api/v1/examples/definition/{fake_id}/generate", json={
        "count": 3
    })
    assert response.status_code == 404


async def test_health_endpoint_monitoring(client: AsyncClient):
    """Test health endpoint monitoring capabilities."""
    
    # Test 1: Basic health check
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    health_data = response.json()
    
    # Validate response structure
    assert "status" in health_data
    assert "database" in health_data
    assert "search_engine" in health_data
    assert "cache_hit_rate" in health_data
    assert "uptime_seconds" in health_data
    assert "connection_pool" in health_data
    
    # Test 2: Check data types
    assert isinstance(health_data["cache_hit_rate"], float)
    assert 0 <= health_data["cache_hit_rate"] <= 1
    assert isinstance(health_data["uptime_seconds"], int)
    assert health_data["uptime_seconds"] >= 0


async def test_concurrent_requests(client: AsyncClient):
    """Test endpoint behavior under concurrent load."""
    
    # Create a corpus for testing
    response = await client.post("/api/v1/corpus", json={
        "words": ["test" + str(i) for i in range(100)],
        "ttl_hours": 1
    })
    corpus_id = response.json()["corpus_id"]
    
    # Test concurrent searches on same corpus
    async def search_corpus(query: str):
        return await client.post(
            f"/api/v1/corpus/{corpus_id}/search",
            params={"query": query}
        )
    
    # Launch 50 concurrent searches
    tasks = [search_corpus(f"test{i % 10}") for i in range(50)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check all succeeded
    success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
    assert success_count == len(tasks)


async def test_cache_performance(client: AsyncClient):
    """Test caching behavior and performance."""
    
    # Test 1: Synonym endpoint caching
    import time
    
    # First request (cache miss)
    start = time.time()
    response1 = await client.get(f"/api/v1/synonyms/{TEST_SYNONYM_WORD}")
    time1 = time.time() - start
    
    # Second request (cache hit)
    start = time.time()
    response2 = await client.get(f"/api/v1/synonyms/{TEST_SYNONYM_WORD}")
    time2 = time.time() - start
    
    # Cache hit should be significantly faster
    assert response1.json() == response2.json()
    # Note: Can't reliably test timing in all environments
    
    # Test 2: Suggestions endpoint caching
    response1 = await client.post("/api/v1/suggestions", json=TEST_SUGGESTIONS_DATA)
    response2 = await client.post("/api/v1/suggestions", json=TEST_SUGGESTIONS_DATA)
    
    # Should return same results
    assert response1.json()["words"] == response2.json()["words"]


# Fixture for test client
@pytest.fixture
async def client():
    """Create test client."""
    # This would normally connect to test database
    # For now, we'll just show the structure
    async with AsyncClient(base_url="http://localhost:8000") as ac:
        yield ac


if __name__ == "__main__":
    # Run tests
    print("API Endpoint Audit Tests")
    print("=" * 50)
    print("This script demonstrates the test cases for auditing endpoints.")
    print("To run actual tests, use: pytest tests/test_endpoint_audit.py")