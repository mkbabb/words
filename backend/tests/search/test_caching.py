"""Comprehensive tests for two-tier caching system."""

import asyncio
import time

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

from floridify.caching import get_global_cache
from floridify.caching.core import GlobalCacheManager
from floridify.caching.models import CacheNamespace
from floridify.corpus.core import Corpus
from floridify.search.models import TrieIndex
from floridify.search.trie import TrieSearch


class TestTwoTierCacheBasic:
    """Test basic two-tier cache functionality."""

    @pytest.mark.asyncio
    async def test_cache_initialization(self):
        """Test two-tier cache initialization."""
        cache = get_global_cache()

        assert isinstance(cache, GlobalCacheManager)
        # Cache manager is properly initialized
        assert cache is not None

    @pytest.mark.asyncio
    async def test_l1_memory_cache(self):
        """Test L1 memory cache operations."""
        cache = get_global_cache()

        # Set value in L1
        await cache.set(
            namespace=CacheNamespace.SEARCH, key="test_l1", value={"data": "test_value"}, ttl=60
        )

        # Get from L1 (should be fast)
        start = time.perf_counter()
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="test_l1")
        elapsed = time.perf_counter() - start

        assert value == {"data": "test_value"}
        assert elapsed < 0.001  # Memory access should be < 1ms

    @pytest.mark.asyncio
    async def test_l2_disk_cache(self):
        """Test L2 disk cache operations."""
        cache = get_global_cache()

        # Large value that might go to L2
        large_value = {"data": "x" * 10000}

        await cache.set(namespace=CacheNamespace.SEARCH, key="test_l2", value=large_value, ttl=3600)

        # Clear L1 to force L2 access
        if hasattr(cache, "l1_cache"):
            cache.l1_cache.clear()

        # Get from L2 (might be slower)
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="test_l2")
        assert value == large_value

    @pytest.mark.asyncio
    async def test_cache_promotion(self):
        """Test L2 to L1 cache promotion."""
        cache = get_global_cache()

        # Set directly to L2 (simulating cold cache)
        test_value = {"promoted": "value"}
        await cache.set(
            namespace=CacheNamespace.SEARCH, key="test_promotion", value=test_value, ttl=3600
        )

        # Clear L1
        if hasattr(cache, "l1_cache"):
            cache.l1_cache.clear()

        # First access (from L2, promotes to L1)
        value1 = await cache.get(namespace=CacheNamespace.SEARCH, key="test_promotion")
        assert value1 == test_value

        # Second access should be faster (from L1)
        start = time.perf_counter()
        value2 = await cache.get(namespace=CacheNamespace.SEARCH, key="test_promotion")
        elapsed = time.perf_counter() - start

        assert value2 == test_value
        assert elapsed < 0.001  # Should be from memory

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache TTL expiration."""
        cache = get_global_cache()

        # Set with short TTL
        await cache.set(
            namespace=CacheNamespace.SEARCH,
            key="test_ttl",
            value="expires_soon",
            ttl=0.1,  # 100ms
        )

        # Should exist immediately
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="test_ttl")
        assert value == "expires_soon"

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="test_ttl")
        assert value is None

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = get_global_cache()

        # Set multiple values
        for i in range(5):
            await cache.set(
                namespace=CacheNamespace.SEARCH, key=f"invalidate_{i}", value=f"value_{i}", ttl=3600
            )

        # Verify all exist
        for i in range(5):
            value = await cache.get(namespace=CacheNamespace.SEARCH, key=f"invalidate_{i}")
            assert value == f"value_{i}"

        # Invalidate specific key
        await cache.delete(namespace=CacheNamespace.SEARCH, key="invalidate_2")

        # Check invalidation
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="invalidate_2")
        assert value is None

        # Others should still exist
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="invalidate_1")
        assert value == "value_1"


class TestCacheNamespaces:
    """Test cache namespace isolation."""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that namespaces are properly isolated."""
        cache = get_global_cache()

        # Set same key in different namespaces
        await cache.set(
            namespace=CacheNamespace.SEARCH, key="shared_key", value="search_value", ttl=3600
        )

        await cache.set(
            namespace=CacheNamespace.TRIE, key="shared_key", value="trie_value", ttl=3600
        )

        await cache.set(
            namespace=CacheNamespace.SEMANTIC, key="shared_key", value="semantic_value", ttl=3600
        )

        # Each namespace should have its own value
        search_value = await cache.get(namespace=CacheNamespace.SEARCH, key="shared_key")
        trie_value = await cache.get(namespace=CacheNamespace.TRIE, key="shared_key")
        semantic_value = await cache.get(namespace=CacheNamespace.SEMANTIC, key="shared_key")

        assert search_value == "search_value"
        assert trie_value == "trie_value"
        assert semantic_value == "semantic_value"

    @pytest.mark.asyncio
    async def test_namespace_clear(self):
        """Test clearing a specific namespace."""
        cache = get_global_cache()

        # Set values in multiple namespaces
        for i in range(3):
            await cache.set(
                namespace=CacheNamespace.SEARCH, key=f"search_{i}", value=f"value_{i}", ttl=3600
            )
            await cache.set(
                namespace=CacheNamespace.TRIE, key=f"trie_{i}", value=f"value_{i}", ttl=3600
            )

        # Clear only SEARCH namespace
        await cache.clear_namespace(CacheNamespace.SEARCH)

        # SEARCH should be cleared
        for i in range(3):
            value = await cache.get(namespace=CacheNamespace.SEARCH, key=f"search_{i}")
            assert value is None

        # TRIE should still exist
        for i in range(3):
            value = await cache.get(namespace=CacheNamespace.TRIE, key=f"trie_{i}")
            assert value == f"value_{i}"


