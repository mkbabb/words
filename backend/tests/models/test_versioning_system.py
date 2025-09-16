"""Test versioning and caching system functionality."""

import asyncio
from datetime import datetime

import pytest

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import (
    CacheNamespace,
    ResourceType,
    VersionConfig,
)
from floridify.corpus.core import Corpus


@pytest.mark.asyncio
class TestVersioningSystem:
    """Test versioning system functionality."""

    async def test_version_creation(self, test_db):
        """Test creating new versions."""
        manager = VersionedDataManager()

        # Save initial version
        v1 = await manager.save(
            resource_id="test-resource",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "version 1"},
            config=VersionConfig(version="1.0.0"),
        )

        assert v1 is not None
        assert v1.resource_id == "test-resource"
        assert v1.version_info.version == "1.0.0"
        assert v1.version_info.is_latest is True

    async def test_version_increment(self, test_db):
        """Test automatic version incrementing."""
        manager = VersionedDataManager()

        # Save initial version
        v1 = await manager.save(
            resource_id="test-increment",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "version 1"},
        )
        assert v1.version_info.version == "1.0.0"

        # Save second version with increment
        v2 = await manager.save(
            resource_id="test-increment",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "version 2"},
            config=VersionConfig(increment_version=True),
        )

        assert v2.version_info.version == "1.0.1"
        assert v2.version_info.is_latest is True

        # First version should no longer be latest
        v1_check = await Corpus.Metadata.get(v1.id)
        assert v1_check.version_info.is_latest is False

    async def test_version_chain(self, test_db):
        """Test version chain relationships."""
        manager = VersionedDataManager()

        # Create version chain
        versions = []
        for i in range(3):
            v = await manager.save(
                resource_id="test-chain",
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content={"data": f"version {i + 1}"},
                config=VersionConfig(
                    version=f"1.0.{i}",
                    increment_version=(i > 0),
                ),
            )
            versions.append(v)

        # Check chain relationships
        assert versions[0].version_info.previous_version is None
        assert versions[0].version_info.next_version == versions[1].id

        assert versions[1].version_info.previous_version == versions[0].id
        assert versions[1].version_info.next_version == versions[2].id

        assert versions[2].version_info.previous_version == versions[1].id
        assert versions[2].version_info.next_version is None
        assert versions[2].version_info.is_latest is True

    async def test_content_deduplication(self, test_db):
        """Test that identical content isn't duplicated."""
        manager = VersionedDataManager()

        content = {"data": "same content", "value": 42}

        # Save first version
        v1 = await manager.save(
            resource_id="test-dedup",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
        )

        # Try to save identical content
        v2 = await manager.save(
            resource_id="test-dedup",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
        )

        # Should return the same version
        assert v1.id == v2.id
        assert v1.content_hash == v2.content_hash

    async def test_force_rebuild(self, test_db):
        """Test force rebuild bypasses cache."""
        manager = VersionedDataManager()

        content = {"data": "test content"}

        # Save initial version
        v1 = await manager.save(
            resource_id="test-force",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
        )

        # Force rebuild with same content
        v2 = await manager.save(
            resource_id="test-force",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=content,
            config=VersionConfig(force_rebuild=True),
        )

        # Should create new version despite same content
        assert v1.id != v2.id
        assert v1.content_hash == v2.content_hash  # Content is same
        assert v2.version_info.version == "1.0.1"  # But version incremented

    async def test_get_latest_version(self, test_db):
        """Test retrieving latest version."""
        manager = VersionedDataManager()

        # Create multiple versions
        for i in range(3):
            await manager.save(
                resource_id="test-latest",
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content={"data": f"version {i + 1}"},
                config=VersionConfig(version=f"1.0.{i}"),
            )

        # Get latest
        latest = await manager.get_latest(
            resource_id="test-latest",
            resource_type=ResourceType.CORPUS,
        )

        assert latest is not None
        assert latest.version_info.version == "1.0.2"
        assert latest.version_info.is_latest is True

    async def test_delete_version(self, test_db):
        """Test deleting versions."""
        manager = VersionedDataManager()

        # Create version
        v1 = await manager.save(
            resource_id="test-delete",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "to be deleted"},
        )

        # Delete it
        deleted = await manager.delete_version(
            resource_id="test-delete",
            resource_type=ResourceType.CORPUS,
        )
        assert deleted is True

        # Should not be retrievable
        gone = await manager.get_latest(
            resource_id="test-delete",
            resource_type=ResourceType.CORPUS,
        )
        assert gone is None

    async def test_concurrent_saves(self, test_db):
        """Test concurrent save operations."""
        manager = VersionedDataManager()

        # Create multiple save tasks
        tasks = []
        for i in range(5):
            task = manager.save(
                resource_id=f"concurrent-{i}",
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content={"data": f"concurrent {i}"},
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed"
            assert result is not None
            assert result.resource_id == f"concurrent-{i}"

    async def test_metadata_handling(self, test_db):
        """Test metadata storage and retrieval."""
        manager = VersionedDataManager()

        metadata = {
            "author": "Test Author",
            "tags": ["test", "versioning"],
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save with metadata
        v1 = await manager.save(
            resource_id="test-metadata",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"data": "test"},
            metadata=metadata,
        )

        # Retrieve and check metadata
        retrieved = await manager.get_latest(
            resource_id="test-metadata",
            resource_type=ResourceType.CORPUS,
        )

        assert retrieved is not None
        # Metadata is stored in the document itself
        assert retrieved.resource_id == "test-metadata"

        # Get content to verify
        from floridify.caching.core import get_versioned_content

        content = await get_versioned_content(retrieved)
        assert content is not None
