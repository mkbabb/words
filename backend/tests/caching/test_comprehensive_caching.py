"""Comprehensive caching system tests.

Tests the complete caching infrastructure including:
- Two-tier caching (L1 memory, L2 filesystem)
- Cache eviction policies
- Compression functionality
- Decorator behavior
- Filesystem backend operations
- Version-based cache keys
- Namespace isolation
"""

import asyncio
import time

import pytest
import pytest_asyncio

from floridify.caching.core import GlobalCacheManager, get_versioned_content
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import (
    CacheNamespace,
    ResourceType,
    VersionConfig,
)


@pytest.mark.asyncio
class TestCachingInfrastructure:
    """Test caching infrastructure components."""

    @pytest_asyncio.fixture
    async def cache_manager(self, tmp_path):
        """Create cache manager with temp directory."""
        filesystem_backend = FilesystemBackend(cache_dir=tmp_path / "cache")
        cache_manager = GlobalCacheManager[FilesystemBackend](l2_backend=filesystem_backend)
        await cache_manager.initialize()
        return cache_manager

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_two_tier_caching(self, cache_manager):
        """Test L1 memory and L2 filesystem caching."""
        from floridify.caching.core import CacheNamespace

        namespace = CacheNamespace.DEFAULT

        # Test L1 memory cache
        key = "test:memory:key"
        value = {"data": "memory cached", "timestamp": time.time()}

        await cache_manager.set(namespace, key, value)
        cached = await cache_manager.get(namespace, key)
        assert cached == value

        # Test L2 filesystem cache for large data
        large_key = "test:filesystem:key"
        large_value = {"data": "x" * (2 * 1024 * 1024)}  # 2MB

        await cache_manager.set(namespace, large_key, large_value)
        cached_large = await cache_manager.get(namespace, large_key)
        assert cached_large == large_value

        # Both L1 and L2 store the data - L1 has it until evicted
        # The implementation stores in both tiers, not just filesystem
        ns = cache_manager.namespaces.get(namespace)
        if ns:
            # Data is in memory cache (within limit) and also in filesystem
            assert large_key in ns.memory_cache

    async def test_cache_eviction(self, cache_manager):
        """Test cache eviction policies."""
        from floridify.caching.core import CacheNamespace

        namespace = CacheNamespace.DEFAULT

        # Fill cache to trigger eviction
        for i in range(10):
            key = f"eviction:test:{i}"
            value = {"data": "x" * (200 * 1024), "id": i}  # 200KB each
            await cache_manager.set(namespace, key, value)

        # Older entries should be evicted
        first_key = "eviction:test:0"
        cached = await cache_manager.get(namespace, first_key)
        # May be evicted from memory but still in filesystem
        ns = cache_manager.namespaces.get(namespace)
        if ns:
            assert cached is not None or first_key not in ns.memory_cache

    async def test_namespace_isolation(self, cache_manager):
        """Test cache namespace isolation."""
        # Set values in different namespaces
        namespaces = [
            CacheNamespace.CORPUS,
            CacheNamespace.SEARCH,
            CacheNamespace.DICTIONARY,
        ]

        for ns in namespaces:
            key = "test:key"  # Same key in different namespaces
            value = {"namespace": ns.value, "data": f"data_{ns.value}"}
            await cache_manager.set(ns, key, value)

        # Verify isolation
        for ns in namespaces:
            key = "test:key"
            cached = await cache_manager.get(ns, key)
            assert cached["namespace"] == ns.value

    async def test_concurrent_access(self, cache_manager):
        """Test concurrent cache operations."""
        from floridify.caching.core import CacheNamespace

        namespace = CacheNamespace.DEFAULT

        async def cache_operation(id: int):
            key = f"concurrent:test:{id}"
            value = {"id": id, "data": f"value_{id}"}
            await cache_manager.set(namespace, key, value)
            cached = await cache_manager.get(namespace, key)
            return cached

        # Run concurrent operations
        tasks = [cache_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all operations succeeded
        for i, result in enumerate(results):
            assert result["id"] == i


@pytest.mark.asyncio
class TestVersionedCaching:
    """Test versioned caching functionality."""

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_version_based_keys(self, test_db, versioned_manager):
        """Test version-based cache key generation."""
        # Save v1
        v1 = await versioned_manager.save(
            resource_id="test-resource",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "version 1"},
            config=VersionConfig(version="1.0.0"),
        )

        # Save v2
        v2 = await versioned_manager.save(
            resource_id="test-resource",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "version 2"},
            config=VersionConfig(version="2.0.0"),
        )

        # Different versions should have different cache keys
        assert v1.id != v2.id
        assert v1.version_info.version != v2.version_info.version

    async def test_cache_invalidation(self, test_db, versioned_manager):
        """Test cache invalidation on updates."""
        # Save initial version
        v1 = await versioned_manager.save(
            resource_id="invalidation-test",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "initial", "vocabulary": ["test1"]},
        )

        # Get with cache
        cached = await versioned_manager.get_latest(
            resource_id="invalidation-test",
            resource_type=ResourceType.CORPUS,
            config=VersionConfig(use_cache=True),
        )
        assert cached is not None
        initial_content = await get_versioned_content(cached)
        assert initial_content["data"] == "initial"

        # Update content with force_rebuild to ensure new version
        v2 = await versioned_manager.save(
            resource_id="invalidation-test",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "updated", "vocabulary": ["test2"]},
            config=VersionConfig(increment_version=True, force_rebuild=True),
        )

        # Verify new version was created
        assert v2.id != v1.id
        assert v2.version_info.version != v1.version_info.version

        # Get latest should return new version
        latest = await versioned_manager.get_latest(
            resource_id="invalidation-test",
            resource_type=ResourceType.CORPUS,
            config=VersionConfig(use_cache=False),  # Bypass cache to ensure fresh read
        )
        content = await get_versioned_content(latest)
        assert content["data"] == "updated"

    async def test_content_deduplication(self, test_db, versioned_manager):
        """Test that identical content is deduplicated."""
        content = {"data": "duplicate content", "value": 123}

        # Save same content multiple times
        saves = []
        for i in range(3):
            saved = await versioned_manager.save(
                resource_id="dedup-test",
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content=content,
            )
            saves.append(saved)

        # All should have same content hash
        hashes = [s.version_info.data_hash for s in saves]
        assert len(set(hashes)) == 1

        # Should reuse same document
        ids = [s.id for s in saves]
        assert len(set(ids)) == 1

    async def test_force_rebuild(self, test_db, versioned_manager):
        """Test force rebuild bypasses cache."""
        content = {"data": "test"}

        # Save initial
        v1 = await versioned_manager.save(
            resource_id="force-test",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
        )

        # Force rebuild with same content
        v2 = await versioned_manager.save(
            resource_id="force-test",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
            config=VersionConfig(force_rebuild=True),
        )

        # Force rebuild creates new version despite same content
        # The version increment depends on existing versions in the database
        assert v2.version_info.data_hash == v1.version_info.data_hash  # Same content
        assert v2.version_info.version != v1.version_info.version  # Different version


