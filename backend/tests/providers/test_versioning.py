"""Tests for versioning system and content deduplication."""

import asyncio
import hashlib
import json

import pytest

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace
from floridify.models.versioned import (
    ContentLocation,
    CorpusMetadata,
    DictionaryEntryMetadata,
    ResourceType,
    VersionConfig,
)


class TestVersionedDataManager:
    """Test versioned data management."""
    
    @pytest.mark.asyncio
    async def test_version_creation(self, test_db, version_manager: VersionedDataManager):
        """Test creating new versions."""
        content = {"word": "test", "definition": "a trial"}
        
        # Create first version
        v1 = await version_manager.save(
            resource_id="test_word",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,
            config=VersionConfig(version="1.0.0"),
        )
        
        assert v1.version_info.version == "1.0.0"
        assert v1.version_info.is_latest is True
        assert v1.resource_id == "test_word"
        
        # Verify content hash
        expected_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
        assert v1.version_info.data_hash == expected_hash
    
    @pytest.mark.asyncio
    async def test_version_increment(self, test_db, version_manager: VersionedDataManager):
        """Test automatic version incrementing."""
        content_v1 = {"data": "version1"}
        content_v2 = {"data": "version2"}
        
        # Create initial version
        v1 = await version_manager.save(
            resource_id="incremented",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content_v1,
            config=VersionConfig(version="1.0.0"),
        )
        
        # Create new version with increment
        v2 = await version_manager.save(
            resource_id="incremented",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content_v2,
            config=VersionConfig(increment_version=True),
        )
        
        assert v2.version_info.version == "1.0.1"
        assert v2.version_info.is_latest is True
        assert v2.version_info.supersedes == v1.id
        
        # Reload v1 to check it's no longer latest
        v1_reloaded = await DictionaryEntryMetadata.get(v1.id)
        assert v1_reloaded is not None
        assert v1_reloaded.version_info.is_latest is False
        assert v1_reloaded.version_info.superseded_by == v2.id
    
    @pytest.mark.asyncio
    async def test_content_deduplication(
        self, test_db, version_manager: VersionedDataManager
    ):
        """Test content deduplication by hash."""
        content = {"identical": "content"}
        
        # Save first version
        v1 = await version_manager.save(
            resource_id="dedup_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,
            config=VersionConfig(version="1.0.0"),
        )
        
        # Try to save identical content
        v2 = await version_manager.save(
            resource_id="dedup_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,  # Same content
            config=VersionConfig(version="1.0.1"),
        )
        
        # Should return the same version due to deduplication
        assert v1.id == v2.id
        assert v1.version_info.data_hash == v2.version_info.data_hash
    
    @pytest.mark.asyncio
    async def test_force_rebuild(self, test_db, version_manager: VersionedDataManager):
        """Test force rebuild bypassing deduplication."""
        content = {"data": "same"}
        
        # Save first version
        v1 = await version_manager.save(
            resource_id="force_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,
            config=VersionConfig(version="1.0.0"),
        )
        
        # Force rebuild with same content
        v2 = await version_manager.save(
            resource_id="force_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,
            config=VersionConfig(version="1.0.1", force_rebuild=True),
        )
        
        # Should create new version despite same content
        assert v1.id != v2.id
        assert v1.version_info.data_hash == v2.version_info.data_hash
        assert v2.version_info.version == "1.0.1"
    
    @pytest.mark.asyncio
    async def test_version_chain(self, test_db, version_manager: VersionedDataManager):
        """Test version chain relationships."""
        versions = []
        
        # Create chain of versions
        for i in range(5):
            content = {"version": i}
            v = await version_manager.save(
                resource_id="chain_test",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content=content,
                config=VersionConfig(
                    version=f"1.0.{i}",
                    increment_version=(i > 0),
                ),
            )
            versions.append(v)
        
        # Verify chain
        for i in range(1, 5):
            assert versions[i].version_info.supersedes == versions[i - 1].id
            
            # Reload previous version
            prev = await DictionaryEntryMetadata.get(versions[i - 1].id)
            assert prev is not None
            assert prev.version_info.superseded_by == versions[i].id
        
        # Only last should be latest
        assert versions[-1].version_info.is_latest is True
        for v in versions[:-1]:
            reloaded = await DictionaryEntryMetadata.get(v.id)
            assert reloaded is not None
            assert reloaded.version_info.is_latest is False
    
    @pytest.mark.asyncio
    async def test_get_latest_version(
        self, test_db, version_manager: VersionedDataManager
    ):
        """Test retrieving latest version."""
        # Create multiple versions
        for i in range(3):
            await version_manager.save(
                resource_id="latest_test",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content={"version": i},
                config=VersionConfig(version=f"1.0.{i}"),
            )
        
        # Get latest
        latest = await version_manager.get_latest(
            "latest_test", ResourceType.DICTIONARY
        )
        
        assert latest is not None
        assert latest.version_info.version == "1.0.2"
        assert latest.version_info.is_latest is True
    
    @pytest.mark.asyncio
    async def test_get_specific_version(
        self, test_db, version_manager: VersionedDataManager
    ):
        """Test retrieving specific version."""
        # Create multiple versions
        versions = []
        for i in range(3):
            v = await version_manager.save(
                resource_id="specific_test",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content={"version": i},
                config=VersionConfig(version=f"1.0.{i}"),
            )
            versions.append(v)
        
        # Get specific version
        v1 = await version_manager.get_by_version(
            "specific_test", ResourceType.DICTIONARY, "1.0.1"
        )
        
        assert v1 is not None
        assert v1.version_info.version == "1.0.1"
        content = await v1.get_content()
        assert content["version"] == 1
    
    @pytest.mark.asyncio
    async def test_list_versions(self, test_db, version_manager: VersionedDataManager):
        """Test listing all versions."""
        # Create multiple versions
        expected_versions = ["1.0.0", "1.0.1", "1.0.2"]
        for ver in expected_versions:
            await version_manager.save(
                resource_id="list_test",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content={"version": ver},
                config=VersionConfig(version=ver),
            )
        
        # List versions
        versions = await version_manager.list_versions(
            "list_test", ResourceType.DICTIONARY
        )
        
        assert set(versions) == set(expected_versions)
    
    @pytest.mark.asyncio
    async def test_delete_version(self, test_db, version_manager: VersionedDataManager):
        """Test deleting specific version."""
        # Create chain of 3 versions
        versions = []
        for i in range(3):
            v = await version_manager.save(
                resource_id="delete_test",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.DICTIONARY,
                content={"version": i},
                config=VersionConfig(
                    version=f"1.0.{i}",
                    increment_version=(i > 0),
                ),
            )
            versions.append(v)
        
        # Delete middle version
        deleted = await version_manager.delete_version(
            "delete_test", ResourceType.DICTIONARY, "1.0.1"
        )
        assert deleted is True
        
        # Verify it's deleted
        v1 = await version_manager.get_by_version(
            "delete_test", ResourceType.DICTIONARY, "1.0.1"
        )
        assert v1 is None
        
        # Verify chain is maintained
        v0 = await DictionaryEntryMetadata.get(versions[0].id)
        v2 = await DictionaryEntryMetadata.get(versions[2].id)
        
        assert v0 is not None
        assert v2 is not None
        assert v0.version_info.superseded_by == v2.id
        assert v2.version_info.supersedes == v0.id


