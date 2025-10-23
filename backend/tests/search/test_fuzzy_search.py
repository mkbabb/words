"""Fuzzy search component tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.search.constants import SearchMethod
from floridify.search.fuzzy import FuzzySearch


@pytest_asyncio.fixture
async def fuzzy_corpus(test_db):
    """Create corpus for fuzzy search testing."""
    vocabulary = [
        # Similar words for fuzzy matching
        "apple",
        "apples",
        "aple",
        "appel",
        "banana",
        "bananna",
        "bannana",
        "orange",
        "orang",
        "oranges",  # Added orange to match test expectations
        "strawberry",
        "strawbery",
        "stawberry",
        "watermelon",
        "watermellon",
        "watermelen",
        # Some distinct words
        "grape",
        "cherry",
        "peach",
        "plum",
    ]

    corpus = await Corpus.create(
        corpus_name="test_fuzzy_corpus",
        vocabulary=vocabulary,
        language=Language.ENGLISH,
    )
    corpus.corpus_type = CorpusType.LANGUAGE
    corpus.lemmatized_vocabulary = vocabulary

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


@pytest_asyncio.fixture
async def fuzzy_search():
    """Create FuzzySearch instance."""
    search = FuzzySearch(min_score=0.4)
    return search


class TestFuzzySearch:
    """Test suite for fuzzy search functionality."""

    @pytest.mark.asyncio
    async def test_rapidfuzz_integration(self, fuzzy_search, fuzzy_corpus):
        """Test RapidFuzz backend performance."""
        # Test with typo
        results = fuzzy_search.search("aple", corpus=fuzzy_corpus, max_results=5)

        # Should find "apple" as top result
        assert len(results) > 0
        assert results[0].word in ["apple", "aple"]
        assert results[0].method == SearchMethod.FUZZY
        assert results[0].score > 0.8

    @pytest.mark.asyncio
    async def test_candidate_preselection(self, fuzzy_search, fuzzy_corpus):
        """Test fuzzy candidate optimization."""
        # Search for a word with many similar candidates
        results = fuzzy_search.search("straberry", corpus=fuzzy_corpus, max_results=3)

        # Should efficiently find strawberry variants
        words = [r.word for r in results]
        assert any("straw" in w for w in words)

    @pytest.mark.asyncio
    async def test_multi_scorer_approach(self, fuzzy_search, fuzzy_corpus):
        """Test WRatio vs token_set_ratio scoring."""
        # Test different scoring methods - FuzzySearch uses default scorer
        # Test with single-word queries that exist in the corpus

        results_apple = fuzzy_search.search(
            "aple",  # Typo of apple
            corpus=fuzzy_corpus,
            max_results=5,
            min_score=0.5,
        )

        results_banana = fuzzy_search.search(
            "bananna",  # Alternative spelling in corpus
            corpus=fuzzy_corpus,
            max_results=5,
            min_score=0.5,
        )

        # Both should find related words
        assert len(results_apple) > 0
        assert len(results_banana) > 0

        # Should find apple variants
        apple_words = [r.word for r in results_apple]
        assert any("apple" in w or "aple" in w or "appel" in w for w in apple_words)

        # Should find banana variants
        banana_words = [r.word for r in results_banana]
        assert any("banana" in w or "bananna" in w for w in banana_words)

    @pytest.mark.asyncio
    async def test_typo_tolerance(self, fuzzy_search, fuzzy_corpus):
        """Test tolerance for different types of typos."""
        # Substitution
        results = fuzzy_search.search("apole", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word for r in results)

        # Insertion
        results = fuzzy_search.search("appple", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word for r in results)

        # Deletion
        results = fuzzy_search.search("aple", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word for r in results)

        # Transposition
        results = fuzzy_search.search("appel", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word or "appel" in r.word for r in results)

    @pytest.mark.asyncio
    async def test_similarity_threshold(self, fuzzy_search, fuzzy_corpus):
        """Test minimum similarity threshold."""
        # High threshold - should only find very similar words
        results = fuzzy_search.search("apple", corpus=fuzzy_corpus, max_results=10, min_score=0.9)

        # All results should have high similarity
        assert all(r.score >= 0.9 for r in results)

        # Low threshold - should find more distant matches
        results = fuzzy_search.search("apple", corpus=fuzzy_corpus, max_results=10, min_score=0.5)

        # Should find more results
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, fuzzy_search, fuzzy_corpus):
        """Test handling of empty queries."""
        results = fuzzy_search.search("", corpus=fuzzy_corpus)
        assert len(results) == 0

        results = fuzzy_search.search("   ", corpus=fuzzy_corpus)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_special_character_handling(self, fuzzy_search, fuzzy_corpus):
        """Test fuzzy search with special characters."""
        # Should normalize and still find matches
        results = fuzzy_search.search("app-le", corpus=fuzzy_corpus, max_results=3)
        assert len(results) > 0

        results = fuzzy_search.search("app_le", corpus=fuzzy_corpus, max_results=3)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_case_insensitive_fuzzy(self, fuzzy_search, fuzzy_corpus):
        """Test case-insensitive fuzzy matching."""
        results = fuzzy_search.search("APPLE", corpus=fuzzy_corpus, max_results=3)

        assert len(results) > 0
        # Should find apple regardless of case
        assert any("apple" in r.word.lower() for r in results)

    @pytest.mark.asyncio
    async def test_performance_with_large_vocabulary(self, test_db):
        """Test fuzzy search performance with large vocabulary."""
        # Generate large vocabulary
        large_vocab = []
        for i in range(1000):
            large_vocab.extend(
                [
                    f"word{i}",
                    f"term{i}",
                    f"text{i}",
                ]
            )

        corpus = Corpus(
            corpus_name="large_fuzzy_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(set(large_vocab)),
            original_vocabulary=large_vocab,
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        search = FuzzySearch(min_score=0.4)

        # Should complete search quickly even with large vocabulary
        import time

        start = time.time()
        results = search.search("word500", corpus=saved_corpus, max_results=5)
        elapsed = time.time() - start

        assert len(results) > 0
        assert elapsed < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_fuzzy_searches(self, fuzzy_search, fuzzy_corpus):
        """Test concurrent fuzzy searches."""
        import asyncio

        queries = ["aple", "bananna", "orang", "grap"]

        # Run searches concurrently
        results = await asyncio.gather(
            *[asyncio.to_thread(fuzzy_search.search, q, fuzzy_corpus, 3) for q in queries]
        )

        # Each search should return results
        assert all(len(r) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_fuzzy_search_ranking(self, fuzzy_search, fuzzy_corpus):
        """Test result ranking by similarity."""
        results = fuzzy_search.search("apple", corpus=fuzzy_corpus, max_results=10)

        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Exact match should be first if it exists
        if results and "apple" in fuzzy_corpus.vocabulary:
            assert results[0].word == "apple"
            assert results[0].score >= 0.99  # Fuzzy might not be exactly 1.0

    @pytest.mark.asyncio
    async def test_phonetic_similarity(self, fuzzy_search, fuzzy_corpus):
        """Test finding phonetically similar words."""
        # Words that sound similar but spelled differently
        results = fuzzy_search.search("cheree", corpus=fuzzy_corpus, max_results=5)

        # Should find "cherry" based on phonetic similarity
        words = [r.word for r in results]
        assert any("cherry" in w for w in words)

    @pytest.mark.asyncio
    async def test_fuzzy_with_empty_corpus(self, test_db):
        """Test fuzzy search with empty corpus."""
        corpus = Corpus(
            corpus_name="empty_fuzzy_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=[],
            original_vocabulary=[],
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        search = FuzzySearch(min_score=0.4)
        results = search.search("test", corpus=saved_corpus)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fuzzy_search_metadata(self, fuzzy_search, fuzzy_corpus):
        """Test metadata in fuzzy search results."""
        results = fuzzy_search.search("aple", corpus=fuzzy_corpus, max_results=3)

        for result in results:
            assert result.method == SearchMethod.FUZZY
            assert 0 <= result.score <= 1.0
            assert result.word in fuzzy_corpus.vocabulary
            assert result.lemmatized_word is not None
