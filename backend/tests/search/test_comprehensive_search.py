"""Comprehensive search tests with MongoDB and versioning.

Tests the complete search functionality including:
- MongoDB persistence of search indices
- Version management for search data
- Multi-method search cascade
- Index rebuilding on corpus changes
- Concurrent search operations
- Cache integration
"""

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from beanie import PydanticObjectId

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace, ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.search.core import Search
from floridify.search.fuzzy import FuzzySearch
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.search.trie import TrieSearch


@pytest.mark.asyncio
class TestSearchMongoDBIntegration:
    """Test search MongoDB persistence and operations."""

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    @pytest_asyncio.fixture
    async def sample_corpus(self):
        """Create sample corpus for testing."""
        return Corpus(
            corpus_name="search-test",
            language="en",
            vocabulary=["apple", "application", "apply", "banana", "band", "cherry"],
            original_vocabulary=["Apple", "Application", "Apply", "Banana", "Band", "Cherry"],
            vocabulary_to_index={
                "apple": 0,
                "application": 1,
                "apply": 2,
                "banana": 3,
                "band": 4,
                "cherry": 5,
            },
            unique_word_count=6,
            total_word_count=6,
            word_frequencies={
                "apple": 10,
                "application": 5,
                "apply": 8,
                "banana": 7,
                "band": 6,
                "cherry": 4,
            },
        )

    async def test_trie_index_persistence(self, test_db, versioned_manager, sample_corpus):
        """Test saving and loading TrieIndex from MongoDB."""
        # Create trie index
        trie_index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name=sample_corpus.corpus_name,
            vocabulary_hash="test_hash_123",
            trie_data=sorted(sample_corpus.vocabulary),  # Sorted for marisa-trie
            word_frequencies=sample_corpus.word_frequencies,
            original_vocabulary=sample_corpus.original_vocabulary,
            normalized_to_original={w: w.title() for w in sample_corpus.vocabulary},
            word_count=sample_corpus.unique_word_count,
            max_frequency=max(sample_corpus.word_frequencies.values()),
        )

        # Save as versioned data
        saved = await versioned_manager.save(
            resource_id=f"trie-{sample_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=trie_index.model_dump(),
            config=VersionConfig(version="1.0.0"),
        )

        assert saved.id is not None
        assert saved.resource_type == ResourceType.SEARCH_INDEX

        # Load from MongoDB
        loaded = await versioned_manager.get_latest(
            resource_id=f"trie-{sample_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
        )

        assert loaded is not None
        loaded_index = TrieIndex(**loaded.content)
        assert loaded_index.corpus_name == trie_index.corpus_name
        assert loaded_index.vocabulary_hash == trie_index.vocabulary_hash

    async def test_semantic_index_persistence(self, test_db, versioned_manager, sample_corpus):
        """Test saving and loading SemanticIndex from MongoDB."""
        import numpy as np

        # Create semantic index with mock embeddings
        embeddings = np.random.randn(len(sample_corpus.vocabulary), 384).astype(np.float32)

        semantic_index = SemanticIndex(
            corpus_id=PydanticObjectId(),
            corpus_name=sample_corpus.corpus_name,
            vocabulary_hash="semantic_hash_456",
            embeddings=embeddings.tolist(),  # Convert to list for storage
            vocabulary=sample_corpus.vocabulary,
            model_name="all-MiniLM-L6-v2",
            dimension=384,
            word_count=sample_corpus.unique_word_count,
        )

        # Save as versioned data
        saved = await versioned_manager.save(
            resource_id=f"semantic-{sample_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=semantic_index.model_dump(),
            config=VersionConfig(version="1.0.0"),
        )

        assert saved.id is not None

        # Load from MongoDB
        loaded = await versioned_manager.get_latest(
            resource_id=f"semantic-{sample_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
        )

        loaded_index = SemanticIndex(**loaded.content)
        assert loaded_index.model_name == semantic_index.model_name
        assert loaded_index.dimension == semantic_index.dimension
        assert len(loaded_index.embeddings) == len(semantic_index.embeddings)

    async def test_search_index_versioning(self, test_db, versioned_manager, sample_corpus):
        """Test version management for search indices."""
        resource_id = "search-index-v-test"

        # Create v1 with initial vocabulary
        v1_index = SearchIndex(
            corpus_id=PydanticObjectId(),
            corpus_name="version-test",
            vocabulary_hash="v1_hash",
            vocabulary=["word1", "word2"],
            version="1.0.0",
        )

        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=v1_index.model_dump(),
            config=VersionConfig(version="1.0.0"),
        )

        # Create v2 with expanded vocabulary
        v2_index = SearchIndex(
            corpus_id=PydanticObjectId(),
            corpus_name="version-test",
            vocabulary_hash="v2_hash",
            vocabulary=["word1", "word2", "word3", "word4"],
            version="2.0.0",
        )

        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=v2_index.model_dump(),
            config=VersionConfig(version="2.0.0"),
        )

        # Verify version chain
        assert v2.version_info.supersedes == v1.id

        # Load v1 (should not be latest)
        v1_loaded = await versioned_manager.get_by_id(v1.id)
        assert not v1_loaded.version_info.is_latest

        # Load latest (should be v2)
        latest = await versioned_manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
        )
        assert latest.id == v2.id

    async def test_index_rebuild_on_corpus_change(self, test_db, versioned_manager):
        """Test that indices rebuild when corpus changes."""
        corpus_id = "rebuild-test-corpus"
        index_id = f"index-{corpus_id}"

        # Save initial corpus version
        corpus_v1 = await versioned_manager.save(
            resource_id=corpus_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={
                "vocabulary": ["initial", "words"],
                "vocabulary_hash": "hash_v1",
            },
            config=VersionConfig(version="1.0.0"),
        )

        # Save corresponding index
        index_v1 = await versioned_manager.save(
            resource_id=index_id,
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content={
                "corpus_id": corpus_id,
                "vocabulary_hash": "hash_v1",
                "vocabulary": ["initial", "words"],
            },
            config=VersionConfig(version="1.0.0"),
            metadata={"corpus_version": "1.0.0"},
        )

        # Update corpus
        corpus_v2 = await versioned_manager.save(
            resource_id=corpus_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={
                "vocabulary": ["initial", "words", "new", "additions"],
                "vocabulary_hash": "hash_v2",
            },
            config=VersionConfig(version="2.0.0"),
        )

        # Rebuild index for new corpus
        index_v2 = await versioned_manager.save(
            resource_id=index_id,
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content={
                "corpus_id": corpus_id,
                "vocabulary_hash": "hash_v2",
                "vocabulary": ["initial", "words", "new", "additions"],
            },
            config=VersionConfig(version="2.0.0"),
            metadata={"corpus_version": "2.0.0"},
        )

        # Verify index was rebuilt with new vocabulary
        assert index_v2.content["vocabulary_hash"] == "hash_v2"
        assert len(index_v2.content["vocabulary"]) == 4
        assert index_v2.metadata["corpus_version"] == "2.0.0"

    async def test_concurrent_search_operations(self, test_db, sample_corpus):
        """Test concurrent search operations."""
        # Create search engines
        trie = TrieSearch(
            index=TrieIndex(
                corpus_id=PydanticObjectId(),
                corpus_name=sample_corpus.corpus_name,
                vocabulary_hash="test",
                trie_data=sorted(sample_corpus.vocabulary),
                word_frequencies=sample_corpus.word_frequencies,
                original_vocabulary=sample_corpus.original_vocabulary,
                normalized_to_original={w: w for w in sample_corpus.vocabulary},
                word_count=len(sample_corpus.vocabulary),
                max_frequency=10,
            )
        )

        fuzzy = FuzzySearch(min_score=0.5)

        async def search_operation(query: str, method: str):
            """Perform search operation."""
            if method == "trie":
                return trie.search_prefix(query)
            elif method == "fuzzy":
                return fuzzy.search(query, sample_corpus)

        # Run concurrent searches
        queries = [
            ("app", "trie"),
            ("ban", "trie"),
            ("aple", "fuzzy"),
            ("cheery", "fuzzy"),
        ] * 5  # Repeat for more concurrency

        tasks = [search_operation(q, m) for q, m in queries]
        results = await asyncio.gather(*tasks)

        # All searches should complete
        assert len(results) == len(queries)
        assert all(r is not None for r in results)

    async def test_search_cascade_with_persistence(self, test_db, versioned_manager, sample_corpus):
        """Test multi-method search cascade with persisted indices."""
        # Save trie index
        trie_index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name=sample_corpus.corpus_name,
            vocabulary_hash="cascade_test",
            trie_data=sorted(sample_corpus.vocabulary),
            word_frequencies=sample_corpus.word_frequencies,
            original_vocabulary=sample_corpus.original_vocabulary,
            normalized_to_original={w: w for w in sample_corpus.vocabulary},
            word_count=len(sample_corpus.vocabulary),
            max_frequency=10,
        )

        await versioned_manager.save(
            resource_id=f"cascade-trie-{sample_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=trie_index.model_dump(),
        )

        # Create search instance
        search = Search(
            corpus=sample_corpus,
            trie_search=TrieSearch(index=trie_index),
            fuzzy_search=FuzzySearch(min_score=0.5),
        )

        # Test cascade: exact -> fuzzy
        results = await search.search("aple")  # Typo should trigger fuzzy
        assert len(results) > 0
        assert any("apple" in str(r).lower() for r in results)

    async def test_search_statistics_tracking(self, test_db, versioned_manager):
        """Test tracking search statistics in MongoDB."""
        # Create search statistics document
        stats = {
            "timestamp": datetime.now(UTC).isoformat(),
            "queries": [
                {"query": "apple", "method": "exact", "results": 1, "latency_ms": 5},
                {"query": "ban", "method": "prefix", "results": 2, "latency_ms": 7},
                {"query": "cheery", "method": "fuzzy", "results": 1, "latency_ms": 15},
            ],
            "total_queries": 3,
            "average_latency_ms": 9,
            "methods_used": {"exact": 1, "prefix": 1, "fuzzy": 1},
        }

        # Save statistics
        saved = await versioned_manager.save(
            resource_id="search-stats-daily",
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=stats,
            metadata={"type": "statistics", "period": "daily"},
        )

        # Load and verify
        loaded = await versioned_manager.get_latest(
            resource_id="search-stats-daily",
            resource_type=ResourceType.SEARCH_INDEX,
        )

        assert loaded.content["total_queries"] == 3
        assert loaded.metadata["type"] == "statistics"

    async def test_search_cache_invalidation(self, test_db, versioned_manager):
        """Test that search cache invalidates on index updates."""
        resource_id = "cache-invalidation-test"

        # Save initial index
        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content={"vocabulary": ["word1", "word2"], "cached": True},
            config=VersionConfig(use_cache=True),
        )

        # Simulate cached search result
        cached_result = await versioned_manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
            config=VersionConfig(use_cache=True),
        )
        assert cached_result.id == v1.id

        # Update index (should invalidate cache)
        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content={"vocabulary": ["word1", "word2", "word3"], "cached": False},
            config=VersionConfig(increment_version=True),
        )

        # Get latest (should be v2, not cached v1)
        latest = await versioned_manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH_INDEX,
        )
        assert latest.id == v2.id
        assert len(latest.content["vocabulary"]) == 3