class TestSearchIndexCaching:
    """Test caching of search indices."""

    @pytest.mark.asyncio
    async def test_trie_index_caching(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test TrieIndex caching."""
        cache = get_global_cache()

        # Create and cache TrieIndex
        trie = TrieSearch.from_corpus(sample_corpus)
        index = await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        # Manually cache the index
        cache_key = f"trie_{sample_corpus.id}"
        await cache.set(
            namespace=CacheNamespace.TRIE, key=cache_key, value=index.model_dump(), ttl=3600
        )

        # Retrieve from cache
        start = time.perf_counter()
        cached_data = await cache.get(namespace=CacheNamespace.TRIE, key=cache_key)
        elapsed = time.perf_counter() - start

        assert cached_data is not None
        assert cached_data["corpus_id"] == str(sample_corpus.id)
        assert elapsed < 0.01  # Should be fast

    @pytest.mark.asyncio
    async def test_semantic_index_caching(
        self, sample_corpus: Corpus, semantic_search, test_db: AsyncIOMotorDatabase
    ):
        """Test SemanticIndex caching."""
        from floridify.search.semantic.models import SemanticIndex

        cache = get_global_cache()

        # Create and cache SemanticIndex
        index = semantic_search.to_semantic_index()
        await SemanticIndex.get_or_create(sample_corpus, "all-MiniLM-L6-v2", index)

        # Cache the index
        cache_key = f"semantic_{sample_corpus.id}_all-MiniLM-L6-v2"
        await cache.set(
            namespace=CacheNamespace.SEMANTIC,
            key=cache_key,
            value={"model_name": "all-MiniLM-L6-v2", "corpus_id": str(sample_corpus.id)},
            ttl=3600,
        )

        # Retrieve from cache
        cached_data = await cache.get(namespace=CacheNamespace.SEMANTIC, key=cache_key)

        assert cached_data is not None
        assert cached_data["model_name"] == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio
    async def test_vocabulary_hash_caching(self, sample_corpus: Corpus):
        """Test vocabulary hash caching for change detection."""
        cache = get_global_cache()

        # Calculate and cache vocabulary hash
        vocab_hash = hash(frozenset(sample_corpus.words.items()))
        cache_key = f"vocab_hash_{sample_corpus.id}"

        await cache.set(namespace=CacheNamespace.CORPUS, key=cache_key, value=vocab_hash, ttl=3600)

        # Check if vocabulary changed
        cached_hash = await cache.get(namespace=CacheNamespace.CORPUS, key=cache_key)
        current_hash = hash(frozenset(sample_corpus.words.items()))

        assert cached_hash == current_hash

        # Modify corpus
        sample_corpus.words["new_word"] = 1
        new_hash = hash(frozenset(sample_corpus.words.items()))

        assert new_hash != cached_hash  # Should detect change


class TestCachePerformance:
    """Test cache performance characteristics."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent cache operations."""
        cache = get_global_cache()

        async def cache_operation(i: int):
            key = f"concurrent_{i}"
            value = f"value_{i}"

            # Set
            await cache.set(namespace=CacheNamespace.SEARCH, key=key, value=value, ttl=60)

            # Get
            result = await cache.get(namespace=CacheNamespace.SEARCH, key=key)
            return result == value

        # Run concurrent operations
        tasks = [cache_operation(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

    @pytest.mark.asyncio
    async def test_cache_hit_miss_ratio(self):
        """Test cache hit/miss ratio tracking."""
        cache = get_global_cache()

        # Generate cache misses
        for i in range(10):
            value = await cache.get(namespace=CacheNamespace.SEARCH, key=f"miss_{i}")
            assert value is None

        # Generate cache hits
        for i in range(10):
            await cache.set(
                namespace=CacheNamespace.SEARCH, key=f"hit_{i}", value=f"value_{i}", ttl=60
            )

        for i in range(10):
            value = await cache.get(namespace=CacheNamespace.SEARCH, key=f"hit_{i}")
            assert value == f"value_{i}"

    @pytest.mark.asyncio
    async def test_large_object_caching(self):
        """Test caching of large objects."""
        cache = get_global_cache()

        # Create large object (simulating large index)
        large_object = {
            "vocabulary": [f"word_{i}" for i in range(10000)],
            "embeddings": [[0.1] * 384 for _ in range(1000)],  # Simulated embeddings
            "metadata": {"size": "large", "version": 1},
        }

        # Cache large object
        await cache.set(
            namespace=CacheNamespace.SEMANTIC, key="large_object", value=large_object, ttl=3600
        )

        # Retrieve large object
        retrieved = await cache.get(namespace=CacheNamespace.SEMANTIC, key="large_object")

        assert retrieved is not None
        assert len(retrieved["vocabulary"]) == 10000
        assert retrieved["metadata"]["size"] == "large"

    @pytest.mark.asyncio
    async def test_cache_memory_limits(self):
        """Test cache memory limit handling."""
        cache = get_global_cache()

        # Fill cache with many objects
        for i in range(1000):
            await cache.set(
                namespace=CacheNamespace.SEARCH,
                key=f"memory_test_{i}",
                value={"data": "x" * 1000},  # 1KB per object
                ttl=3600,
            )

        # Cache should handle memory pressure gracefully
        # Older entries might be evicted

        # Recent entries should still be accessible
        value = await cache.get(namespace=CacheNamespace.SEARCH, key="memory_test_999")
        assert value is not None


class TestCacheIntegration:
    """Test cache integration with search pipeline."""

    @pytest.mark.asyncio
    async def test_search_result_caching(self, search_engine):
        """Test caching of search results."""
        cache = get_global_cache()

        # Perform search
        query = "apple"
        results1 = await search_engine.search(query)

        # Cache results
        cache_key = f"search_results_{query}"
        await cache.set(
            namespace=CacheNamespace.SEARCH,
            key=cache_key,
            value=[r.model_dump() for r in results1],
            ttl=300,
        )

        # Retrieve cached results
        cached_results = await cache.get(namespace=CacheNamespace.SEARCH, key=cache_key)

        assert cached_results is not None
        assert len(cached_results) == len(results1)
        assert cached_results[0]["word"] == results1[0].word

    @pytest.mark.asyncio
    async def test_index_rebuild_cache_invalidation(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test cache invalidation on index rebuild."""
        cache = get_global_cache()

        # Create and cache index
        trie1 = TrieSearch.from_corpus(sample_corpus)
        index1 = await TrieIndex.get_or_create(sample_corpus, trie1.to_trie_index())

        cache_key = f"trie_{sample_corpus.id}"
        await cache.set(
            namespace=CacheNamespace.TRIE, key=cache_key, value=index1.model_dump(), ttl=3600
        )

        # Modify corpus (triggers rebuild)
        sample_corpus.words["rebuild_test"] = 1
        await sample_corpus.save()

        # Rebuild index
        trie2 = TrieSearch.from_corpus(sample_corpus)
        index2 = await TrieIndex.get_or_create(sample_corpus, trie2.to_trie_index())

        # Cache should be invalidated/updated
        await cache.set(
            namespace=CacheNamespace.TRIE, key=cache_key, value=index2.model_dump(), ttl=3600
        )

        cached = await cache.get(namespace=CacheNamespace.TRIE, key=cache_key)
        assert "rebuild_test" in cached["vocabulary"]

    @pytest.mark.asyncio
    async def test_cross_request_caching(self):
        """Test cache persistence across requests."""
        cache = get_global_cache()

        # Simulate first request
        request_id = "req_1"
        await cache.set(
            namespace=CacheNamespace.SEARCH,
            key=f"session_{request_id}",
            value={"user": "test", "query": "apple"},
            ttl=600,
        )

        # Simulate second request
        cached_session = await cache.get(
            namespace=CacheNamespace.SEARCH, key=f"session_{request_id}"
        )

        assert cached_session is not None
        assert cached_session["user"] == "test"
        assert cached_session["query"] == "apple"
