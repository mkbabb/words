"""Comprehensive tests for the lookup pipeline REST API endpoints.
Tests both /api/v1/lookup/{word} and streaming variants with full pipeline coverage.

The lookup pipeline requires search indices (trie, fuzzy, semantic) which are
expensive to build. These tests mock lookup_word_pipeline at the router level
while keeping real MongoDB documents and the full API response serialization.
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from floridify.models.dictionary import Definition, DictionaryEntry, Word

from ..conftest import assert_response_structure, assert_valid_object_id


class TestLookupPipelineAPI:
    """Test lookup pipeline with comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_lookup_basic_word_success(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        mock_lookup_pipeline,
    ):
        """Test basic word lookup with existing data."""
        # Setup test data
        test_word = await word_factory(text="happy", language="en")
        await definition_factory(
            word_instance=test_word,
            part_of_speech="adjective",
            text="Feeling pleasure or contentment",
        )

        # Make request — mock_lookup_pipeline creates a synthesis entry from existing data
        response = await async_client.get("/api/v1/lookup/happy?no_ai=true")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        required_fields = ["word", "definitions", "pronunciation"]
        assert_response_structure(data, required_fields)

        # Validate content
        assert data["word"] == "happy"
        assert len(data["definitions"]) >= 1
        assert data["definitions"][0]["part_of_speech"] == "adjective"
        # Accept various AI-generated happiness-related terms
        definition_text = data["definitions"][0]["text"].lower()
        happiness_terms = [
            "pleasure",
            "contentment",
            "satisfaction",
            "joy",
            "happiness",
            "cheerful",
            "glad",
        ]
        assert any(term in definition_text for term in happiness_terms), (
            f"Definition should contain happiness-related terms, got: {definition_text}"
        )

    @pytest.mark.asyncio
    async def test_lookup_word_not_found_triggers_providers(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline,
    ):
        """Test lookup of non-existent word triggers provider lookup."""
        # Request non-existent word — mock creates Word + Definition on the fly
        response = await async_client.get("/api/v1/lookup/nonexistentword")

        # Should get data from mocked pipeline
        assert response.status_code == 200
        data = response.json()

        # Verify word data returned
        assert data["word"] == "nonexistentword"
        assert "definitions" in data

        # Verify word was created in database (by mock)
        word = await Word.find_one(Word.text == "nonexistentword")
        assert word is not None

    @pytest.mark.asyncio
    async def test_lookup_with_query_parameters(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline,
    ):
        """Test lookup with various query parameters."""
        # Test force_refresh parameter
        response = await async_client.get("/api/v1/lookup/test?force_refresh=true")
        assert response.status_code == 200

        # Test providers parameter
        response = await async_client.get("/api/v1/lookup/test?providers=wiktionary")
        assert response.status_code == 200

        # Test languages parameter
        response = await async_client.get("/api/v1/lookup/test?languages=en")
        assert response.status_code == 200

        # Test no_ai parameter
        response = await async_client.get("/api/v1/lookup/test?no_ai=true")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_lookup_caching_behavior(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        mock_lookup_pipeline,
    ):
        """Test that lookups return consistent results."""
        # Setup test data
        test_word = await word_factory(text="cached", language="en")
        await definition_factory(word_instance=test_word)

        # First request
        response1 = await async_client.get("/api/v1/lookup/cached")
        assert response1.status_code == 200

        # Second request should also succeed
        response2 = await async_client.get("/api/v1/lookup/cached")
        assert response2.status_code == 200

        # Both should return the same word
        assert response1.json()["word"] == response2.json()["word"]

        # Test with force_refresh
        response3 = await async_client.get("/api/v1/lookup/cached?force_refresh=true")
        assert response3.status_code == 200

    @pytest.mark.asyncio
    async def test_lookup_streaming_endpoint(
        self,
        async_client: AsyncClient,
        mock_streaming_lookup,
    ):
        """Test streaming lookup endpoint with Server-Sent Events."""
        response = await async_client.get(
            "/api/v1/lookup/streaming/stream",
            headers={"Accept": "text/event-stream"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("data: "):
                try:
                    event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue

        # Should have at least some events (config and/or progress and/or complete)
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_lookup_with_ai_synthesis(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline_with_ai,
    ):
        """Test lookup with AI synthesis enabled."""
        response = await async_client.get("/api/v1/lookup/synthesize")

        assert response.status_code == 200
        data = response.json()

        # Should have AI-synthesized content
        assert "model_info" in data
        assert data["model_info"] is not None

        # Verify synthesized entry was created in DB
        entry = await DictionaryEntry.find_one(
            DictionaryEntry.provider == "synthesis",
        )
        assert entry is not None

    @pytest.mark.asyncio
    async def test_lookup_error_handling(self, async_client: AsyncClient):
        """Test error handling for invalid inputs."""
        # Empty word — FastAPI returns 404 because the route doesn't match
        response = await async_client.get("/api/v1/lookup/")
        assert response.status_code in [404, 307]  # Not found or redirect

        # Very long word (101 characters) — validation rejects it
        long_word = "a" * 101
        response = await async_client.get(f"/api/v1/lookup/{long_word}")
        assert response.status_code in [400, 422]  # Bad request or validation error

        # Null bytes are stripped by sanitization, resulting in "testword" which is valid.
        # But without mock_lookup_pipeline, the pipeline returns None -> 404.
        # We test that the sanitization doesn't crash.
        response = await async_client.get("/api/v1/lookup/test%00word")
        # Could be 200 (if pipeline finds it), 400, 404, or 422
        assert response.status_code in [200, 400, 404, 422]

        # Path traversal attempt — contains / which fails validation regex
        response = await async_client.get("/api/v1/lookup/../../../etc/passwd")
        assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_lookup_unicode_support(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline,
    ):
        """Test lookup with Unicode characters."""
        unicode_words = ["café", "naïve", "résumé"]

        for word in unicode_words:
            response = await async_client.get(f"/api/v1/lookup/{word}")
            assert response.status_code == 200
            data = response.json()
            assert data["word"] == word

    @pytest.mark.asyncio
    async def test_lookup_concurrent_requests(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline,
    ):
        """Test handling of concurrent lookup requests."""
        word = "concurrent"
        tasks = [async_client.get(f"/api/v1/lookup/{word}") for _ in range(5)]

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["word"] == word

    @pytest.mark.asyncio
    async def test_lookup_response_headers(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        mock_lookup_pipeline,
    ):
        """Test proper HTTP response from lookup."""
        # Setup test data
        test_word = await word_factory(text="headers", language="en")
        await definition_factory(word_instance=test_word)

        response = await async_client.get("/api/v1/lookup/headers")

        assert response.status_code == 200

        # Verify response is valid JSON
        data = response.json()
        assert data["word"] == "headers"
        assert "definitions" in data

    @pytest.mark.asyncio
    async def test_lookup_database_integration(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline,
    ):
        """Test proper database operations during lookup."""
        word = "database"

        # Verify word doesn't exist initially
        initial_word = await Word.find_one(Word.text == word)
        assert initial_word is None

        # Make lookup request — mock creates the Word in the test DB
        response = await async_client.get(f"/api/v1/lookup/{word}")
        assert response.status_code == 200

        # Verify word was created by mock pipeline
        created_word = await Word.find_one(Word.text == word)
        assert created_word is not None
        assert_valid_object_id(str(created_word.id))

        # Verify definitions were created
        definitions = await Definition.find(Definition.word_id == created_word.id).to_list()
        assert len(definitions) > 0

        # Verify synthesized entry was created
        entry = await DictionaryEntry.find_one(
            DictionaryEntry.word_id == created_word.id,
            DictionaryEntry.provider == "synthesis",
        )
        assert entry is not None

    @pytest.mark.asyncio
    async def test_lookup_provider_fallback_chain(
        self,
        async_client: AsyncClient,
        mock_lookup_pipeline,
    ):
        """Test that lookup works even when some providers fail.

        Since mock_lookup_pipeline bypasses real providers, this test verifies
        the API layer handles the pipeline result correctly regardless of
        provider behavior.
        """
        response = await async_client.get("/api/v1/lookup/fallback")

        # Should succeed via mock pipeline
        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "fallback"
        assert len(data["definitions"]) > 0

    @pytest.mark.asyncio
    async def test_lookup_performance_benchmark(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        mock_lookup_pipeline,
        performance_thresholds,
    ):
        """Test that lookup completes within performance thresholds."""
        import time

        # Setup test data
        test_word = await word_factory(text="performance", language="en")
        await definition_factory(word_instance=test_word)

        # Time the operation
        start = time.perf_counter()
        response = await async_client.get("/api/v1/lookup/performance")
        elapsed = time.perf_counter() - start

        assert response.status_code == 200

        # Assert performance threshold (generous since this is mocked)
        assert elapsed < performance_thresholds.get("lookup_single", 2.0)

    @pytest.mark.asyncio
    async def test_lookup_with_multiple_definitions(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        mock_lookup_pipeline,
    ):
        """Test lookup for word with multiple definitions."""
        # Setup word with multiple definitions
        test_word = await word_factory(text="bank", language="en")

        # Financial institution
        await definition_factory(
            word_instance=test_word,
            part_of_speech="noun",
            text="A financial institution",
        )

        # River bank
        await definition_factory(
            word_instance=test_word,
            part_of_speech="noun",
            text="The land alongside a river",
        )

        response = await async_client.get("/api/v1/lookup/bank")

        assert response.status_code == 200
        data = response.json()

        assert data["word"] == "bank"
        assert len(data["definitions"]) == 2

        # Verify both definitions are present
        definition_texts = [d["text"] for d in data["definitions"]]
        assert any("financial" in text.lower() for text in definition_texts)
        assert any("river" in text.lower() for text in definition_texts)
