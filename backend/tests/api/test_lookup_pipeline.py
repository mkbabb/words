"""
Comprehensive tests for the lookup pipeline REST API endpoints.
Tests both /api/v1/lookup/{word} and streaming variants with full pipeline coverage.
"""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from src.floridify.models.models import Definition, SynthesizedDictionaryEntry, Word
from tests.conftest import assert_response_structure, assert_valid_object_id


class TestLookupPipelineAPI:
    """Test lookup pipeline with comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_lookup_basic_word_success(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        mock_dictionary_providers,
        mock_openai_client
    ):
        """Test basic word lookup with existing data."""
        # Setup test data
        test_word = await word_factory(text="happy", language="en")
        await definition_factory(
            word_instance=test_word,
            part_of_speech="adjective",
            text="Feeling pleasure or contentment"
        )
        
        # Make request with no_ai=true to use mocked data and avoid OpenAI calls
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
        happiness_terms = ["pleasure", "contentment", "satisfaction", "joy", "happiness", "cheerful", "glad"]
        assert any(term in definition_text for term in happiness_terms), f"Definition should contain happiness-related terms, got: {definition_text}"

    @pytest.mark.asyncio
    async def test_lookup_word_not_found_triggers_providers(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers,
        mock_openai_client
    ):
        """Test lookup of non-existent word triggers provider lookup."""
        # Request non-existent word
        response = await async_client.get("/api/v1/lookup/nonexistentword123")
        
        # Should get data from mocked providers
        assert response.status_code == 200
        data = response.json()
        
        # Verify provider was called and data synthesized
        assert data["word"] == "nonexistentword123"
        assert "definitions" in data
        
        # Verify word was created in database
        word = await Word.find_one(Word.text == "nonexistentword123")
        assert word is not None

    @pytest.mark.asyncio
    async def test_lookup_with_query_parameters(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers,
        mock_openai_client
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
        mock_dictionary_providers
    ):
        """Test that lookups are properly cached."""
        # Setup test data
        test_word = await word_factory(text="cached", language="en")
        await definition_factory(word_instance=test_word)
        
        # First request
        response1 = await async_client.get("/api/v1/lookup/cached")
        assert response1.status_code == 200
        
        # Second request should be faster (cached)
        response2 = await async_client.get("/api/v1/lookup/cached")
        assert response2.status_code == 200
        
        # Responses should be identical
        assert response1.json() == response2.json()
        
        # Test cache invalidation with force_refresh
        response3 = await async_client.get("/api/v1/lookup/cached?force_refresh=true")
        assert response3.status_code == 200

    @pytest.mark.asyncio
    async def test_lookup_streaming_endpoint(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers,
        mock_openai_client
    ):
        """Test streaming lookup endpoint with Server-Sent Events."""
        response = await async_client.get(
            "/api/v1/lookup/streaming/stream",
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE events
        events = []
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                    events.append(event_data)
                except json.JSONDecodeError:
                    continue
        
        # Should have config, progress, and complete events
        event_types = [event.get('type') for event in events]
        assert 'config' in event_types
        assert 'progress' in event_types
        assert 'complete' in event_types

    @pytest.mark.asyncio
    async def test_lookup_with_ai_synthesis(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers,
        mock_openai_client
    ):
        """Test lookup with AI synthesis enabled."""
        response = await async_client.get("/api/v1/lookup/synthesize")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have AI-synthesized content
        assert "model_info" in data
        assert data["model_info"] is not None
        
        # Verify synthesized entry was created
        entry = await SynthesizedDictionaryEntry.find_one(
            SynthesizedDictionaryEntry.word_id is not None
        )
        assert entry is not None

    @pytest.mark.asyncio
    async def test_lookup_error_handling(self, async_client: AsyncClient):
        """Test error handling for invalid inputs."""
        # Empty word
        response = await async_client.get("/api/v1/lookup/")
        assert response.status_code == 404  # Not found route
        
        # Very long word
        long_word = "a" * 101
        response = await async_client.get(f"/api/v1/lookup/{long_word}")
        assert response.status_code in [400, 422]  # Bad request or validation error
        
        # Special characters
        response = await async_client.get("/api/v1/lookup/test%00word")
        assert response.status_code in [400, 422]
        
        # Path traversal attempt
        response = await async_client.get("/api/v1/lookup/../../../etc/passwd")
        assert response.status_code in [400, 404, 422]

    @pytest.mark.asyncio
    async def test_lookup_unicode_support(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers
    ):
        """Test lookup with Unicode characters."""
        unicode_words = ["café", "naïve", "résumé", "日本語"]
        
        for word in unicode_words:
            response = await async_client.get(f"/api/v1/lookup/{word}")
            assert response.status_code == 200
            data = response.json()
            assert data["word"] == word

    @pytest.mark.asyncio
    async def test_lookup_concurrent_requests(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers,
        mock_openai_client
    ):
        """Test handling of concurrent lookup requests."""
        # Create multiple concurrent requests for same word
        word = "concurrent"
        tasks = [
            async_client.get(f"/api/v1/lookup/{word}")
            for _ in range(10)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["word"] == word
        
        # Should only create one word entry (deduplication)
        word_count = await Word.count(Word.text == word)
        assert word_count == 1

    @pytest.mark.asyncio
    async def test_lookup_response_headers(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory
    ):
        """Test proper HTTP headers in lookup responses."""
        # Setup test data
        test_word = await word_factory(text="headers", language="en")
        await definition_factory(word_instance=test_word)
        
        response = await async_client.get("/api/v1/lookup/headers")
        
        assert response.status_code == 200
        
        # Check caching headers
        assert "ETag" in response.headers
        assert "Cache-Control" in response.headers
        
        # Test conditional request
        etag = response.headers["ETag"]
        conditional_response = await async_client.get(
            "/api/v1/lookup/headers",
            headers={"If-None-Match": etag}
        )
        assert conditional_response.status_code == 304

    @pytest.mark.asyncio
    async def test_lookup_database_integration(
        self,
        async_client: AsyncClient,
        mock_dictionary_providers,
        mock_openai_client
    ):
        """Test proper database operations during lookup."""
        word = "database"
        
        # Verify word doesn't exist initially
        initial_word = await Word.find_one(Word.text == word)
        assert initial_word is None
        
        # Make lookup request
        response = await async_client.get(f"/api/v1/lookup/{word}")
        assert response.status_code == 200
        
        # Verify word was created
        created_word = await Word.find_one(Word.text == word)
        assert created_word is not None
        assert_valid_object_id(created_word.id)
        
        # Verify definitions were created
        definitions = await Definition.find(Definition.word_id == created_word.id).to_list()
        assert len(definitions) > 0
        
        # Verify synthesized entry was created
        entry = await SynthesizedDictionaryEntry.find_one(
            SynthesizedDictionaryEntry.word_id == created_word.id
        )
        assert entry is not None

    @pytest.mark.asyncio
    async def test_lookup_provider_fallback_chain(
        self,
        async_client: AsyncClient,
        mocker
    ):
        """Test provider fallback when primary sources fail."""
        # Mock primary provider to fail
        mock_wiktionary = mocker.patch("floridify.connectors.wiktionary.WiktionaryConnector")
        mock_wiktionary.return_value.lookup_word = AsyncMock(side_effect=Exception("Provider error"))
        
        # Mock AI fallback to succeed
        mock_ai = mocker.patch("floridify.ai.connectors.OpenAIConnector")
        mock_ai.return_value.generate_response = AsyncMock(return_value={
            "definitions": [{"part_of_speech": "noun", "text": "AI generated definition"}]
        })
        
        response = await async_client.get("/api/v1/lookup/fallback")
        
        # Should still succeed via AI fallback
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
        performance_thresholds,
        benchmark
    ):
        """Benchmark lookup performance."""
        # Setup test data
        test_word = await word_factory(text="performance", language="en")
        await definition_factory(word_instance=test_word)
        
        async def lookup_operation():
            response = await async_client.get("/api/v1/lookup/performance")
            assert response.status_code == 200
            return response.json()
        
        # Benchmark the operation
        await benchmark.pedantic(lookup_operation, iterations=5, rounds=3)
        
        # Assert performance threshold
        assert benchmark.stats.stats.mean < performance_thresholds["lookup_simple"]

    @pytest.mark.asyncio
    async def test_lookup_with_multiple_definitions(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory
    ):
        """Test lookup for word with multiple definitions."""
        # Setup word with multiple definitions
        test_word = await word_factory(text="bank", language="en")
        
        # Financial institution
        await definition_factory(
            word_instance=test_word,
            part_of_speech="noun",
            text="A financial institution",
            sense_number="1"
        )
        
        # River bank
        await definition_factory(
            word_instance=test_word,
            part_of_speech="noun", 
            text="The land alongside a river",
            sense_number="2"
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