class TestContentStorage:
    """Test content storage strategies."""
    
    @pytest.mark.asyncio
    async def test_inline_storage(self, test_db, version_manager: VersionedDataManager):
        """Test inline content storage for small data."""
        small_content = {"small": "data"}
        
        saved = await version_manager.save(
            resource_id="inline_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=small_content,
        )
        
        # Small content should be stored inline
        assert saved.content_inline == small_content
        assert saved.content_external is None
    
    @pytest.mark.asyncio
    async def test_external_storage(self, test_db, version_manager: VersionedDataManager):
        """Test external content storage for large data."""
        # Create large content (>100KB threshold)
        large_content = {"data": "x" * 200_000}  # ~200KB
        
        saved = await version_manager.save(
            resource_id="external_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=large_content,
        )
        
        # Large content should be stored externally
        assert saved.content_inline is None
        assert saved.content_external is not None
        assert isinstance(saved.content_external, ContentLocation)
        
        # Verify content can be retrieved
        retrieved = await saved.get_content()
        assert retrieved == large_content
    
    @pytest.mark.asyncio
    async def test_content_compression(
        self, test_db, version_manager: VersionedDataManager
    ):
        """Test content compression for external storage."""
        # Create highly compressible content
        repetitive_content = {"data": ["test"] * 10_000}
        
        saved = await version_manager.save(
            resource_id="compress_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=repetitive_content,
        )
        
        if saved.content_external:
            # Check compression was applied
            assert saved.content_external.compression == "zstd"
            assert saved.content_external.size_compressed < saved.content_external.size_original
        
        # Verify decompression works
        retrieved = await saved.get_content()
        assert retrieved == repetitive_content


