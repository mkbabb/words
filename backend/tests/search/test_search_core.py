"""Core search functionality tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.models.dictionary import Definition, DictionaryProvider, Word
from floridify.search.constants import SearchMethod
from floridify.search.core import Search


@pytest_asyncio.fixture
async def search_engine(test_db, sample_words):
    """Create a search engine instance with proper corpus."""
    # Extract vocabulary from sample words
    vocabulary = sorted(set(word.text for word in sample_words))

    # Create and save corpus
    corpus = Corpus(
        corpus_name="test_corpus",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=vocabulary,
        original_vocabulary=vocabulary,
    )

    # Build necessary indices for search to work
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(vocabulary)}
    corpus._build_signature_index()

    manager = TreeCorpusManager()
    saved_corpus = await manager.save_corpus(corpus)

    # Create search engine from corpus
    engine = await Search.from_corpus(
        corpus_name=saved_corpus.corpus_name,
        semantic=False,  # Disable semantic for basic tests
    )
    yield engine
    if hasattr(engine, "close"):
        await engine.close()


@pytest_asyncio.fixture
async def sample_words(test_db):
    """Create sample words for search testing."""
    words_data = [
        {"text": "apple", "normalized": "apple", "lemma": "apple"},
        {"text": "apples", "normalized": "apples", "lemma": "apple"},
        {"text": "application", "normalized": "application", "lemma": "application"},
        {"text": "apply", "normalized": "apply", "lemma": "apply"},
        {"text": "applied", "normalized": "applied", "lemma": "apply"},
        {"text": "banana", "normalized": "banana", "lemma": "banana"},
        {"text": "cherry", "normalized": "cherry", "lemma": "cherry"},
        {"text": "date", "normalized": "date", "lemma": "date"},
        {"text": "elderberry", "normalized": "elderberry", "lemma": "elderberry"},
        {"text": "fig", "normalized": "fig", "lemma": "fig"},
    ]

    created_words = []
    for word_data in words_data:
        word = Word(**word_data, language=Language.ENGLISH)
        await word.save()
        created_words.append(word)

        # Add a simple definition for each word
        definition = Definition(
            word_id=word.id,
            text=f"A fruit called {word.text}",
            part_of_speech="noun",
            providers=[DictionaryProvider.FREE_DICTIONARY],
        )
        await definition.save()

    return created_words


class TestSearch:
    """Test suite for Search engine."""

    @pytest.mark.asyncio
    async def test_exact_search(self, search_engine: Search, sample_words, test_db):
        """Test exact word matching."""
        results = await search_engine.search("apple", method=SearchMethod.EXACT)

        assert len(results) > 0
        assert results[0].word == "apple"
        assert results[0].score == 1.0
        assert results[0].method == SearchMethod.EXACT

    @pytest.mark.asyncio
    async def test_fuzzy_search(self, search_engine: Search, sample_words, test_db):
        """Test fuzzy word matching."""
        results = await search_engine.search("aple", method=SearchMethod.FUZZY, min_score=0.7)

        assert len(results) > 0
        # Should find "apple" with high similarity
        apple_results = [r for r in results if r.word == "apple"]
        assert len(apple_results) > 0
        assert apple_results[0].method == SearchMethod.FUZZY
        assert apple_results[0].score > 0.7

    @pytest.mark.asyncio
    async def test_prefix_search(self, search_engine: Search, sample_words, test_db):
        """Test prefix matching."""
        results = await search_engine.search("app", method=SearchMethod.PREFIX)

        assert len(results) >= 3  # apple, application, apply
        words = [r.word for r in results]
        assert all(w.startswith("app") for w in words)

    @pytest.mark.asyncio
    async def test_cascade_search(self, search_engine: Search, sample_words, test_db):
        """Test cascading search fallback."""
        # First test exact match
        results = await search_engine.cascade_search("apple")
        assert len(results) > 0
        assert results[0].method == SearchMethod.EXACT

        # Test fuzzy fallback
        results = await search_engine.cascade_search("aple")
        assert len(results) > 0
        assert results[0].method == SearchMethod.FUZZY

    @pytest.mark.asyncio
    async def test_search_with_limit(self, search_engine: Search, sample_words, test_db):
        """Test search result limiting."""
        results = await search_engine.search("a", method=SearchMethod.PREFIX, max_results=3)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, search_engine: Search, sample_words, test_db):
        """Test case-insensitive search."""
        results_lower = await search_engine.search("apple", method=SearchMethod.EXACT)
        results_upper = await search_engine.search("APPLE", method=SearchMethod.EXACT)
        results_mixed = await search_engine.search("ApPlE", method=SearchMethod.EXACT)

        # All should find the same word
        assert len(results_lower) == len(results_upper) == len(results_mixed)
        assert results_lower[0].word == results_upper[0].word == results_mixed[0].word

    @pytest.mark.asyncio
    async def test_empty_query(self, search_engine: Search, test_db):
        """Test handling of empty search query."""
        results = await search_engine.search("", method=SearchMethod.EXACT)
        assert len(results) == 0

        results = await search_engine.search("   ", method=SearchMethod.EXACT)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_special_characters(self, test_db):
        """Test handling of special characters in search."""
        from floridify.text.normalize import batch_normalize

        # Create a fresh corpus with special characters
        original_vocabulary = ["café", "résumé", "naïve"]
        normalized_vocabulary = batch_normalize(original_vocabulary)

        corpus = Corpus(
            corpus_name="test_special",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=normalized_vocabulary,  # Normalized for search
            original_vocabulary=original_vocabulary,  # Original with diacritics
        )

        # Build necessary indices
        corpus.vocabulary_to_index = {word: i for i, word in enumerate(normalized_vocabulary)}
        corpus.normalized_to_original_indices = {i: [i] for i in range(len(normalized_vocabulary))}
        corpus._build_signature_index()

        # Save and create search engine
        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)
        search_engine = await Search.from_corpus(
            corpus_name=saved_corpus.corpus_name, semantic=False
        )

        # Test searching with diacritics - should normalize and find
        results = await search_engine.search("café", method=SearchMethod.EXACT)
        assert len(results) > 0
        assert results[0].word == "café"  # Returns original form

        # Test searching without diacritics finds the word with diacritics
        results = await search_engine.search("cafe", method=SearchMethod.EXACT)
        assert len(results) > 0
        assert results[0].word == "café"  # Returns original form

    @pytest.mark.asyncio
    async def test_search_scoring(self, search_engine: Search, sample_words, test_db):
        """Test that search results are properly scored."""
        results = await search_engine.search("app", method=SearchMethod.PREFIX)

        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, search_engine: Search, sample_words, test_db):
        """Test concurrent search operations."""
        import asyncio

        queries = ["apple", "banana", "cherry", "date", "fig"]

        # Run searches concurrently
        results = await asyncio.gather(
            *[search_engine.search(q, method=SearchMethod.EXACT) for q in queries]
        )

        # Each search should return results
        assert all(len(r) > 0 for r in results)
        # Results should match queries
        for query, result_list in zip(queries, results, strict=False):
            assert result_list[0].word == query

    @pytest.mark.asyncio
    async def test_search_metadata(self, search_engine: Search, sample_words, test_db):
        """Test that search results include proper metadata."""
        results = await search_engine.search("apple", method=SearchMethod.EXACT)

        assert len(results) > 0
        result = results[0]

        # Check result structure
        assert result.word == "apple"
        assert result.score == 1.0
        assert result.method == SearchMethod.EXACT
        assert result.language == Language.ENGLISH


class TestSearchMethod:
    """Test search method enumeration."""

    def test_search_method_values(self):
        """Test SearchMethod enum values."""
        assert SearchMethod.EXACT.value == "exact"
        assert SearchMethod.FUZZY.value == "fuzzy"
        assert SearchMethod.SEMANTIC.value == "semantic"
        assert SearchMethod.PREFIX.value == "prefix"

    def test_search_method_from_string(self):
        """Test creating SearchMethod from string."""
        assert SearchMethod("exact") == SearchMethod.EXACT
        assert SearchMethod("fuzzy") == SearchMethod.FUZZY
        assert SearchMethod("semantic") == SearchMethod.SEMANTIC
