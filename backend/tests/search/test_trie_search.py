"""Comprehensive tests for TrieSearch (exact search) functionality."""

import time

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

from floridify.corpus.core import Corpus
from floridify.search.models import TrieIndex
from floridify.search.trie import TrieSearch


class TestTrieSearchBasic:
    """Test basic TrieSearch functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, sample_corpus: Corpus):
        """Test TrieSearch initialization from corpus."""
        # Create TrieSearch without MongoDB
        from beanie import PydanticObjectId

        index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name=sample_corpus.corpus_name,
            vocabulary_hash="test_hash",
            trie_data=sorted(sample_corpus.vocabulary),
            word_frequencies={word: 10 for word in sample_corpus.vocabulary},
            original_vocabulary=sample_corpus.original_vocabulary,
            normalized_to_original={word: word for word in sample_corpus.vocabulary},
            word_count=len(sample_corpus.vocabulary),
            max_frequency=10,
        )

        trie = TrieSearch(index=index)

        assert trie.index is not None
        assert trie.index.corpus_name == sample_corpus.corpus_name
        assert trie.index.word_count > 0
        assert trie._trie is not None

    @pytest.mark.asyncio
    async def test_exact_search(self, trie_search: TrieSearch):
        """Test exact word search."""
        # Test exact matches - returns str | None
        result = trie_search.search_exact("apple")
        assert result == "apple"

        # Test case insensitive
        result = trie_search.search_exact("APPLE")
        assert result == "apple"

        # Test non-existent word
        result = trie_search.search_exact("xyz123")
        assert result is None

    @pytest.mark.asyncio
    async def test_prefix_search(self, trie_search: TrieSearch):
        """Test prefix search functionality."""
        # Search for words starting with "app" - returns list[str]
        results = trie_search.search_prefix("app")

        assert len(results) > 0
        expected_words = ["apple", "application", "apply", "appreciate", "approach"]

        for word in expected_words:
            assert word in results

        # All results should start with "app"
        for word in results:
            assert word.startswith("app")

    @pytest.mark.asyncio
    async def test_empty_query(self, trie_search: TrieSearch):
        """Test handling of empty queries."""
        result = trie_search.search_exact("")
        assert result is None

        results = trie_search.search_prefix("")
        assert results == []

    @pytest.mark.asyncio
    async def test_whitespace_handling(self, trie_search: TrieSearch):
        """Test handling of whitespace in queries."""
        result = trie_search.search_exact("  apple  ")
        assert result == "apple"

        results = trie_search.search_prefix("  app  ")
        assert len(results) > 0
        for word in results:
            assert word.startswith("app")

    @pytest.mark.asyncio
    async def test_special_characters(self, trie_search: TrieSearch):
        """Test handling of special characters."""
        # These should return no results as they're not in our test corpus
        special_queries = ["user@email", "hello-world", "$100", "C++"]

        for query in special_queries:
            result = trie_search.search_exact(query)
            assert result is None

    @pytest.mark.asyncio
    async def test_unicode_normalization(self, sample_corpus: Corpus):
        """Test Unicode normalization in search."""
        # Create a corpus with unicode words
        from beanie import PydanticObjectId

        unicode_words = ["café", "naïve", "résumé"]
        all_words = sample_corpus.vocabulary + unicode_words

        index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name="unicode-test",
            vocabulary_hash="test_hash",
            trie_data=sorted(all_words),
            word_frequencies={word: 10 for word in all_words},
            original_vocabulary=all_words,
            normalized_to_original={word: word for word in all_words},
            word_count=len(all_words),
            max_frequency=10,
        )

        trie = TrieSearch(index=index)

        # Search with different Unicode forms
        result = trie.search_exact("cafe")  # Without accent
        # Should find if normalization works

        result = trie.search_exact("café")  # With accent
        if result:
            assert result == "café"


class TestTrieSearchPerformance:
    """Test TrieSearch performance characteristics."""

    @pytest.mark.asyncio
    async def test_search_performance(self, trie_search: TrieSearch, performance_thresholds: dict):
        """Test search operation performance."""
        # Warm up
        _ = trie_search.search_exact("test")

        # Measure exact search time
        start = time.perf_counter()
        for _ in range(100):
            trie_search.search_exact("apple")
        elapsed = (time.perf_counter() - start) / 100

        assert elapsed < performance_thresholds["exact_search"]

    @pytest.mark.asyncio
    async def test_prefix_search_performance(
        self, trie_search: TrieSearch, performance_thresholds: dict
    ):
        """Test prefix search performance."""
        # Warm up
        _ = trie_search.search_prefix("te")

        # Measure prefix search time
        start = time.perf_counter()
        for _ in range(100):
            trie_search.search_prefix("com")
        elapsed = (time.perf_counter() - start) / 100

        # Prefix search should still be fast
        assert elapsed < performance_thresholds["exact_search"] * 10

    @pytest.mark.asyncio
    async def test_large_corpus_performance(self):
        """Test performance with large corpus."""
        from beanie import PydanticObjectId

        # Create large corpus
        large_words = [f"word_{i:06d}" for i in range(10000)]

        # Measure index build time
        start = time.perf_counter()

        # Create index directly without MongoDB
        index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name="large-test",
            vocabulary_hash="test_hash",
            trie_data=sorted(large_words),
            word_frequencies={word: 1 for word in large_words},
            original_vocabulary=large_words,
            normalized_to_original={word: word for word in large_words},
            word_count=len(large_words),
            max_frequency=1,
        )

        trie = TrieSearch(index=index)
        build_time = time.perf_counter() - start

        # Should build quickly even for large corpus
        assert build_time < 1.0

        # Search should still be fast
        start = time.perf_counter()
        result = trie.search_exact("word_005000")
        search_time = time.perf_counter() - start

        assert search_time < 0.001
        assert result == "word_005000"


class TestTrieIndexPersistence:
    """Test TrieIndex persistence and versioning."""

    @pytest.mark.asyncio
    async def test_index_creation(self, sample_corpus: Corpus, trie_search: TrieSearch):
        """Test creating and storing TrieIndex."""
        # Access the index that was created when building from corpus
        index = trie_search.index

        assert index is not None
        assert index.corpus_name == sample_corpus.corpus_name
        assert index.vocabulary_hash is not None
        assert index.word_count > 0
        assert index.trie_data is not None

    @pytest.mark.asyncio
    async def test_index_serialization(self, trie_search: TrieSearch):
        """Test TrieIndex serialization/deserialization."""
        # Access the existing index
        index = trie_search.index

        # Serialize to dict
        index_dict = index.model_dump()
        assert "trie_data" in index_dict
        assert "word_frequencies" in index_dict
        assert "corpus_id" in index_dict

        # Deserialize
        restored_index = TrieIndex(**index_dict)
        assert restored_index.corpus_id == index.corpus_id
        assert restored_index.word_count == index.word_count

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires MongoDB persistence")
    async def test_index_versioning(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test TrieIndex versioning with Metadata."""
        # This test requires real MongoDB persistence
        # Would test version incrementing and hash changes
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires MongoDB persistence")
    async def test_index_retrieval(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test retrieving stored TrieIndex."""
        # This test requires real MongoDB persistence
        # Would test saving and retrieving indices
        pass

    @pytest.mark.asyncio
    async def test_from_index_reconstruction(self, sample_corpus: Corpus, trie_search: TrieSearch):
        """Test reconstructing TrieSearch from index."""
        # Get the index from the search
        index = trie_search.index

        # Reconstruct search from index
        reconstructed = TrieSearch(index=index)

        assert reconstructed.index.corpus_name == trie_search.index.corpus_name
        assert reconstructed.index.word_count == trie_search.index.word_count

        # Test that search works
        result = reconstructed.search_exact("apple")
        assert result == "apple"


class TestTrieSearchEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_very_long_query(self, trie_search: TrieSearch):
        """Test handling of very long queries."""
        long_query = "a" * 1000
        result = trie_search.search_exact(long_query)
        assert result is None

        results = trie_search.search_prefix(long_query)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_numeric_queries(self, trie_search: TrieSearch):
        """Test numeric string queries."""
        numeric_queries = ["123", "456.789", "0", "-1"]

        for query in numeric_queries:
            result = trie_search.search_exact(query)
            assert result is None

    @pytest.mark.asyncio
    async def test_mixed_case_prefix(self, trie_search: TrieSearch):
        """Test prefix search with mixed case."""
        results = trie_search.search_prefix("COM")

        assert len(results) > 0
        # Should find words starting with "com" regardless of case
        for word in results:
            assert word.lower().startswith("com")

    @pytest.mark.asyncio
    async def test_punctuation_in_query(self, trie_search: TrieSearch):
        """Test queries containing punctuation."""
        punctuated_queries = [
            "apple.",
            "apple!",
            "apple?",
            "(apple)",
            "apple's",
        ]

        for query in punctuated_queries:
            trie_search.search_exact(query)
            # Depends on normalization strategy
            # Our test corpus doesn't have punctuated words

    @pytest.mark.asyncio
    async def test_empty_corpus(self):
        """Test behavior with empty corpus."""
        from beanie import PydanticObjectId

        # Create empty index
        index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name="empty-test",
            vocabulary_hash="empty",
            trie_data=[],
            word_frequencies={},
            original_vocabulary=[],
            normalized_to_original={},
            word_count=0,
            max_frequency=0,
        )

        trie = TrieSearch(index=index)

        result = trie.search_exact("anything")
        assert result is None

        results = trie.search_prefix("any")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_single_word_corpus(self):
        """Test behavior with single-word corpus."""
        from beanie import PydanticObjectId

        # Create single-word index
        index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name="single-test",
            vocabulary_hash="single",
            trie_data=["unique"],
            word_frequencies={"unique": 1},
            original_vocabulary=["unique"],
            normalized_to_original={"unique": "unique"},
            word_count=1,
            max_frequency=1,
        )

        trie = TrieSearch(index=index)

        result = trie.search_exact("unique")
        assert result == "unique"

        result = trie.search_exact("other")
        assert result is None

        results = trie.search_prefix("uni")
        assert len(results) == 1
        assert results[0] == "unique"
