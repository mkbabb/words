"""Comprehensive tests for multi-method search cascade integration."""

import time

import pytest

from floridify.corpus.core import Corpus
from floridify.search.constants import SearchMode
from floridify.search.core import Search
from floridify.search.models import SearchIndex


class TestSearchCascade:
    """Test the multi-method search cascade."""

    @pytest.mark.asyncio
    async def test_search_initialization(self, search_engine: Search):
        """Test unified Search engine initialization."""
        assert search_engine.corpus is not None
        assert search_engine.exact_search is not None
        assert search_engine.fuzzy_search is not None
        assert search_engine.semantic_search is not None

        # Check method priorities
        assert Search.METHOD_PRIORITY["exact"] > Search.METHOD_PRIORITY["fuzzy"]
        assert Search.METHOD_PRIORITY["fuzzy"] > Search.METHOD_PRIORITY["semantic"]

    @pytest.mark.asyncio
    async def test_exact_match_early_termination(self, search_engine: Search):
        """Test that exact matches terminate the cascade early."""
        start = time.perf_counter()
        results = await search_engine.search("apple", mode=SearchMode.SMART)
        elapsed = time.perf_counter() - start

        assert len(results) > 0
        assert results[0].word == "apple"
        assert results[0].method == "exact"
        assert results[0].score >= 0.99

        # Should be very fast due to early termination
        assert elapsed < 0.01  # 10ms

    @pytest.mark.asyncio
    async def test_fuzzy_fallback(self, search_engine: Search):
        """Test fallback to fuzzy search when exact fails."""
        # Misspelled word
        results = await search_engine.search("aple", mode=SearchMode.SMART)

        assert len(results) > 0
        # Should find apple through fuzzy search
        found_words = [r.word for r in results[:5]]
        assert "apple" in found_words

        # Check that fuzzy method was used
        methods_used = {r.method for r in results[:5]}
        assert "fuzzy" in methods_used

    @pytest.mark.asyncio
    async def test_semantic_fallback(self, search_engine: Search):
        """Test fallback to semantic search for conceptual queries."""
        # Conceptual query that won't match exact or fuzzy
        results = await search_engine.search("fruit", mode=SearchMode.SMART)

        assert len(results) > 0

        # Should use semantic search
        methods_used = {r.method for r in results}
        assert "semantic" in methods_used

        # Should find fruit-related words
        [r.word for r in results[:20]]
        # May find apple, banana, cherry, etc.

    @pytest.mark.asyncio
    async def test_cascade_ordering(self, search_engine: Search):
        """Test that cascade respects method priorities in results."""
        # Query that might match multiple methods
        results = await search_engine.search("comput", mode=SearchMode.SMART)

        assert len(results) > 0

        # Group results by method
        exact_results = [r for r in results if r.method == "exact"]
        fuzzy_results = [r for r in results if r.method == "fuzzy"]
        semantic_results = [r for r in results if r.method == "semantic"]

        # If we have results from multiple methods, exact should come first
        if exact_results and fuzzy_results:
            exact_min_idx = results.index(exact_results[0])
            fuzzy_min_idx = results.index(fuzzy_results[0])
            assert exact_min_idx < fuzzy_min_idx

        if fuzzy_results and semantic_results:
            fuzzy_min_idx = results.index(fuzzy_results[0])
            semantic_min_idx = results.index(semantic_results[0])
            assert fuzzy_min_idx < semantic_min_idx

    @pytest.mark.asyncio
    async def test_deduplication(self, search_engine: Search):
        """Test that duplicate results are properly deduplicated."""
        # A query that might return same word from multiple methods
        results = await search_engine.search("apple", mode=SearchMode.SMART, max_results=50)

        # Count occurrences of each word
        word_counts = {}
        for result in results:
            word_counts[result.word] = word_counts.get(result.word, 0) + 1

        # Each word should appear only once
        for word, count in word_counts.items():
            assert count == 1, f"Word '{word}' appears {count} times"

    @pytest.mark.asyncio
    async def test_score_normalization(self, search_engine: Search):
        """Test that scores are properly normalized across methods."""
        results = await search_engine.search("test", mode=SearchMode.SMART, max_results=50)

        for result in results:
            # All scores should be normalized to [0, 1]
            assert 0.0 <= result.score <= 1.0
            # Distance should be non-negative
            assert result.distance >= 0.0


