"""Unified version management system.

This module provides centralized version management for all data types,
handling caching, storage, deduplication, and version chains.
"""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any, TypeVar

from motor.motor_asyncio import AsyncIOMotorClientSession

from .models import CacheNamespace, CompressionType
from .unified import UnifiedCache, get_unified
from ..models.versioned import (
    ContentLocation,
    CorpusVersionedData,
    DictionaryVersionedData,
    LiteratureVersionedData,
    SemanticVersionedData,
    StorageType,
    VersionConfig,
    VersionedData,
    VersionInfo,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=VersionedData)


class VersionedDataManager[T: VersionedData]:
    """Centralized manager for all versioned data operations.

    Uses the unified cache system for all memory and disk caching,
    leveraging per-namespace memory limits for efficient resource usage.
    """

    def __init__(
        self,
        data_class: type[T],
        cache_namespace: CacheNamespace = CacheNamespace.DEFAULT,
        default_config: VersionConfig | None = None,
    ):
        """Initialize versioned data manager.

        Args:
            data_class: The versioned data class to manage
            default_config: Default configuration for version management

        """
        self.data_class = data_class
        self.cache_namespace = cache_namespace
        self.config = default_config or VersionConfig()
        self._cache: UnifiedCache | None = None
        self._lock = asyncio.Lock()

    async def get_cache(self) -> UnifiedCache:
        """Get or create cache instance."""
        if self._cache is None:
            self._cache = await get_unified()
        return self._cache

    def generate_cache_key(
        self,
        resource_type: str,
        resource_id: str,
        version: str | None = None,
        hash_value: str | None = None,
    ) -> str:
        """Generate standardized cache key.

        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            version: Optional version string
            hash_value: Optional hash value

        Returns:
            Standardized cache key

        """
        # Sanitize resource_id to be URL-safe
        safe_id = resource_id.replace("/", "_").replace(" ", "_").replace(":", "_")
        parts = [resource_type, safe_id]

        if version:
            parts.append(f"v{version}")
        if hash_value:
            parts.append(hash_value[:8])

        return ":".join(parts)

    async def get_latest(
        self,
        resource_id: str,
        resource_type: str | None = None,
        config: VersionConfig | None = None,
    ) -> T | None:
        """Get the latest version of a resource.

        Args:
            resource_id: The resource identifier
            resource_type: Optional resource type filter
            config: Optional config override

        Returns:
            Latest version or None if not found

        """
        config = config or self.config

        # Skip cache check if force_rebuild
        if config.force_rebuild:
            return None

        # Get appropriate namespace
        cache_key = self.generate_cache_key(resource_type or "unknown", resource_id)

        # Check unified cache (it handles memory and disk)
        cache = await self.get_cache()
        cached_data = await cache.get_compressed(self.cache_namespace, cache_key)

        if cached_data is not None:
            # Reconstruct from cached data
            if isinstance(cached_data, dict):
                return self.data_class(**cached_data)
            # Assume it's already a proper instance
            return cached_data if isinstance(cached_data, self.data_class) else None

        # Build query
        query = {
            "resource_id": resource_id,
            "version_info.is_latest": True,
        }
        if resource_type:
            query["resource_type"] = resource_type

        # Find latest version in database
        latest = await self.data_class.find_one(query)

        if latest and latest.content_location:
            # Load content from storage
            content = await self.load_content(latest.content_location)
            if content and not latest.content_inline:
                latest.content_inline = content

        # Cache the result if found
        if latest:
            await cache.set_compressed(
                namespace=self.cache_namespace,
                key=cache_key,
                value=latest.model_dump(),
                ttl=config.ttl,
            )

        return latest

    async def save(
        self,
        resource_id: str,
        content: dict[str, Any],
        resource_type: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        config: VersionConfig | None = None,
        **kwargs: Any,
    ) -> T:
        """Save a new version of data.

        Args:
            resource_id: The resource identifier
            content: The content to save
            resource_type: The type of resource
            metadata: Optional metadata
            tags: Optional tags
            config: Optional config override
            **kwargs: Additional fields for the versioned data

        Returns:
            The saved versioned data

        """
        config = config or self.config

        # Compute hash for deduplication
        data_hash = VersionedData.compute_hash(content)

        # Check for existing version with same hash
        if not config.force_rebuild:
            existing = await self.data_class.find_one(
                {
                    "resource_id": resource_id,
                    "resource_type": resource_type,
                    "version_info.data_hash": data_hash,
                },
            )

            if existing:
                logger.debug(f"Content already exists for {resource_id} with same hash")
                return existing

        # Store content in cache
        content_location = await self.store_content(
            resource_id=resource_id,
            resource_type=resource_type,
            content=content,
            data_hash=data_hash,
            ttl=config.ttl,
        )

        # Create version info with proper versioning
        next_version = await self._get_next_version(resource_id)
        version_info = VersionInfo(
            version=next_version,
            data_hash=data_hash,
            is_latest=True,
        )

        # Create versioned data
        versioned_data = self.data_class(
            resource_id=resource_id,
            resource_type=resource_type,
            version_info=version_info,
            content_location=content_location,
            content_inline=content if len(json.dumps(content)) < 1024 else None,
            metadata=metadata or {},
            tags=tags or [],
            **kwargs,
        )

        # Use transaction for atomic version chain update
        async with (
            await self.data_class.get_motor_collection().database.client.start_session() as session
        ):
            async with session.start_transaction():
                # Update version chain atomically
                await self._update_version_chain_atomic(
                    versioned_data,
                    session,
                )

                # Save to database
                await versioned_data.save(session=session)

        # Cache the new version

        cache_key = self.generate_cache_key(resource_type, resource_id)
        cache = await self.get_cache()
        await cache.set_compressed(
            namespace=self.cache_namespace,
            key=cache_key,
            value=versioned_data.model_dump(),
            ttl=config.ttl,
            tags=tags,
        )

        logger.info(f"Saved new version for {resource_type}:{resource_id}")
        return versioned_data

    async def store_content(
        self,
        resource_id: str,
        resource_type: str,
        content: dict[str, Any],
        data_hash: str,
        ttl: timedelta | None = None,
    ) -> ContentLocation:
        """Store content in cache and return location.

        Args:
            resource_id: The resource identifier
            resource_type: The type of resource
            content: The content to store
            data_hash: Hash of the content
            ttl: Optional TTL for cache storage

        Returns:
            Content location information

        """
        # Use centralized namespace mapping

        cache = await self.get_cache()
        next_version = await self._get_next_version(resource_id)
        cache_key = self.generate_cache_key(
            resource_type,
            resource_id,
            next_version,
            data_hash,
        )

        # Store in unified cache with compression
        await cache.set_compressed(
            namespace=self.cache_namespace,
            key=cache_key,
            value=content,
            ttl=ttl,  # Use the provided TTL
        )

        return ContentLocation(
            storage_type=StorageType.CACHE,
            cache_namespace=self.cache_namespace,
            cache_key=cache_key,
            content_type="json",
            compression_type=CompressionType.ZLIB,
            size_bytes=len(json.dumps(content)),
        )

    async def load_content(
        self,
        location: ContentLocation,
    ) -> dict[str, Any] | None:
        """Load content from storage location.

        Args:
            location: Content location information

        Returns:
            Content or None if not found

        """
        if location.storage_type == StorageType.CACHE:
            cache = await self.get_cache()
            if not location.cache_namespace:
                logger.error("Cache namespace is required for cache storage")
                return None

            # Try to get compressed first, then regular
            if not location.cache_key:
                logger.error("Cache key is required for cache storage")
                return None
            result = await cache.get_compressed(
                namespace=location.cache_namespace,
                key=location.cache_key,
            )
            if result is None:
                # Fallback to regular get
                if location.cache_key:
                    result = await cache.get(
                        namespace=location.cache_namespace,
                        key=location.cache_key,
                    )
            return result

        if location.storage_type == StorageType.DISK and location.file_path:
            # TODO: Implement disk loading
            logger.warning("Disk storage not yet implemented")
            return None
        if location.storage_type == StorageType.DATABASE:
            # Content should be inline
            return None
        logger.warning(f"Unknown storage type: {location.storage_type}")
        return None

    async def get_versions(
        self,
        resource_id: str,
        resource_type: str | None = None,
        limit: int = 10,
    ) -> list[T]:
        """Get version history for a resource.

        Args:
            resource_id: The resource identifier
            resource_type: Optional resource type filter
            limit: Maximum number of versions to return

        Returns:
            List of versions, newest first

        """
        query = {"resource_id": resource_id}
        if resource_type:
            query["resource_type"] = resource_type

        versions = (
            await self.data_class.find(query)
            .sort("-version_info.created_at")
            .limit(limit)
            .to_list()
        )

        return versions

    async def cleanup_versions(
        self,
        resource_id: str,
        resource_type: str | None = None,
        keep_count: int = 5,
    ) -> int:
        """Clean up old versions, keeping only the most recent.

        Args:
            resource_id: The resource identifier
            resource_type: Optional resource type filter
            keep_count: Number of versions to keep

        Returns:
            Number of versions deleted

        """
        # Get all versions
        versions = await self.get_versions(
            resource_id=resource_id,
            resource_type=resource_type,
            limit=1000,
        )

        if len(versions) <= keep_count:
            return 0

        # Delete old versions
        to_delete = versions[keep_count:]
        deleted_count = 0

        for version in to_delete:
            # Clean up cache if needed
            if (
                version.content_location
                and version.content_location.storage_type == StorageType.CACHE
            ):
                cache = await self.get_cache()
                if (
                    version.content_location.cache_namespace
                    and version.content_location.cache_key
                ):
                    await cache.delete(
                        namespace=version.content_location.cache_namespace,
                        key=version.content_location.cache_key,
                    )

            # Delete from database
            await version.delete()
            deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old versions for {resource_id}")
        return deleted_count

    async def cleanup_all_versions(
        self,
        resource_type: str,
        keep_count: int = 5,
    ) -> int:
        """Clean up all versions of a resource type.

        Args:
            resource_type: The resource type to clean up
            keep_count: Number of versions to keep per resource

        Returns:
            Total number of versions deleted

        """
        # Get all unique resource IDs for this type
        pipeline = [
            {"$match": {"resource_type": resource_type}},
            {"$group": {"_id": "$resource_id"}},
        ]

        collection = self.data_class.get_motor_collection()
        cursor = collection.aggregate(pipeline)

        total_deleted = 0
        async for doc in cursor:
            resource_id = doc["_id"]
            deleted = await self.cleanup_versions(
                resource_id=resource_id,
                resource_type=resource_type,
                keep_count=keep_count,
            )
            total_deleted += deleted

        logger.info(
            f"Cleaned up {total_deleted} total versions for type {resource_type}"
        )
        return total_deleted

    async def invalidate_cache(
        self,
        resource_id: str | None = None,
        resource_type: str | None = None,
    ) -> int:
        """Invalidate cache entries.

        Args:
            resource_id: Optional specific resource to invalidate
            resource_type: Optional resource type to invalidate

        Returns:
            Number of entries invalidated

        """
        cache = await self.get_cache()

        if resource_type:
            # Invalidate entire namespace
            return await cache.invalidate_namespace(self.cache_namespace)
        if resource_id:
            # Invalidate specific resource
            return await cache.delete(self.cache_namespace, resource_id)

    async def _get_next_version(self, resource_id: str) -> str:
        """Get the next version number for a resource.

        Args:
            resource_id: The resource identifier

        Returns:
            Next semantic version string

        """
        # Get latest version
        latest = await self.data_class.find_one(
            {
                "resource_id": resource_id,
                "version_info.is_latest": True,
            },
        )

        if not latest or not latest.version_info:
            return "1.0.0"

        # Parse current version and increment patch
        try:
            parts = latest.version_info.version.split(".")
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{major}.{minor}.{patch + 1}"
        except (ValueError, IndexError):
            return "1.0.0"

    async def _update_version_chain_atomic(
        self,
        new_version: T,
        session: AsyncIOMotorClientSession,
    ) -> None:
        """Update version chain atomically within a transaction.

        Args:
            new_version: New version being added
            session: MongoDB session for transaction

        """
        if new_version.version_info.is_latest:
            # Mark previous versions as not latest
            collection = self.data_class.get_motor_collection()
            await collection.update_many(
                {
                    "resource_id": new_version.resource_id,
                    "resource_type": new_version.resource_type,
                    "version_info.is_latest": True,
                    "_id": {"$ne": new_version.id},
                },
                {
                    "$set": {
                        "version_info.is_latest": False,
                        "version_info.superseded_by": new_version.id,
                    },
                },
                session=session,
            )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics from unified cache

        """
        if self._cache:
            # This will be handled by the unified cache
            return {"status": "using_unified_cache"}
        return {"status": "cache_not_initialized"}


# Global instances for common data types
corpus_version_manager = VersionedDataManager(CorpusVersionedData)
dictionary_version_manager = VersionedDataManager(DictionaryVersionedData)
semantic_version_manager = VersionedDataManager(SemanticVersionedData)
literature_version_manager = VersionedDataManager(LiteratureVersionedData)


# Factory functions for manager access
def get_corpus_version_manager() -> VersionedDataManager[CorpusVersionedData]:
    """Get the global corpus version manager instance."""
    return corpus_version_manager


def get_dictionary_version_manager() -> VersionedDataManager[DictionaryVersionedData]:
    """Get the global dictionary version manager instance."""
    return dictionary_version_manager


def get_semantic_version_manager() -> VersionedDataManager[SemanticVersionedData]:
    """Get the global semantic version manager instance."""
    return semantic_version_manager


def get_literature_version_manager() -> VersionedDataManager[LiteratureVersionedData]:
    """Get the global literature version manager instance."""
    return literature_version_manager
