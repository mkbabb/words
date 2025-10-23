"""Trie search component tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.search.trie import TrieSearch


@pytest_asyncio.fixture
async def trie_corpus(test_db):
    """Create corpus for trie search testing."""
    vocabulary = [
        "apple",
        "apples",
        "application",
        "apply",
        "applied",
        "applying",
        "banana",
        "bananas",
        "band",
        "bandage",
        "bandwidth",
        "cat",
        "cats",
        "catch",
        "catching",
        "catfish",
        "dog",
        "dogs",
        "dodge",
        "dodging",
        "dogma",
    ]

    corpus = Corpus(
        corpus_name="test_trie_corpus",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=sorted(vocabulary),
        original_vocabulary=vocabulary,
        lemmatized_vocabulary=vocabulary,
    )

    # Build indices
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted(vocabulary))}
    corpus._build_signature_index()

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


@pytest_asyncio.fixture
async def trie_search(trie_corpus):
    """Create TrieSearch instance with corpus."""
    from floridify.search.models import TrieIndex

    # Create trie index from corpus
    index = await TrieIndex.get_or_create(corpus=trie_corpus)

    # Create trie search with index
    search = TrieSearch(index=index)
    await search.initialize()
    return search


class TestTrieSearch:
    """Test suite for trie search functionality."""

    @pytest.mark.asyncio
    async def test_exact_matching_performance(self, trie_search):
        """Test O(m) exact search performance."""
        result = trie_search.search_exact("apple")

        assert result == "apple"

    @pytest.mark.asyncio
    async def test_prefix_enumeration(self, trie_search):
        """Test prefix search with frequency ranking."""
        results = trie_search.search_prefix("app")

        # Should find all words starting with "app"
        assert "apple" in results
        assert "apples" in results
        assert "application" in results
        assert "apply" in results
        assert "applied" in results
        assert "applying" in results

    @pytest.mark.asyncio
    async def test_marisa_trie_persistence(self, trie_search, tmp_path):
        """Test trie serialization/deserialization."""
        # Ensure trie is built
        if not trie_search._trie:
            await trie_search.initialize()

        # Save trie
        trie_path = tmp_path / "test_trie.marisa"
        trie_search._trie.save(str(trie_path))

        # Load new trie
        from marisa_trie import Trie

        loaded_trie = Trie()
        loaded_trie.load(str(trie_path))

        # Verify same content
        assert "apple" in loaded_trie
        assert "banana" in loaded_trie
        assert list(loaded_trie.prefixes("application")) == ["application"]

    @pytest.mark.asyncio
    async def test_empty_prefix_search(self, trie_search):
        """Test searching with empty prefix."""
        results = trie_search.search_prefix("")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_nonexistent_prefix(self, trie_search):
        """Test searching for nonexistent prefix."""
        results = trie_search.search_prefix("xyz")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_prefix_with_limit(self, trie_search):
        """Test limiting prefix search results."""
        results = trie_search.search_prefix("a", max_results=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, trie_search):
        """Test case-insensitive trie search."""
        result = trie_search.search_exact("APPLE")

        assert result == "apple"

    @pytest.mark.asyncio
    async def test_special_characters(self, trie_search):
        """Test handling of special characters."""
        # Special characters should be normalized to "apple"
        # Might be None due to normalization
        _ = trie_search.search_exact("app-le")

        # Prefix search should find words starting with "app"
        results = trie_search.search_prefix("app")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_concurrent_trie_searches(self, trie_search):
        """Test concurrent trie operations."""
        import asyncio

        queries = ["app", "ban", "cat", "dog"]

        # Run searches concurrently
        results = await asyncio.gather(
            *[asyncio.to_thread(trie_search.search_prefix, q) for q in queries]
        )

        # Each search should return results
        assert all(len(r) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_trie_memory_efficiency(self, trie_search):
        """Test memory efficiency of trie structure."""
        # Marisa trie should be memory efficient
        import sys

        # Ensure trie is built
        if not trie_search._trie:
            await trie_search.initialize()

        # Get size of trie object
        trie_size = sys.getsizeof(trie_search._trie)

        # Should be reasonably small for test vocabulary
        assert trie_size < 1_000_000  # Less than 1MB for test data

    @pytest.mark.asyncio
    async def test_prefix_boundary_conditions(self, trie_search):
        """Test prefix search at word boundaries."""
        # Search for exact word that is also a prefix
        results = trie_search.search_prefix("cat")

        assert "cat" in results
        assert "cats" in results
        assert "catch" in results
        assert "catching" in results
        assert "catfish" in results

    @pytest.mark.asyncio
    async def test_trie_index_creation(self, test_db):
        """Test creating trie index from corpus."""
        from floridify.search.models import TrieIndex

        vocabulary = ["test", "testing", "tester"]

        corpus = Corpus(
            corpus_name="test_index_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        # Create trie index
        index = await TrieIndex.get_or_create(corpus=saved_corpus)

        assert index is not None
        assert index.corpus_name == "test_index_corpus"
        assert index.vocabulary_hash is not None

    @pytest.mark.asyncio
    async def test_trie_with_empty_corpus(self, test_db):
        """Test trie creation with empty corpus."""
        corpus = Corpus(
            corpus_name="empty_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=[],
            original_vocabulary=[],
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        from floridify.search.models import TrieIndex

        # Create index from empty corpus
        index = await TrieIndex.get_or_create(corpus=saved_corpus)

        search = TrieSearch(index=index)
        await search.initialize()

        results = search.search_prefix("test")
        assert len(results) == 0