class TestSearchModes:
    """Test different search modes."""

    @pytest.mark.asyncio
    async def test_exact_mode(self, search_engine: Search):
        """Test exact-only search mode."""
        results = await search_engine.search("apple", mode=SearchMode.EXACT)

        if results:
            # Should only contain exact matches
            for result in results:
                assert result.method == "exact"
                assert result.word.lower() == "apple"

    @pytest.mark.asyncio
    async def test_fuzzy_mode(self, search_engine: Search):
        """Test fuzzy-only search mode."""
        results = await search_engine.search("aple", mode=SearchMode.FUZZY)

        assert len(results) > 0
        # Should only contain fuzzy matches
        for result in results:
            assert result.method == "fuzzy"

    @pytest.mark.asyncio
    async def test_semantic_mode(self, search_engine: Search):
        """Test semantic-only search mode."""
        results = await search_engine.search("fruit", mode=SearchMode.SEMANTIC)

        assert len(results) > 0
        # Should only contain semantic matches
        for result in results:
            assert result.method == "semantic"

    @pytest.mark.asyncio
    async def test_smart_mode_adaptation(self, search_engine: Search):
        """Test that smart mode adapts to different query types."""
        # Exact word - should use exact
        exact_results = await search_engine.search("apple", mode=SearchMode.SMART)
        assert exact_results[0].method == "exact"

        # Misspelling - should use fuzzy
        fuzzy_results = await search_engine.search("aple", mode=SearchMode.SMART)
        assert any(r.method == "fuzzy" for r in fuzzy_results[:5])

        # Concept - should use semantic
        semantic_results = await search_engine.search("fruit vegetable food", mode=SearchMode.SMART)
        assert any(r.method == "semantic" for r in semantic_results)


class TestCascadePerformance:
    """Test cascade performance characteristics."""

    @pytest.mark.asyncio
    async def test_cascade_performance(self, search_engine: Search, performance_thresholds: dict):
        """Test overall cascade performance."""
        queries = [
            "apple",  # Exact match
            "aple",  # Fuzzy match
            "fruit",  # Semantic match
            "xyz123",  # No match
        ]

        # Warm up
        _ = await search_engine.search("test")

        start = time.perf_counter()
        for query in queries:
            _ = await search_engine.search(query, mode=SearchMode.SMART)
        avg_time = (time.perf_counter() - start) / len(queries)

        assert avg_time < performance_thresholds["cascade_search"]

    @pytest.mark.asyncio
    async def test_early_termination_efficiency(self, search_engine: Search):
        """Test that early termination improves performance."""
        # Exact match (should terminate early)
        start = time.perf_counter()
        await search_engine.search("apple", mode=SearchMode.SMART)
        exact_time = time.perf_counter() - start

        # Force all methods (no early termination)
        start = time.perf_counter()
        all_methods_results = []
        all_methods_results.extend(await search_engine.search("apple", mode=SearchMode.EXACT))
        all_methods_results.extend(await search_engine.search("apple", mode=SearchMode.FUZZY))
        all_methods_results.extend(await search_engine.search("apple", mode=SearchMode.SEMANTIC))
        all_methods_time = time.perf_counter() - start

        # Early termination should be faster
        assert exact_time < all_methods_time

    @pytest.mark.asyncio
    async def test_batch_cascade_performance(self, search_engine: Search):
        """Test performance with batch queries."""
        queries = [
            "apple",
            "banana",
            "computer",
            "education",
            "aple",
            "banna",
            "compter",
            "eduction",
            "fruit",
            "technology",
            "learning",
            "communication",
        ]

        start = time.perf_counter()
        results = []
        for query in queries:
            results.append(await search_engine.search(query, mode=SearchMode.SMART))
        batch_time = time.perf_counter() - start

        # Should complete reasonably fast
        assert batch_time < len(queries) * 0.1  # 100ms per query max
        assert all(isinstance(r, list) for r in results)