class TestVersionedCache:
    """Test cache integration with versioning."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(
        self, test_db, version_manager: VersionedDataManager, cache_manager
    ):
        """Test cache hits for versioned data."""
        version_manager.cache = cache_manager
        
        content = {"cached": "data"}
        
        # Save with caching enabled
        saved = await version_manager.save(
            resource_id="cache_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,
            config=VersionConfig(use_cache=True),
        )
        
        # First get - from database
        result1 = await version_manager.get_latest(
            "cache_test", ResourceType.DICTIONARY, use_cache=True
        )
        
        # Second get - should hit cache
        result2 = await version_manager.get_latest(
            "cache_test", ResourceType.DICTIONARY, use_cache=True
        )
        
        assert result1 is not None
        assert result2 is not None
        assert result1.id == result2.id
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(
        self, test_db, version_manager: VersionedDataManager, cache_manager
    ):
        """Test cache invalidation on new version."""
        version_manager.cache = cache_manager
        
        # Create initial version
        v1 = await version_manager.save(
            resource_id="invalidate_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"version": 1},
            config=VersionConfig(use_cache=True),
        )
        
        # Get to populate cache
        cached = await version_manager.get_latest(
            "invalidate_test", ResourceType.DICTIONARY, use_cache=True
        )
        assert cached is not None
        assert cached.id == v1.id
        
        # Create new version
        v2 = await version_manager.save(
            resource_id="invalidate_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"version": 2},
            config=VersionConfig(increment_version=True, use_cache=True),
        )
        
        # Get latest should return new version
        latest = await version_manager.get_latest(
            "invalidate_test", ResourceType.DICTIONARY, use_cache=True
        )
        assert latest is not None
        assert latest.id == v2.id
        assert latest.id != v1.id
    
    @pytest.mark.asyncio
    async def test_cache_ttl(
        self, test_db, version_manager: VersionedDataManager, cache_manager
    ):
        """Test cache TTL expiration."""
        version_manager.cache = cache_manager
        
        # Save with short TTL
        saved = await version_manager.save(
            resource_id="ttl_test",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"ttl": "test"},
            config=VersionConfig(use_cache=True, ttl=1),  # 1 second TTL
        )
        
        # Get immediately - should hit cache
        result1 = await version_manager.get_latest(
            "ttl_test", ResourceType.DICTIONARY, use_cache=True
        )
        assert result1 is not None
        
        # Wait for TTL to expire
        await asyncio.sleep(1.5)
        
        # Get again - cache should be expired
        result2 = await version_manager.get_latest(
            "ttl_test", ResourceType.DICTIONARY, use_cache=True
        )
        assert result2 is not None
        assert result2.id == result1.id  # Same data, but from DB not cache


class TestVersionDependencies:
    """Test version dependency tracking."""
    
    @pytest.mark.asyncio
    async def test_dependency_tracking(
        self, test_db, version_manager: VersionedDataManager
    ):
        """Test tracking dependencies between versions."""
        # Create base versions
        dep1 = await version_manager.save(
            resource_id="dep1",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"dependency": 1},
        )
        
        dep2 = await version_manager.save(
            resource_id="dep2",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"dependency": 2},
        )
        
        # Create version with dependencies
        main = await version_manager.save(
            resource_id="main",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"main": "content"},
            dependencies=[dep1.id, dep2.id] if dep1.id and dep2.id else [],
        )
        
        assert len(main.version_info.dependencies) == 2
        assert dep1.id in main.version_info.dependencies
        assert dep2.id in main.version_info.dependencies
    
    @pytest.mark.asyncio
    async def test_cascading_invalidation(
        self, test_db, version_manager: VersionedDataManager
    ):
        """Test cascading invalidation of dependent versions."""
        # Create dependency chain
        base = await version_manager.save(
            resource_id="base",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"base": "content"},
        )
        
        dependent = await version_manager.save(
            resource_id="dependent",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"dependent": "content"},
            dependencies=[base.id] if base.id else [],
        )
        
        # Update base - should invalidate dependent
        new_base = await version_manager.save(
            resource_id="base",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content={"base": "updated"},
            config=VersionConfig(increment_version=True),
        )
        
        # Dependent should still reference old base version
        reloaded = await CorpusMetadata.get(dependent.id)
        assert reloaded is not None
        assert base.id in reloaded.version_info.dependencies
        assert new_base.id not in reloaded.version_info.dependencies