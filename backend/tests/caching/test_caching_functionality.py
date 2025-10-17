"""Tests for caching and versioning functionality without database dependencies.

Focuses on testing the core caching logic and versioning system
without requiring full database initialization.
"""

import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import (
    CacheNamespace,
    CompressionType,
    ContentLocation,
    StorageType,
    VersionConfig,
    VersionInfo,
)


class TestCacheBasicFunctionality:
    """Test basic caching operations."""

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self):
        """Test set, get, and delete operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "test_key"
            data = {"test": "value", "number": 42}

            # Set
            await manager.set(namespace, key, data)

            # Get
            retrieved = await manager.get(namespace, key)
            assert retrieved == data

            # Delete
            await manager.delete(namespace, key)

            # Verify deleted
            after_delete = await manager.get(namespace, key)
            assert after_delete is None

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that different namespaces are isolated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            key = "shared_key"
            dict_data = {"type": "dictionary"}
            lit_data = {"type": "literature"}

            # Store in different namespaces
            await manager.set(CacheNamespace.DICTIONARY, key, dict_data)
            await manager.set(CacheNamespace.LITERATURE, key, lit_data)

            # Retrieve from each namespace
            dict_result = await manager.get(CacheNamespace.DICTIONARY, key)
            lit_result = await manager.get(CacheNamespace.LITERATURE, key)

            assert dict_result == dict_data
            assert lit_result == lit_data
            assert dict_result != lit_result

    @pytest.mark.asyncio
    async def test_large_data_caching(self):
        """Test caching of large data structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            # Create large data structure
            large_data = {
                "definitions": [f"Definition {i}" for i in range(1000)],
                "examples": [f"Example sentence {i}" for i in range(500)],
                "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
            }

            namespace = CacheNamespace.DICTIONARY
            key = "large_data_test"

            # Cache large data
            await manager.set(namespace, key, large_data)

            # Retrieve and verify
            retrieved = await manager.get(namespace, key)
            assert retrieved is not None
            assert len(retrieved["definitions"]) == 1000
            assert len(retrieved["examples"]) == 500
            assert len(retrieved["metadata"]) == 100

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            async def cache_operation(i: int):
                key = f"concurrent_key_{i}"
                data = {"index": i, "timestamp": datetime.now(UTC).isoformat()}

                await manager.set(namespace, key, data)
                retrieved = await manager.get(namespace, key)

                assert retrieved["index"] == i
                return retrieved

            # Run multiple concurrent operations
            tasks = [cache_operation(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            for i, result in enumerate(results):
                assert result["index"] == i


class TestErrorHandling:
    """Test error handling in caching and versioning."""

    @pytest.mark.asyncio
    async def test_cache_nonexistent_key(self):
        """Test retrieving nonexistent cache key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            result = await manager.get(CacheNamespace.DICTIONARY, "nonexistent_key")
            assert result is None


class TestCachePerformance:
    """Test cache performance characteristics."""

    @pytest.mark.asyncio
    async def test_batch_cache_operations(self):
        """Test performance of batch cache operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            # Prepare batch data
            batch_data = {}
            for i in range(100):
                key = f"batch_key_{i}"
                data = {"index": i, "content": f"Content for item {i}"}
                batch_data[key] = data

            # Set all items
            start_time = datetime.now(UTC)
            for key, data in batch_data.items():
                await manager.set(namespace, key, data)
            set_duration = (datetime.now(UTC) - start_time).total_seconds()

            # Get all items
            start_time = datetime.now(UTC)
            retrieved_data = {}
            for key in batch_data:
                retrieved_data[key] = await manager.get(namespace, key)
            get_duration = (datetime.now(UTC) - start_time).total_seconds()

            # Verify all data retrieved correctly
            assert len(retrieved_data) == 100
            for key, data in batch_data.items():
                assert retrieved_data[key] == data

            # Performance should be reasonable (less than 10 seconds for 100 items)
            assert set_duration < 10.0
            assert get_duration < 10.0

    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self):
        """Test memory usage with different data sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY

            # Test different data sizes
            sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB

            for size in sizes:
                key = f"size_test_{size}"
                data = {"content": "A" * size, "size": size}

                # Should handle all sizes
                await manager.set(namespace, key, data)
                retrieved = await manager.get(namespace, key)

                assert retrieved is not None
                assert retrieved["size"] == size
                assert len(retrieved["content"]) == size