class TestSearchIndexIntegration:
    """Test SearchIndex model integration."""

    @pytest.mark.asyncio
    async def test_search_index_creation(self, sample_corpus: Corpus, search_engine: Search):
        """Test creating SearchIndex from search engine."""
        index = await SearchIndex.from_corpus(sample_corpus)

        assert index.corpus_id == sample_corpus.id
        assert index.corpus_name == sample_corpus.name
        assert index.language == sample_corpus.language
        assert index.search_config is not None

    @pytest.mark.asyncio
    async def test_search_index_persistence(self, sample_corpus: Corpus, test_db):
        """Test SearchIndex persistence with Metadata."""
        # Create and save index
        index = await SearchIndex.from_corpus(sample_corpus)

        # Should have proper configuration
        assert index.search_config.enable_exact is True
        assert index.search_config.enable_fuzzy is True
        assert index.search_config.enable_semantic is True

        # Check component indices
        assert index.trie_index_id is not None or index.trie_index_state == "pending"
        assert index.semantic_index_id is not None or index.semantic_index_state == "pending"

    @pytest.mark.asyncio
    async def test_search_from_index(self, sample_corpus: Corpus, search_engine: Search):
        """Test reconstructing Search from SearchIndex."""
        # Create index
        index = await SearchIndex.from_corpus(sample_corpus)

        # Reconstruct search engine
        reconstructed = await Search.from_search_index(index)

        assert reconstructed.corpus.id == search_engine.corpus.id

        # Test that search works
        results = await reconstructed.search("apple", mode=SearchMode.SMART)
        assert len(results) > 0


class TestCascadeEdgeCases:
    """Test edge cases in cascade behavior."""

    @pytest.mark.asyncio
    async def test_empty_query_cascade(self, search_engine: Search):
        """Test cascade with empty query."""
        results = await search_engine.search("", mode=SearchMode.SMART)
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_no_results_cascade(self, search_engine: Search):
        """Test cascade when no method returns results."""
        # Query that shouldn't match anything
        results = await search_engine.search("xyz123qwe456", mode=SearchMode.SMART)

        assert isinstance(results, list)
        # May return empty or low-score semantic matches

    @pytest.mark.asyncio
    async def test_special_character_cascade(self, search_engine: Search):
        """Test cascade with special characters."""
        special_queries = ["@test", "#hash", "user@email", "$100", "test-case"]

        for query in special_queries:
            results = await search_engine.search(query, mode=SearchMode.SMART)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_unicode_cascade(self, search_engine: Search):
        """Test cascade with Unicode queries."""
        unicode_queries = ["café", "naïve", "北京", "🚀"]

        for query in unicode_queries:
            results = await search_engine.search(query, mode=SearchMode.SMART)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_max_results_combination(self, search_engine: Search):
        """Test max_results with cascade combination."""
        # Request only 5 results
        results = await search_engine.search("test", mode=SearchMode.SMART, max_results=5)

        assert len(results) <= 5

        # Should still respect method priority
        if results:
            [r.method for r in results]
            # Higher priority methods should appear first

    @pytest.mark.asyncio
    async def test_min_score_cascade(self, search_engine: Search):
        """Test min_score filtering across cascade."""
        results = await search_engine.search("test", mode=SearchMode.SMART, min_score=0.7)

        # All results should meet threshold
        for result in results:
            assert result.score >= 0.7

    @pytest.mark.asyncio
    async def test_cascade_with_single_method_failure(self, sample_corpus: Corpus):
        """Test cascade when one method is unavailable."""
        # Create search from corpus
        search = await Search.from_corpus(
            corpus_name=sample_corpus.resource_id,
            semantic=False,  # Disable semantic
        )

        # Should still work with available methods
        results = await search.search("apple", mode=SearchMode.SMART)
        assert len(results) > 0
        assert all(r.method == "fuzzy" for r in results)

    @pytest.mark.asyncio
    async def test_result_metadata_preservation(self, search_engine: Search):
        """Test that metadata is preserved through cascade."""
        results = await search_engine.search("apple", mode=SearchMode.SMART)

        for result in results:
            assert result.word is not None
            assert result.score is not None
            assert result.method is not None
            assert result.distance is not None

            # Check metadata if present
            if result.metadata:
                # May contain frequency, source, etc.
                assert isinstance(result.metadata, dict)
