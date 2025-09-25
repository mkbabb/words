"""Comprehensive tests for the search pipeline REST API endpoints.
Tests exact, fuzzy, and basic search functionality without FAISS dependencies.
"""

import asyncio

import pytest
from httpx import AsyncClient

from ..conftest import assert_response_structure


class TestSearchPipelineAPI:
    """Test search pipeline with comprehensive coverage."""

    @pytest.mark.asyncio
    async def test_search_exact_match(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        test_words,
    ):
        """Test exact word matching in search."""
        # Setup test words
        for word_text in test_words[:5]:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Test exact match
        response = await async_client.get("/api/v1/search?q=test")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        required_fields = ["query", "results", "total_found", "language"]
        assert_response_structure(data, required_fields)

        # Validate content
        assert data["query"] == "test"
        assert data["total_found"] > 0
        assert len(data["results"]) > 0

        # First result should be exact match with high score
        first_result = data["results"][0]
        assert first_result["word"] == "test"
        assert first_result["score"] >= 0.9
        assert first_result["method"] == "exact"

    @pytest.mark.asyncio
    async def test_search_fuzzy_matching(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test fuzzy matching for misspelled words."""
        # Setup test words
        words = ["testing", "tested", "tester", "testimony", "testament"]
        for word_text in words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Test fuzzy search with misspelling
        response = await async_client.get("/api/v1/search?q=testin")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "testin"
        assert data["total_found"] > 0

        # Should find similar words via fuzzy matching
        result_words = [r["word"] for r in data["results"]]
        assert "testing" in result_words

        # Check that fuzzy results have appropriate scores
        fuzzy_results = [r for r in data["results"] if r["method"] == "fuzzy"]
        assert len(fuzzy_results) > 0
        for result in fuzzy_results:
            assert 0.3 <= result["score"] <= 0.9

    @pytest.mark.asyncio
    async def test_search_with_path_parameter(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search using path parameter variant."""
        # Setup test data
        word = await word_factory(text="example", language="en")
        await definition_factory(word_instance=word)

        # Test path parameter variant
        response = await async_client.get("/api/v1/search/example")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "example"
        assert len(data["results"]) > 0
        assert data["results"][0]["word"] == "example"

    @pytest.mark.asyncio
    async def test_search_query_parameters(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search with various query parameters."""
        # Setup multiple test words
        words = ["search", "searching", "searched", "researcher", "research"]
        for word_text in words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Test max_results parameter
        response = await async_client.get("/api/v1/search?q=search&max_results=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2

        # Test min_score parameter
        response = await async_client.get("/api/v1/search?q=search&min_score=0.8")
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            assert result["score"] >= 0.8

        # Test language parameter
        response = await async_client.get("/api/v1/search?q=search&language=en")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"

    @pytest.mark.asyncio
    async def test_search_suggestions_endpoint(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search suggestions for autocomplete."""
        # Setup test words with common prefix
        suggestion_words = ["happy", "happiness", "happily", "happen", "happening"]
        for word_text in suggestion_words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Test suggestions
        response = await async_client.get("/api/v1/search/happ/suggestions")

        assert response.status_code == 200
        data = response.json()

        # Should return suggestions starting with "happ"
        assert len(data["results"]) > 0
        for result in data["results"]:
            assert result["word"].startswith("happ")

        # Test limit parameter
        response = await async_client.get("/api/v1/search/happ/suggestions?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 3

    @pytest.mark.asyncio
    async def test_search_no_results(self, async_client: AsyncClient):
        """Test search behavior when no results found."""
        response = await async_client.get("/api/v1/search?q=nonexistentword12345")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "nonexistentword12345"
        assert data["total_found"] == 0
        assert len(data["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_empty_query_handling(self, async_client: AsyncClient):
        """Test handling of empty or invalid queries."""
        # Empty query
        response = await async_client.get("/api/v1/search?q=")
        assert response.status_code in [400, 422]

        # Whitespace only
        response = await async_client.get("/api/v1/search?q=%20%20%20")
        assert response.status_code in [400, 422]

        # Very long query
        long_query = "a" * 201
        response = await async_client.get(f"/api/v1/search?q={long_query}")
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_search_unicode_support(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search with Unicode characters."""
        # Setup Unicode words
        unicode_words = ["café", "naïve", "résumé", "piñata"]
        for word_text in unicode_words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Test Unicode search
        response = await async_client.get("/api/v1/search?q=café")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "café"
        assert len(data["results"]) > 0
        assert data["results"][0]["word"] == "café"

    @pytest.mark.asyncio
    async def test_search_special_characters(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search with special characters and punctuation."""
        # Setup words with special characters
        special_words = ["e-mail", "self-control", "mother-in-law", "rock'n'roll"]
        for word_text in special_words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Test hyphenated word search
        response = await async_client.get("/api/v1/search?q=e-mail")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "e-mail"
        assert len(data["results"]) > 0

    @pytest.mark.asyncio
    async def test_search_case_insensitivity(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test that search is case insensitive."""
        # Setup test word
        word = await word_factory(text="CaseSensitive", language="en")
        await definition_factory(word_instance=word)

        # Test different case variations
        test_cases = ["casesensitive", "CASESENSITIVE", "CaseSensitive", "caseSENSITIVE"]

        for query in test_cases:
            response = await async_client.get(f"/api/v1/search?q={query}")

            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) > 0
            # Should find the word regardless of case
            result_words = [r["word"].lower() for r in data["results"]]
            assert "casesensitive" in result_words

    @pytest.mark.asyncio
    async def test_search_concurrent_requests(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test handling of concurrent search requests."""
        # Setup test words
        words = ["concurrent1", "concurrent2", "concurrent3"]
        for word_text in words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        # Create concurrent search requests
        tasks = [async_client.get("/api/v1/search?q=concurrent") for _ in range(10)]

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "concurrent"
            assert len(data["results"]) >= 3

    @pytest.mark.asyncio
    async def test_search_response_caching(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search response caching behavior."""
        # Setup test data
        word = await word_factory(text="cached", language="en")
        await definition_factory(word_instance=word)

        # First request
        response1 = await async_client.get("/api/v1/search?q=cached")
        assert response1.status_code == 200

        # Check caching headers
        assert "Cache-Control" in response1.headers

        # Second identical request should return same results
        response2 = await async_client.get("/api/v1/search?q=cached")
        assert response2.status_code == 200

        # Results should be identical
        assert response1.json() == response2.json()

    @pytest.mark.asyncio
    async def test_search_performance_benchmark(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
        performance_thresholds,
        benchmark,
    ):
        """Benchmark search performance."""
        # Setup multiple test words
        for i in range(50):
            word = await word_factory(text=f"searchword{i}", language="en")
            await definition_factory(word_instance=word)

        async def search_operation():
            response = await async_client.get("/api/v1/search?q=searchword")
            assert response.status_code == 200
            return response.json()

        # Benchmark the operation
        await benchmark.pedantic(search_operation, iterations=5, rounds=3)

        # Assert performance threshold
        assert benchmark.stats.stats.mean < performance_thresholds["search_basic"]

    @pytest.mark.asyncio
    async def test_search_result_scoring(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test that search results are properly scored and ordered."""
        # Setup words with varying similarity to query
        words = [
            ("test", 1.0),  # Exact match
            ("testing", 0.8),  # Close match
            ("testament", 0.6),  # Partial match
            ("best", 0.4),  # Fuzzy match
        ]

        for word_text, expected_min_score in words:
            word = await word_factory(text=word_text, language="en")
            await definition_factory(word_instance=word)

        response = await async_client.get("/api/v1/search?q=test")

        assert response.status_code == 200
        data = response.json()

        # Results should be ordered by score (highest first)
        scores = [result["score"] for result in data["results"]]
        assert scores == sorted(scores, reverse=True)

        # Exact match should have highest score
        if data["results"]:
            assert data["results"][0]["word"] == "test"
            assert data["results"][0]["score"] >= 0.9

    @pytest.mark.asyncio
    async def test_search_method_indication(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test that search results indicate the method used."""
        # Setup test words
        exact_word = await word_factory(text="exact", language="en")
        await definition_factory(word_instance=exact_word)

        fuzzy_word = await word_factory(text="exactly", language="en")
        await definition_factory(word_instance=fuzzy_word)

        response = await async_client.get("/api/v1/search?q=exact")

        assert response.status_code == 200
        data = response.json()

        # Should have results with method indicators
        methods = [result["method"] for result in data["results"]]
        assert "exact" in methods

        # May also have fuzzy matches
        valid_methods = ["exact", "fuzzy", "semantic"]
        for method in methods:
            assert method in valid_methods

    @pytest.mark.asyncio
    async def test_search_phrase_detection(
        self,
        async_client: AsyncClient,
        word_factory,
        definition_factory,
    ):
        """Test search behavior with multi-word phrases."""
        # Setup phrasal expressions
        phrase_word = await word_factory(text="break down", language="en")
        await definition_factory(
            word_instance=phrase_word,
            part_of_speech="phrasal verb",
            text="To stop working or functioning",
        )

        response = await async_client.get("/api/v1/search?q=break down")

        assert response.status_code == 200
        data = response.json()

        if data["results"]:
            # Should find the phrasal verb
            result_words = [r["word"] for r in data["results"]]
            assert "break down" in result_words

            # Should indicate it's a phrase
            phrase_results = [r for r in data["results"] if r.get("is_phrase")]
            assert len(phrase_results) > 0
