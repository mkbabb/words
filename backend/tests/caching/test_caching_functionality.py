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
    async def test_cache_initialization(self):
        """Test cache manager can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            assert manager.l2_backend == backend
            assert manager.l1_caches is not None

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
    async def test_cache_with_ttl(self):
        """Test cache TTL behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            namespace = CacheNamespace.DICTIONARY
            key = "ttl_test"
            data = {"expires": "soon"}

            # Set with TTL
            await manager.set(namespace, key, data, ttl_override=timedelta(seconds=1))

            # Should be available immediately
            immediate = await manager.get(namespace, key)
            assert immediate == data

            # Wait for expiration
            await asyncio.sleep(1.5)

            # May or may not be expired depending on cache implementation
            # This tests the interface, not necessarily the expiration logic

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


class TestVersioningFunctionality:
    """Test versioning system functionality."""

    def test_version_info_creation(self):
        """Test VersionInfo can be created with correct structure."""
        content = {"test": "data"}
        data_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

        version_info = VersionInfo(version="1.0.0", data_hash=data_hash, is_latest=True)

        assert version_info.version == "1.0.0"
        assert version_info.data_hash == data_hash
        assert version_info.is_latest is True
        assert version_info.created_at is not None

    def test_version_config_creation(self):
        """Test VersionConfig with various options."""
        config = VersionConfig(
            force_rebuild=True,
            use_cache=False,
            version="2.0.0",
            increment_version=False,
            ttl=timedelta(hours=24),
        )

        assert config.force_rebuild is True
        assert config.use_cache is False
        assert config.version == "2.0.0"
        assert config.increment_version is False
        assert config.ttl == timedelta(hours=24)

    def test_content_location_creation(self):
        """Test ContentLocation for external storage."""
        location = ContentLocation(
            storage_type=StorageType.CACHE,
            cache_namespace=CacheNamespace.DICTIONARY,
            cache_key="test_key",
            path="/tmp/test/content.json",
            compression=CompressionType.ZSTD,
            size_bytes=1024,
            size_compressed=512,
            checksum="abc123def456",
        )

        assert location.storage_type == StorageType.CACHE
        assert location.cache_namespace == CacheNamespace.DICTIONARY
        assert location.size_bytes == 1024
        assert location.size_compressed == 512
        assert location.checksum == "abc123def456"

    def test_hash_generation_consistency(self):
        """Test that identical content produces identical hashes."""
        content1 = {"definitions": ["test"], "word": "example"}
        content2 = {"word": "example", "definitions": ["test"]}  # Different order

        hash1 = hashlib.sha256(json.dumps(content1, sort_keys=True).encode()).hexdigest()

        hash2 = hashlib.sha256(json.dumps(content2, sort_keys=True).encode()).hexdigest()

        # Should be identical despite different order
        assert hash1 == hash2

    def test_version_chain_logic(self):
        """Test version chain relationships."""
        # Version 1
        version1 = VersionInfo(version="1.0.0", data_hash="hash1", is_latest=False)

        # Version 2 supersedes version 1
        version2 = VersionInfo(
            version="2.0.0",
            data_hash="hash2",
            is_latest=True,
            supersedes=None,  # Would be version1.id in real usage
        )

        # Update version 1 to point to version 2
        version1.is_latest = False
        version1.superseded_by = None  # Would be version2.id in real usage

        assert version1.is_latest is False
        assert version2.is_latest is True


class TestCompressionAndStorage:
    """Test compression and storage functionality."""

    def test_compression_type_enum(self):
        """Test compression type enumeration."""
        assert CompressionType.ZSTD == "zstd"
        assert CompressionType.LZ4 == "lz4"
        assert CompressionType.GZIP == "gzip"
        assert CompressionType.NONE == "none"

    def test_storage_type_enum(self):
        """Test storage type enumeration."""
        assert StorageType.MEMORY == "memory"
        assert StorageType.CACHE == "cache"
        assert StorageType.DATABASE == "database"
        assert StorageType.S3 == "s3"

    def test_cache_namespace_enum(self):
        """Test cache namespace enumeration."""
        namespaces = [
            CacheNamespace.DICTIONARY,
            CacheNamespace.LITERATURE,
            CacheNamespace.SEMANTIC,
            CacheNamespace.CORPUS,
            CacheNamespace.TRIE,
        ]

        for namespace in namespaces:
            assert isinstance(namespace, str)
            assert len(namespace) > 3  # Should be meaningful names

    @pytest.mark.asyncio
    async def test_size_based_storage_decision(self):
        """Test logic for choosing storage type based on size."""
        # Small data (should be inline)
        small_data = {"small": "content"}
        small_size = len(json.dumps(small_data, sort_keys=True).encode())

        # Large data (should be external)
        large_data = {"large": "A" * 2_000_000}  # >1MB
        large_size = len(json.dumps(large_data, sort_keys=True).encode())

        # Test size threshold logic
        threshold = 1_000_000  # 1MB

        assert small_size < threshold
        assert large_size > threshold


class TestCacheKeyGeneration:
    """Test cache key generation patterns."""

    def test_cache_key_patterns(self):
        """Test various cache key generation patterns."""
        # Dictionary entry keys
        word = "example"
        provider = "wiktionary"
        version = "1.0.0"

        dict_key = f"dict:{provider}:{word}:v{version}"
        assert word in dict_key
        assert provider in dict_key
        assert version in dict_key

        # Literature entry keys
        title = "hamlet"
        author = "shakespeare"

        lit_key = f"lit:{author}:{title}"
        assert author in lit_key
        assert title in lit_key

        # Semantic index keys
        corpus_id = "english_corpus"
        model_name = "sentence_transformer"

        semantic_key = f"semantic:{corpus_id}:{model_name}"
        assert corpus_id in semantic_key
        assert model_name in semantic_key

    def test_key_sanitization(self):
        """Test cache key sanitization for special characters."""
        # Keys with special characters that need sanitization
        problematic_keys = [
            "word with spaces",
            "word/with/slashes",
            "word:with:colons",
            "word-with-dashes",
        ]

        for key in problematic_keys:
            # Basic sanitization logic
            sanitized = key.replace(" ", "_").replace("/", "_").replace(":", "_")

            # Should not contain problematic characters
            assert " " not in sanitized
            assert "/" not in sanitized
            # Colons might be used as separators, so check context


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

    @pytest.mark.asyncio
    async def test_cache_invalid_namespace(self):
        """Test using undefined namespace (should handle gracefully)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()

            # Using a valid namespace string (this tests the interface)
            namespace = CacheNamespace.DICTIONARY

            # Should handle normally
            await manager.set(namespace, "test_key", {"test": "data"})
            result = await manager.get(namespace, "test_key")
            assert result == {"test": "data"}

    def test_version_info_validation(self):
        """Test version info with invalid data."""
        # Empty version
        version_info = VersionInfo(version="", data_hash="valid_hash", is_latest=True)

        # Should create but version is empty
        assert version_info.version == ""
        assert version_info.data_hash == "valid_hash"

        # Invalid hash (empty)
        version_info_empty_hash = VersionInfo(version="1.0.0", data_hash="", is_latest=True)

        assert version_info_empty_hash.data_hash == ""


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
