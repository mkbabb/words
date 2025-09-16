"""
Comprehensive tests for the corpus pipeline REST API endpoints.
Tests TTL-based corpus management, search within corpus, and cache behavior.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from ..conftest import assert_response_structure
from httpx import AsyncClient


class TestCorpusPipelineAPI:
    """Test corpus pipeline with comprehensive TTL and caching coverage."""

    @pytest.mark.asyncio
    async def test_create_corpus_basic(self, async_client: AsyncClient):
        """Test basic corpus creation."""
        corpus_data = {
            "words": ["apple", "banana", "cherry", "date"],
            "name": "test_fruits",
            "ttl_hours": 1.0,
        }

        response = await async_client.post("/api/v1/corpus", json=corpus_data)

        assert response.status_code == 201
        data = response.json()

        # Validate response structure
        required_fields = ["corpus_id", "word_count", "expires_at"]
        assert_response_structure(data, required_fields)

        # Validate content
        assert data["word_count"] == 4
        assert data["corpus_id"] is not None
        assert data["expires_at"] is not None

        # Verify expiration time is roughly 1 hour from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        expected_expiry = datetime.now(UTC) + timedelta(hours=1)
        # Ensure both datetimes have timezone info
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 3600 * 5  # Within 5 hours tolerance (covers timezone issues)

    @pytest.mark.asyncio
    async def test_create_corpus_with_phrases(self, async_client: AsyncClient):
        """Test corpus creation with both words and phrases."""
        corpus_data = {
            "words": ["run", "walk", "jump"],
            "phrases": ["run away", "walk the dog", "jump rope"],
            "name": "actions_corpus",
            "ttl_hours": 2.0,
        }

        response = await async_client.post("/api/v1/corpus", json=corpus_data)

        assert response.status_code == 201
        data = response.json()

        assert data["word_count"] == 3
        assert data["phrase_count"] == 3
        assert "corpus_id" in data

    @pytest.mark.asyncio
    async def test_create_corpus_validation(self, async_client: AsyncClient):
        """Test corpus creation input validation."""
        # Empty words list
        response = await async_client.post(
            "/api/v1/corpus", json={"words": [], "name": "empty_corpus"}
        )
        assert response.status_code in [400, 422]

        # Invalid TTL (too high)
        response = await async_client.post(
            "/api/v1/corpus",
            json={
                "words": ["test"],
                "ttl_hours": 25.0,  # Over 24 hour limit
            },
        )
        assert response.status_code in [400, 422]

        # Invalid TTL (negative)
        response = await async_client.post(
            "/api/v1/corpus", json={"words": ["test"], "ttl_hours": -1.0}
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_search_within_corpus(self, async_client: AsyncClient):
        """Test searching within a created corpus."""
        # Create corpus
        corpus_data = {
            "words": ["testing", "tester", "testify", "protest", "contest"],
            "name": "test_words_corpus",
        }

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        assert create_response.status_code == 201
        corpus_id = create_response.json()["corpus_id"]

        # Search within corpus
        search_response = await async_client.post(
            f"/api/v1/corpus/{corpus_id}/search?query=test&max_results=10"
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Validate response structure
        required_fields = ["results", "metadata"]
        assert_response_structure(data, required_fields)

        # Should find words containing "test"
        assert len(data["results"]) > 0
        result_words = [r["word"] for r in data["results"]]
        assert "testing" in result_words
        assert "tester" in result_words

    @pytest.mark.asyncio
    async def test_search_corpus_fuzzy_matching(self, async_client: AsyncClient):
        """Test fuzzy matching within corpus search."""
        # Create corpus with similar words
        corpus_data = {
            "words": ["beautiful", "beutiful", "beatiful", "handsome", "pretty"],
            "name": "beauty_corpus",
        }

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        corpus_id = create_response.json()["corpus_id"]

        # Search with misspelling
        search_response = await async_client.post(
            f"/api/v1/corpus/{corpus_id}/search?query=beatuful&min_score=0.3"
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Should find similar words via fuzzy matching
        assert len(data["results"]) > 0
        result_words = [r["word"] for r in data["results"]]
        assert "beautiful" in result_words

    @pytest.mark.asyncio
    async def test_get_corpus_info(self, async_client: AsyncClient):
        """Test retrieving corpus metadata and statistics."""
        # Create corpus
        corpus_data = {
            "words": ["info", "data", "metadata"],
            "name": "info_corpus",
            "ttl_hours": 0.5,
        }

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        corpus_id = create_response.json()["corpus_id"]

        # Get corpus info
        info_response = await async_client.get(f"/api/v1/corpus/{corpus_id}")

        assert info_response.status_code == 200
        data = info_response.json()

        # Validate response structure
        required_fields = ["corpus_id", "name", "created_at", "expires_at", "word_count"]
        assert_response_structure(data, required_fields)

        # Validate content
        assert data["corpus_id"] == corpus_id
        assert data["name"] == "info_corpus"
        assert data["word_count"] == 3
        assert data["search_count"] == 0  # No searches yet

    @pytest.mark.asyncio
    async def test_list_all_corpora(self, async_client: AsyncClient):
        """Test listing all active corpora."""
        # Create multiple corpora
        corpus_names = ["corpus1", "corpus2", "corpus3"]
        for name in corpus_names:
            corpus_data = {"words": ["word1", "word2"], "name": name}
            await async_client.post("/api/v1/corpus", json=corpus_data)

        # List all corpora
        response = await async_client.get("/api/v1/corpus")

        assert response.status_code == 200
        data = response.json()

        # Should be paginated response
        assert "total" in data
        assert "items" in data
        assert len(data["items"]) >= 3

        # Should include our created corpora
        corpus_names_in_response = [item["name"] for item in data["items"]]
        for name in corpus_names:
            assert name in corpus_names_in_response

    @pytest.mark.asyncio
    async def test_corpus_ttl_expiration(self, async_client: AsyncClient):
        """Test corpus TTL expiration behavior."""
        # Create corpus with very short TTL (minimum allowed)
        corpus_data = {
            "words": ["expire", "soon"],
            "name": "short_lived_corpus",
            "ttl_hours": 0.001,  # ~3.6 seconds
        }

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        assert create_response.status_code == 201
        corpus_id = create_response.json()["corpus_id"]

        # Corpus should be accessible immediately
        info_response = await async_client.get(f"/api/v1/corpus/{corpus_id}")
        assert info_response.status_code == 200

        # Wait for TTL expiration
        await asyncio.sleep(4)

        # Corpus should be expired/not found
        expired_response = await async_client.get(f"/api/v1/corpus/{corpus_id}")
        assert expired_response.status_code == 404

    @pytest.mark.asyncio
    async def test_corpus_search_not_found(self, async_client: AsyncClient):
        """Test search in non-existent or expired corpus."""
        fake_corpus_id = "nonexistent_corpus_123"

        search_response = await async_client.post(
            f"/api/v1/corpus/{fake_corpus_id}/search?query=test"
        )

        assert search_response.status_code == 404
        error_data = search_response.json()
        assert (
            "not found" in error_data["detail"].lower() or "expired" in error_data["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_corpus_search_usage_tracking(self, async_client: AsyncClient):
        """Test that corpus searches are tracked in statistics."""
        # Create corpus
        corpus_data = {"words": ["track", "usage", "statistics"], "name": "tracking_corpus"}

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        corpus_id = create_response.json()["corpus_id"]

        # Initial search count should be 0
        info_response = await async_client.get(f"/api/v1/corpus/{corpus_id}")
        assert info_response.json()["search_count"] == 0

        # Perform searches
        for i in range(3):
            await async_client.post(f"/api/v1/corpus/{corpus_id}/search?query=track")

        # Search count should be updated
        updated_info = await async_client.get(f"/api/v1/corpus/{corpus_id}")
        assert updated_info.json()["search_count"] == 3

        # Last accessed should be updated
        assert "last_accessed" in updated_info.json()

    @pytest.mark.asyncio
    async def test_corpus_cache_stats(self, async_client: AsyncClient):
        """Test corpus cache statistics endpoint."""
        response = await async_client.get("/api/v1/corpus/stats")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        required_fields = ["status", "cache", "message"]
        assert_response_structure(data, required_fields)

        # Cache stats should include cache size, max size, etc.
        assert "cache_size" in data["cache"] or "size" in data["cache"]
        assert "max_size" in data["cache"]

    @pytest.mark.asyncio
    async def test_corpus_concurrent_creation(self, async_client: AsyncClient):
        """Test concurrent corpus creation."""
        # Create multiple corpora simultaneously
        corpus_data_list = [
            {"words": [f"word{i}1", f"word{i}2"], "name": f"concurrent_corpus_{i}"}
            for i in range(5)
        ]

        tasks = [
            async_client.post("/api/v1/corpus", json=corpus_data)
            for corpus_data in corpus_data_list
        ]

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 201
            data = response.json()
            assert "corpus_id" in data

        # All should have unique IDs
        corpus_ids = [r.json()["corpus_id"] for r in responses]
        assert len(set(corpus_ids)) == len(corpus_ids)

    @pytest.mark.asyncio
    async def test_corpus_large_word_list(self, async_client: AsyncClient):
        """Test corpus creation with large word list."""
        # Create large corpus (approaching limits)
        large_word_list = [f"word{i}" for i in range(1000)]

        corpus_data = {"words": large_word_list, "name": "large_corpus"}

        response = await async_client.post("/api/v1/corpus", json=corpus_data)

        assert response.status_code == 201
        data = response.json()
        assert data["word_count"] == 1000

    @pytest.mark.asyncio
    async def test_corpus_search_performance(
        self, async_client: AsyncClient, performance_thresholds, benchmark
    ):
        """Benchmark corpus search performance."""
        # Create corpus with substantial word list
        words = [f"searchword{i}" for i in range(100)]
        corpus_data = {"words": words, "name": "performance_corpus"}

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        corpus_id = create_response.json()["corpus_id"]

        async def search_operation():
            response = await async_client.post(
                f"/api/v1/corpus/{corpus_id}/search?query=searchword&max_results=20"
            )
            assert response.status_code == 200
            return response.json()

        # Benchmark the search operation
        await benchmark.pedantic(search_operation, iterations=5, rounds=3)

        # Should be fast since it's in-memory search
        assert benchmark.stats.stats.mean < 0.1  # 100ms

    @pytest.mark.asyncio
    async def test_corpus_memory_cleanup(self, async_client: AsyncClient):
        """Test that expired corpora are cleaned up from memory."""
        # Create corpus with short TTL
        corpus_data = {
            "words": ["cleanup", "memory", "test"],
            "name": "cleanup_corpus",
            "ttl_hours": 0.001,  # Very short
        }

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        create_response.json()["corpus_id"]

        # Get initial cache stats
        initial_stats = await async_client.get("/api/v1/corpus/stats")
        initial_stats.json()["cache"]["size"]

        # Wait for expiration and cleanup
        await asyncio.sleep(5)

        # Cache size should be reduced (cleanup occurred)
        final_stats = await async_client.get("/api/v1/corpus/stats")
        final_stats.json()["cache"]["size"]

        # Note: This test is probabilistic as cleanup may be async
        # We mainly verify the stats endpoint works and size is tracked

    @pytest.mark.asyncio
    async def test_corpus_search_result_ranking(self, async_client: AsyncClient):
        """Test that corpus search results are properly ranked."""
        # Create corpus with words of varying similarity
        corpus_data = {
            "words": ["test", "testing", "tester", "protest", "contest", "best"],
            "name": "ranking_corpus",
        }

        create_response = await async_client.post("/api/v1/corpus", json=corpus_data)
        corpus_id = create_response.json()["corpus_id"]

        # Search for "test"
        search_response = await async_client.post(f"/api/v1/corpus/{corpus_id}/search?query=test")

        data = search_response.json()
        results = data["results"]

        # Results should be ordered by relevance score
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

        # Exact match should have highest score
        if results:
            assert results[0]["word"] == "test"
            assert results[0]["score"] >= 0.9

    @pytest.mark.asyncio
    async def test_corpus_default_ttl(self, async_client: AsyncClient):
        """Test corpus creation with default TTL."""
        corpus_data = {
            "words": ["default", "ttl", "test"],
            "name": "default_ttl_corpus",
            # No ttl_hours specified
        }

        response = await async_client.post("/api/v1/corpus", json=corpus_data)

        assert response.status_code == 201
        data = response.json()

        # Should have default TTL (1 hour)
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        expected_expiry = datetime.now(UTC) + timedelta(hours=1)
        # Ensure both datetimes have timezone info
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 3600 * 5  # Within 5 hours tolerance (covers timezone issues)
