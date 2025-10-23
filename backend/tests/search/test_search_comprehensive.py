"""Comprehensive search tests with language and literature corpora."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.models.base import Language
from floridify.search.constants import SearchMethod
from floridify.search.core import Search


@pytest_asyncio.fixture
async def language_corpus_small(test_db):
    """Create a small language corpus for testing."""
    # Small set of words for basic testing
    vocabulary = [
        "apple",
        "apples",
        "application",
        "apply",
        "applied",
        "banana",
        "bananas",
        "band",
        "bandage",
        "cat",
        "cats",
        "catch",
        "catching",
        "caught",
        "dog",
        "dogs",
        "dodge",
        "dodging",
        "elephant",
        "elephants",
        "elegant",
        "elegance",
    ]

    corpus = Corpus(
        corpus_name="test_language_small",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=sorted(vocabulary),
        original_vocabulary=vocabulary,
    )

    # Build necessary indices for search
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted(vocabulary))}
    corpus._build_signature_index()

    # Save corpus to database
    from floridify.corpus.manager import TreeCorpusManager

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)

    return saved


@pytest_asyncio.fixture
async def language_corpus_large(test_db):
    """Create a large language corpus for performance testing."""
    # Generate larger vocabulary for performance testing
    base_words = [
        "test",
        "word",
        "search",
        "find",
        "query",
        "match",
        "result",
        "language",
        "corpus",
        "index",
    ]
    vocabulary = []

    for base in base_words:
        for i in range(100):
            vocabulary.append(f"{base}{i}")
            vocabulary.append(f"{base}ing{i}")
            vocabulary.append(f"{base}ed{i}")
            vocabulary.append(f"{base}s{i}")

    corpus = Corpus(
        corpus_name="test_language_large",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=sorted(set(vocabulary)),
        original_vocabulary=vocabulary,
    )

    # Build necessary indices for search
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(corpus.vocabulary)}
    corpus._build_signature_index()

    from floridify.corpus.manager import TreeCorpusManager

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)

    return saved


@pytest_asyncio.fixture
async def literature_corpus(test_db):
    """Create a literature corpus for testing."""
    # Extract vocabulary from sample text
    sample_text = """
    The quick brown fox jumps over the lazy dog.
    This is a sample text for testing literature corpus.
    It contains various words and phrases that will be indexed.
    Search functionality should work across all these terms.
    """

    # Simple word extraction
    words = []
    for word in sample_text.lower().split():
        cleaned = "".join(c for c in word if c.isalnum())
        if cleaned:
            words.append(cleaned)

    vocabulary = sorted(set(words))

    corpus = Corpus(
        corpus_name="test_literature",
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        vocabulary=vocabulary,
        original_vocabulary=words,
    )

    # Build necessary indices for search
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(vocabulary)}
    corpus._build_signature_index()

    from floridify.corpus.manager import TreeCorpusManager

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)

    return saved


@pytest_asyncio.fixture
async def search_engine_small(language_corpus_small):
    """Create search engine with small language corpus."""
    engine = await Search.from_corpus(
        corpus_name=language_corpus_small.corpus_name,
        semantic=False,  # Disable semantic for faster tests
    )
    yield engine
    if hasattr(engine, "close"):
        await engine.close()


@pytest_asyncio.fixture
async def search_engine_large(language_corpus_large):
    """Create search engine with large language corpus."""
    engine = await Search.from_corpus(
        corpus_name=language_corpus_large.corpus_name,
        semantic=False,  # Disable semantic for performance testing
    )
    yield engine
    if hasattr(engine, "close"):
        await engine.close()


@pytest_asyncio.fixture
async def search_engine_literature(literature_corpus):
    """Create search engine with literature corpus."""
    engine = await Search.from_corpus(corpus_name=literature_corpus.corpus_name, semantic=False)
    yield engine
    if hasattr(engine, "close"):
        await engine.close()


@pytest_asyncio.fixture
async def search_engine_with_semantic(language_corpus_small):
    """Create search engine with semantic search enabled."""
    engine = await Search.from_corpus(
        corpus_name=language_corpus_small.corpus_name, semantic=True
    )

    # Wait for semantic initialization to complete
    if engine.semantic_search and hasattr(engine, "_semantic_init_task"):
        if engine._semantic_init_task and not engine._semantic_init_task.done():
            await engine._semantic_init_task

    yield engine
    if hasattr(engine, "close"):
        await engine.close()


class TestSearchWithSmallCorpus:
    """Test search functionality with small language corpus."""

    @pytest.mark.asyncio
    async def test_exact_search(self, search_engine_small):
        """Test exact word matching."""
        results = await search_engine_small.search("apple", method=SearchMethod.EXACT)

        assert len(results) > 0
        assert results[0].word == "apple"
        assert results[0].method == SearchMethod.EXACT
        assert results[0].score >= 0.95

    @pytest.mark.asyncio
    async def test_prefix_search(self, search_engine_small):
        """Test prefix matching."""
        results = await search_engine_small.search("app", method=SearchMethod.PREFIX)

        assert len(results) > 0
        words = [r.word for r in results]
        # Should match apple, apples, application, apply, applied
        assert "apple" in words
        assert "application" in words
        assert "apply" in words

    @pytest.mark.asyncio
    async def test_fuzzy_search(self, search_engine_small):
        """Test fuzzy matching for typos."""
        results = await search_engine_small.search("aple", method=SearchMethod.FUZZY)

        assert len(results) > 0
        words = [r.word for r in results]
        assert "apple" in words  # Should find despite typo

    @pytest.mark.asyncio
    async def test_cascade_search_fallback(self, search_engine_small):
        """Test cascade search with fallback."""
        # Test exact match first
        results = await search_engine_small.cascade_search("apple")
        assert len(results) > 0
        assert results[0].word == "apple"
        assert results[0].method == SearchMethod.EXACT

        # Test fuzzy fallback for typo
        results = await search_engine_small.cascade_search("aple")
        assert len(results) > 0
        assert results[0].method == SearchMethod.FUZZY

    @pytest.mark.asyncio
    async def test_multi_method_search(self, search_engine_small):
        """Test cascading through multiple search methods."""
        # Search for something that won't exact match
        results = await search_engine_small.search("elepha")

        assert len(results) > 0
        # Should find elephant through prefix or fuzzy
        words = [r.word for r in results]
        assert "elephant" in words or "elephants" in words

    @pytest.mark.asyncio
    async def test_empty_query(self, search_engine_small):
        """Test handling empty search queries."""
        results = await search_engine_small.search("")
        assert len(results) == 0

        results = await search_engine_small.search("   ")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_word(self, search_engine_small):
        """Test searching for word not in corpus."""
        results = await search_engine_small.search("xyz123notaword")
        assert len(results) == 0


class TestSearchWithLargeCorpus:
    """Test search performance with large language corpus."""

    @pytest.mark.asyncio
    async def test_large_corpus_exact_search(self, search_engine_large):
        """Test exact search in large corpus."""
        results = await search_engine_large.search("test42", method=SearchMethod.EXACT)

        assert len(results) > 0
        assert results[0].word == "test42"

    @pytest.mark.asyncio
    async def test_large_corpus_prefix_performance(self, search_engine_large):
        """Test prefix search performance in large corpus."""
        import time

        start = time.perf_counter()
        results = await search_engine_large.search(
            "word", method=SearchMethod.PREFIX, max_results=200
        )
        elapsed = time.perf_counter() - start

        assert len(results) > 0
        assert elapsed < 1.0  # Should complete within 1 second

        # Should find many matches
        assert len(results) >= 100

    @pytest.mark.asyncio
    async def test_concurrent_searches_large(self, search_engine_large):
        """Test concurrent searches on large corpus."""
        queries = [f"test{i}" for i in range(10)]

        # Run concurrent searches
        results = await asyncio.gather(
            *[search_engine_large.search(q, method=SearchMethod.PREFIX) for q in queries]
        )

        # All should return results
        assert all(len(r) > 0 for r in results)


class TestSearchWithLiteratureCorpus:
    """Test search with literature corpus."""

    @pytest.mark.asyncio
    async def test_literature_word_search(self, search_engine_literature):
        """Test searching words from literature."""
        results = await search_engine_literature.search("quick")

        assert len(results) > 0
        assert results[0].word == "quick"

    @pytest.mark.asyncio
    async def test_literature_phrase_components(self, search_engine_literature):
        """Test finding components of phrases."""
        # Search for words that appear in "quick brown fox"
        for word in ["quick", "brown", "fox"]:
            results = await search_engine_literature.search(word)
            assert len(results) > 0
            assert results[0].word == word

    @pytest.mark.asyncio
    async def test_literature_fuzzy_search(self, search_engine_literature):
        """Test fuzzy search in literature corpus."""
        # Typo in "sample"
        results = await search_engine_literature.search("sampl", method=SearchMethod.FUZZY)

        assert len(results) > 0
        words = [r.word for r in results]
        assert "sample" in words


class TestSearchWithSemantic:
    """Test semantic search capabilities."""

    @pytest.mark.asyncio
    async def test_semantic_search_enabled(self, search_engine_with_semantic):
        """Test that semantic search can be enabled."""
        assert search_engine_with_semantic.index.semantic_enabled

        # Wait for semantic search to be ready
        if hasattr(search_engine_with_semantic, "await_semantic_ready"):
            await search_engine_with_semantic.await_semantic_ready()

        # Test real semantic search
        results = await search_engine_with_semantic.search("cat")
        assert isinstance(results, list)
        # Should find words in vocabulary
        if len(results) > 0:
            assert all(r.word in search_engine_with_semantic.corpus.vocabulary for r in results)


class TestSearchEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_special_characters(self, search_engine_small):
        """Test handling special characters."""
        # Should handle gracefully
        results = await search_engine_small.search("app!@#$le")
        # May or may not find results depending on normalization
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_unicode_search(self, search_engine_small):
        """Test Unicode character handling."""
        results = await search_engine_small.search("café")
        # Should handle Unicode gracefully
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_very_long_query(self, search_engine_small):
        """Test handling very long queries."""
        long_query = "a" * 500
        results = await search_engine_small.search(long_query)
        # Should handle without crashing
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_corpus_not_found(self, test_db):
        """Test handling when corpus doesn't exist."""
        with pytest.raises(ValueError, match="Corpus.*not found"):
            await Search.from_corpus(corpus_name="nonexistent_corpus")


class TestSearchInitialization:
    """Test search engine initialization."""

    @pytest.mark.asyncio
    async def test_from_corpus_initialization(self, language_corpus_small):
        """Test creating search engine from corpus."""
        engine = await Search.from_corpus(corpus_name=language_corpus_small.corpus_name)

        assert engine is not None
        assert engine.index is not None
        assert engine.index.corpus_name == language_corpus_small.corpus_name

        if hasattr(engine, "close"):
            await engine.close()

    @pytest.mark.asyncio
    async def test_search_index_creation(self, language_corpus_small):
        """Test search index is properly created."""
        from floridify.corpus.utils import get_vocabulary_hash

        engine = await Search.from_corpus(corpus_name=language_corpus_small.corpus_name)

        assert engine.index.vocabulary_hash == get_vocabulary_hash(language_corpus_small.vocabulary)
        assert engine.index.vocabulary_size == len(language_corpus_small.vocabulary)

        if hasattr(engine, "close"):
            await engine.close()
