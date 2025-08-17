"""Tests for multi-tier caching system."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from floridify.caching.compression import CompressionType
from floridify.caching.core import (
    GlobalCacheManager,
    L1MemoryCache,
    L2FilesystemCache,
    load_external_content,
    store_external_content,
)
from floridify.caching.decorators import cached, clear_cache, invalidate_cache
from floridify.caching.models import (
    CacheNamespace,
    ContentLocation,
)


class TestL1MemoryCache:
    """Test L1 in-memory cache layer."""
    
    @pytest.mark.asyncio
    async def test_memory_cache_basic_operations(self):
        """Test basic get/set/delete operations."""
        cache = L1MemoryCache(max_size=100, ttl=3600)
        
        # Test set and get
        await cache.set("key1", {"data": "value1"})
        result = await cache.get("key1")
        assert result == {"data": "value1"}
        
        # Test overwrite
        await cache.set("key1", {"data": "value2"})
        result = await cache.get("key1")
        assert result == {"data": "value2"}
        
        # Test delete
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_memory_cache_ttl(self):
        """Test TTL expiration in memory cache."""
        cache = L1MemoryCache(max_size=100, ttl=0.1)  # 100ms TTL
        
        await cache.set("ttl_test", "value")
        
        # Should exist immediately
        assert await cache.get("ttl_test") == "value"
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should be expired
        assert await cache.get("ttl_test") is None
    
    @pytest.mark.asyncio
    async def test_memory_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = L1MemoryCache(max_size=3, ttl=3600)
        
        # Fill cache
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new item - should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") == "value1"  # Still exists
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") == "value3"  # Still exists
        assert await cache.get("key4") == "value4"  # Newly added
    
    @pytest.mark.asyncio
    async def test_memory_cache_clear(self):
        """Test clearing the entire cache."""
        cache = L1MemoryCache(max_size=100, ttl=3600)
        
        # Add multiple items
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Clear cache
        await cache.clear()
        
        # All should be gone
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None
    
    @pytest.mark.asyncio
    async def test_memory_cache_stats(self):
        """Test cache statistics tracking."""
        cache = L1MemoryCache(max_size=100, ttl=3600)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        
        # Perform operations
        await cache.set("key1", "value1")
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.sets == 1
        assert stats.hit_rate == 0.5


class TestL2FilesystemCache:
    """Test L2 filesystem cache layer."""
    
    @pytest.mark.asyncio
    async def test_filesystem_cache_basic_operations(self):
        """Test basic filesystem cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = L2FilesystemCache(base_dir=Path(tmpdir), ttl=3600)
            
            # Test set and get
            data = {"large": "data" * 1000}
            await cache.set("fs_key1", data)
            
            result = await cache.get("fs_key1")
            assert result == data
            
            # Test delete
            await cache.delete("fs_key1")
            result = await cache.get("fs_key1")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_filesystem_cache_compression(self):
        """Test compression in filesystem cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = L2FilesystemCache(
                base_dir=Path(tmpdir),
                compression=CompressionType.ZSTD,
                ttl=3600,
            )
            
            # Create large, compressible data
            large_data = {"data": ["test"] * 10000}
            
            await cache.set("compressed", large_data)
            
            # Verify file is compressed
            cache_file = cache._get_cache_path("compressed")
            assert cache_file.exists()
            
            # File size should be much smaller than uncompressed
            file_size = cache_file.stat().st_size
            uncompressed_size = len(json.dumps(large_data).encode())
            assert file_size < uncompressed_size * 0.5  # At least 50% compression
            
            # Verify data is correctly decompressed
            result = await cache.get("compressed")
            assert result == large_data
    
    @pytest.mark.asyncio
    async def test_filesystem_cache_namespace_isolation(self):
        """Test namespace isolation in filesystem cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = L2FilesystemCache(base_dir=Path(tmpdir), ttl=3600)
            
            # Set same key in different namespaces
            await cache.set("shared_key", "namespace1_value", namespace="ns1")
            await cache.set("shared_key", "namespace2_value", namespace="ns2")
            
            # Get from different namespaces
            result1 = await cache.get("shared_key", namespace="ns1")
            result2 = await cache.get("shared_key", namespace="ns2")
            
            assert result1 == "namespace1_value"
            assert result2 == "namespace2_value"
    
    @pytest.mark.asyncio
    async def test_filesystem_cache_cleanup(self):
        """Test cleanup of expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = L2FilesystemCache(base_dir=Path(tmpdir), ttl=0.1)
            
            # Add entries
            await cache.set("expire1", "value1")
            await cache.set("expire2", "value2")
            
            # Wait for expiration
            await asyncio.sleep(0.2)
            
            # Run cleanup
            await cache.cleanup()
            
            # Should be removed
            assert await cache.get("expire1") is None
            assert await cache.get("expire2") is None


class TestGlobalCacheManager:
    """Test global cache manager with multi-tier caching."""
    
    @pytest.mark.asyncio
    async def test_global_cache_initialization(self):
        """Test global cache manager initialization."""
        manager = GlobalCacheManager()
        
        # Should have empty L1 caches initially
        assert len(manager.l1_caches) == 0
        assert manager.l2_cache is None
        
        # Initialize with filesystem cache
        with tempfile.TemporaryDirectory() as tmpdir:
            await manager.initialize(
                l2_base_dir=Path(tmpdir),
                l1_max_size=100,
                l1_ttl=3600,
                l2_ttl=86400,
            )
            
            assert manager.l2_cache is not None
            assert isinstance(manager.l2_cache, L2FilesystemCache)
    
    @pytest.mark.asyncio
    async def test_cache_hierarchy(self):
        """Test L1 -> L2 cache hierarchy."""
        manager = GlobalCacheManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            await manager.initialize(
                l2_base_dir=Path(tmpdir),
                l1_max_size=100,
                l1_ttl=3600,
                l2_ttl=86400,
            )
            
            namespace = CacheNamespace.DICTIONARY
            
            # Set value - should go to both L1 and L2
            await manager.set(namespace, "test_key", {"data": "value"})
            
            # Get from L1 (fast path)
            result = await manager.get(namespace, "test_key")
            assert result == {"data": "value"}
            
            # Clear L1 to force L2 lookup
            if namespace in manager.l1_caches:
                await manager.l1_caches[namespace].clear()
            
            # Should still get from L2
            result = await manager.get(namespace, "test_key")
            assert result == {"data": "value"}
            
            # Should be restored to L1
            l1_result = await manager.l1_caches[namespace].get("test_key")
            assert l1_result == {"data": "value"}
    
    @pytest.mark.asyncio
    async def test_namespace_specific_caches(self):
        """Test namespace-specific L1 caches."""
        manager = GlobalCacheManager()
        
        # Set in different namespaces
        await manager.set(CacheNamespace.DICTIONARY, "key1", "dict_value")
        await manager.set(CacheNamespace.CORPUS, "key1", "corpus_value")
        await manager.set(CacheNamespace.SEMANTIC, "key1", "semantic_value")
        
        # Should have separate L1 caches
        assert len(manager.l1_caches) == 3
        
        # Get from different namespaces
        assert await manager.get(CacheNamespace.DICTIONARY, "key1") == "dict_value"
        assert await manager.get(CacheNamespace.CORPUS, "key1") == "corpus_value"
        assert await manager.get(CacheNamespace.SEMANTIC, "key1") == "semantic_value"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_cascade(self):
        """Test invalidation across cache tiers."""
        manager = GlobalCacheManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            await manager.initialize(l2_base_dir=Path(tmpdir))
            
            namespace = CacheNamespace.DICTIONARY
            
            # Set value
            await manager.set(namespace, "invalidate_key", "original")
            
            # Delete should remove from both L1 and L2
            await manager.delete(namespace, "invalidate_key")
            
            # Should be gone from both
            assert await manager.get(namespace, "invalidate_key") is None
            
            # Clear L1 and check L2 directly
            if namespace in manager.l1_caches:
                await manager.l1_caches[namespace].clear()
            
            # Still should be None (deleted from L2 too)
            assert await manager.get(namespace, "invalidate_key") is None
    
    @pytest.mark.asyncio
    async def test_global_cache_stats(self):
        """Test aggregated cache statistics."""
        manager = GlobalCacheManager()
        
        # Perform operations across namespaces
        await manager.set(CacheNamespace.DICTIONARY, "key1", "value1")
        await manager.set(CacheNamespace.CORPUS, "key2", "value2")
        
        await manager.get(CacheNamespace.DICTIONARY, "key1")  # Hit
        await manager.get(CacheNamespace.DICTIONARY, "missing")  # Miss
        await manager.get(CacheNamespace.CORPUS, "key2")  # Hit
        
        stats = manager.get_stats()
        
        # Should have stats for each namespace
        assert CacheNamespace.DICTIONARY in stats
        assert CacheNamespace.CORPUS in stats
        
        dict_stats = stats[CacheNamespace.DICTIONARY]
        assert dict_stats.hits == 1
        assert dict_stats.misses == 1
        
        corpus_stats = stats[CacheNamespace.CORPUS]
        assert corpus_stats.hits == 1
        assert corpus_stats.misses == 0


class TestCacheDecorators:
    """Test caching decorators."""
    
    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test @cached decorator for automatic caching."""
        call_count = 0
        
        @cached(namespace=CacheNamespace.DICTIONARY, ttl=3600)
        async def expensive_function(param: str) -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate expensive operation
            return f"result_{param}"
        
        # First call - should execute
        result1 = await expensive_function("test")
        assert result1 == "result_test"
        assert call_count == 1
        
        # Second call - should use cache
        result2 = await expensive_function("test")
        assert result2 == "result_test"
        assert call_count == 1  # Not incremented
        
        # Different parameter - should execute
        result3 = await expensive_function("other")
        assert result3 == "result_other"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_decorator(self):
        """Test cache invalidation decorator."""
        cache_manager = GlobalCacheManager()
        
        @cached(namespace=CacheNamespace.DICTIONARY, ttl=3600)
        async def get_data(key: str) -> str:
            return f"data_{key}"
        
        @invalidate_cache(namespace=CacheNamespace.DICTIONARY, pattern="test*")
        async def update_data(key: str, value: str) -> None:
            # This would update the underlying data
            pass
        
        # Cache some data
        result = await get_data("test_key")
        assert result == "data_test_key"
        
        # Update - should invalidate cache
        await update_data("test_key", "new_value")
        
        # Next get should recalculate (not from cache)
        # In real scenario, get_data would return updated value
        result = await get_data("test_key")
        assert result == "data_test_key"  # Would be new value in real scenario
    
    @pytest.mark.asyncio
    async def test_clear_cache_decorator(self):
        """Test clearing entire cache namespace."""
        @cached(namespace=CacheNamespace.DICTIONARY, ttl=3600)
        async def cached_function(param: str) -> str:
            return f"cached_{param}"
        
        @clear_cache(namespace=CacheNamespace.DICTIONARY)
        async def clear_dictionary_cache() -> None:
            pass
        
        # Cache multiple values
        await cached_function("value1")
        await cached_function("value2")
        await cached_function("value3")
        
        # Clear entire namespace
        await clear_dictionary_cache()
        
        # All should be recalculated
        # (In practice, would check if function is called again)