@pytest.mark.asyncio
class TestSearchIndexOptimization:
    """Test search index optimization and performance."""

    @pytest_asyncio.fixture
    async def large_corpus(self):
        """Create large corpus for performance testing."""
        # Generate large vocabulary
        vocabulary = [f"word_{i:05d}" for i in range(10000)]
        frequencies = {word: i % 100 + 1 for i, word in enumerate(vocabulary)}

        return Corpus(
            corpus_name="large-corpus",
            language="en",
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            vocabulary_to_index={w: i for i, w in enumerate(vocabulary)},
            word_frequencies=frequencies,
            unique_word_count=len(vocabulary),
            total_word_count=sum(frequencies.values()),
        )

    async def test_index_compression(self, test_db, versioned_manager, large_corpus):
        """Test index compression for large vocabularies."""
        # Create large index
        large_index = TrieIndex(
            corpus_id=PydanticObjectId(),
            corpus_name=large_corpus.corpus_name,
            vocabulary_hash="large_hash",
            trie_data=sorted(large_corpus.vocabulary),
            word_frequencies=large_corpus.word_frequencies,
            original_vocabulary=large_corpus.original_vocabulary,
            normalized_to_original={w: w for w in large_corpus.vocabulary},
            word_count=large_corpus.unique_word_count,
            max_frequency=100,
        )

        # Save with compression
        saved = await versioned_manager.save(
            resource_id=f"large-index-{large_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
            namespace=CacheNamespace.SEARCH,
            content=large_index.model_dump(),
            config=VersionConfig(compress=True),
        )

        # Verify compression occurred
        assert saved.storage_info.compressed
        assert saved.storage_info.compression_ratio > 0

        # Load and verify decompression
        loaded = await versioned_manager.get_latest(
            resource_id=f"large-index-{large_corpus.corpus_name}",
            resource_type=ResourceType.SEARCH_INDEX,
        )

        loaded_index = TrieIndex(**loaded.content)
        assert len(loaded_index.trie_data) == len(large_index.trie_data)

    async def test_batch_index_operations(self, test_db, versioned_manager):
        """Test batch operations on search indices."""
        # Create multiple indices
        indices = []
        for i in range(10):
            index = SearchIndex(
                corpus_id=PydanticObjectId(),
                corpus_name=f"batch-corpus-{i}",
                vocabulary_hash=f"hash_{i}",
                vocabulary=[f"word_{i}_{j}" for j in range(10)],
            )
            indices.append(index)

        # Batch save
        save_tasks = [
            versioned_manager.save(
                resource_id=f"batch-index-{i}",
                resource_type=ResourceType.SEARCH_INDEX,
                namespace=CacheNamespace.SEARCH,
                content=index.model_dump(),
            )
            for i, index in enumerate(indices)
        ]

        saved = await asyncio.gather(*save_tasks)
        assert len(saved) == 10

        # Batch load
        load_tasks = [
            versioned_manager.get_latest(
                resource_id=f"batch-index-{i}",
                resource_type=ResourceType.SEARCH_INDEX,
            )
            for i in range(10)
        ]

        loaded = await asyncio.gather(*load_tasks)
        assert len(loaded) == 10
        assert all(l is not None for l in loaded)