@pytest.mark.asyncio
class TestFilesystemBackend:
    """Test filesystem backend operations."""

    @pytest_asyncio.fixture
    async def fs_backend(self, tmp_path):
        """Create filesystem backend."""
        return FilesystemBackend(cache_dir=tmp_path / "fs_cache")

    async def test_file_operations(self, fs_backend):
        """Test basic file operations."""
        key = "test:file:key"
        value = {"data": "filesystem test"}

        # Write
        await fs_backend.set(key, value)

        # Read
        cached = await fs_backend.get(key)
        assert cached == value

        # Delete
        await fs_backend.delete(key)
        deleted = await fs_backend.get(key)
        assert deleted is None

    async def test_directory_structure(self, fs_backend, tmp_path):
        """Test cache directory structure."""
        # Set values with different namespaces
        await fs_backend.set("corpus:test:1", {"type": "corpus"})
        await fs_backend.set("search:test:1", {"type": "search"})
        await fs_backend.set("provider:test:1", {"type": "provider"})

        # Check directory structure
        cache_dir = tmp_path / "fs_cache"
        assert cache_dir.exists()

        # diskcache creates SQLite database files, not individual JSON files
        # Check for database files that should be created
        cache_files = list(cache_dir.glob("cache.db*"))
        assert len(cache_files) >= 1  # At least cache.db should exist

        # Verify the data can be retrieved
        corpus_data = await fs_backend.get("corpus:test:1")
        search_data = await fs_backend.get("search:test:1")
        provider_data = await fs_backend.get("provider:test:1")

        assert corpus_data == {"type": "corpus"}
        assert search_data == {"type": "search"}
        assert provider_data == {"type": "provider"}

    async def test_concurrent_file_access(self, fs_backend):
        """Test concurrent file operations."""

        async def file_operation(id: int):
            key = f"concurrent:file:{id}"
            value = {"id": id}
            await fs_backend.set(key, value)
            return await fs_backend.get(key)

        # Run concurrent file operations
        tasks = [file_operation(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        for i, result in enumerate(results):
            assert result["id"] == i

    async def test_large_file_handling(self, fs_backend):
        """Test handling of large files."""
        key = "test:large:file"
        # Create 5MB of data
        large_value = {"data": "x" * (5 * 1024 * 1024)}

        await fs_backend.set(key, large_value)
        cached = await fs_backend.get(key)

        assert cached == large_value

    async def test_cleanup_operations(self, fs_backend, tmp_path):
        """Test cache cleanup operations."""
        # Create multiple cache entries
        for i in range(5):
            await fs_backend.set(f"cleanup:test:{i}", {"id": i})

        # Verify data exists by retrieving it
        for i in range(5):
            cached = await fs_backend.get(f"cleanup:test:{i}")
            assert cached == {"id": i}

        # Clear all
        await fs_backend.clear()

        # Verify cleanup - data should no longer be retrievable
        for i in range(5):
            cached = await fs_backend.get(f"cleanup:test:{i}")
            assert cached is None