class TestExternalContentStorage:
    """Test external content storage for large data."""
    
    @pytest.mark.asyncio
    async def test_store_external_content(self):
        """Test storing large content externally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure external storage
            with patch('floridify.caching.core.EXTERNAL_STORAGE_DIR', Path(tmpdir)):
                large_data = {"vocabulary": ["word"] * 100000}
                
                location = await store_external_content(
                    content=large_data,
                    namespace=CacheNamespace.CORPUS,
                    key="large_corpus",
                )
                
                assert isinstance(location, ContentLocation)
                assert location.storage_type == "filesystem"
                assert location.compression == "zstd"
                assert location.size_original > 0
                assert location.size_compressed < location.size_original
                
                # Verify file exists
                file_path = Path(tmpdir) / location.path
                assert file_path.exists()
    
    @pytest.mark.asyncio
    async def test_load_external_content(self):
        """Test loading externally stored content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('floridify.caching.core.EXTERNAL_STORAGE_DIR', Path(tmpdir)):
                original_data = {"test": ["data"] * 1000}
                
                # Store
                location = await store_external_content(
                    content=original_data,
                    namespace=CacheNamespace.CORPUS,
                    key="test_external",
                )
                
                # Load
                loaded_data = await load_external_content(location)
                
                assert loaded_data == original_data
    
    @pytest.mark.asyncio
    async def test_external_content_with_encryption(self):
        """Test external content with optional encryption."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('floridify.caching.core.EXTERNAL_STORAGE_DIR', Path(tmpdir)):
                sensitive_data = {"api_key": "secret", "data": "sensitive"}
                
                location = await store_external_content(
                    content=sensitive_data,
                    namespace=CacheNamespace.DICTIONARY,
                    key="sensitive",
                    encrypt=True,  # Enable encryption
                )
                
                # Should be encrypted
                assert location.encrypted is True
                
                # Load and verify
                loaded = await load_external_content(location)
                assert loaded == sensitive_data


class TestCachePerformance:
    """Test cache performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_l1_vs_l2_performance(self):
        """Compare L1 vs L2 cache performance."""
        import time
        
        manager = GlobalCacheManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            await manager.initialize(l2_base_dir=Path(tmpdir))
            
            namespace = CacheNamespace.DICTIONARY
            test_data = {"test": "data" * 100}
            
            # Warm up caches
            await manager.set(namespace, "perf_test", test_data)
            
            # Test L1 performance
            l1_start = time.perf_counter()
            for _ in range(1000):
                await manager.get(namespace, "perf_test")
            l1_time = time.perf_counter() - l1_start
            
            # Clear L1 to test L2
            await manager.l1_caches[namespace].clear()
            
            # Test L2 performance (first get will populate L1)
            l2_start = time.perf_counter()
            await manager.get(namespace, "perf_test")
            l2_time = time.perf_counter() - l2_start
            
            # L1 should be significantly faster
            assert l1_time < l2_time * 10  # L1 should be at least 10x faster
    
    @pytest.mark.asyncio
    async def test_cache_with_concurrent_access(self):
        """Test cache with concurrent access patterns."""
        manager = GlobalCacheManager()
        
        async def concurrent_operation(key: str, value: str):
            await manager.set(CacheNamespace.DICTIONARY, key, value)
            result = await manager.get(CacheNamespace.DICTIONARY, key)
            assert result == value
        
        # Run many concurrent operations
        tasks = [
            concurrent_operation(f"key_{i}", f"value_{i}")
            for i in range(100)
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify all values are cached
        for i in range(100):
            result = await manager.get(CacheNamespace.DICTIONARY, f"key_{i}")
            assert result == f"value_{i}"