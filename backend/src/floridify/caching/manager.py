"""Versioned data manager for unified caching and content management."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, TypeVar

from beanie import PydanticObjectId

from ..models.registry import get_model_class as get_versioned_model_class
from ..utils.logging import get_logger
from .core import GlobalCacheManager, get_global_cache
from .filesystem import FilesystemBackend
from .models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
    VersionConfig,
    VersionInfo,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseVersionedData)


class VersionedDataManager:
    """Manages versioned data with proper typing and performance optimization."""

    def __init__(self) -> None:
        """Initialize with cache integration."""
        self.cache: GlobalCacheManager[FilesystemBackend] | None = (
            None  # Will be initialized lazily (GlobalCacheManager)
        )
        self.lock = asyncio.Lock()

    async def save(
        self,
        resource_id: str,
        resource_type: ResourceType,
        namespace: CacheNamespace,
        content: Any,
        config: VersionConfig = VersionConfig(),
        metadata: dict[str, Any] | None = None,
        dependencies: list[PydanticObjectId] | None = None,
    ) -> BaseVersionedData:
        """Save with versioning and optimal serialization."""
        # Single serialization with sorted keys and ObjectId handling
        content_str = json.dumps(content, sort_keys=True, default=self._json_encoder)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        # Check for duplicate
        if not config.force_rebuild:
            existing = await self._find_by_hash(resource_id, content_hash)
            if existing:
                logger.debug(f"Found existing version for {resource_id} with same content")
                return existing

        # Get latest for version increment
        latest = None
        if config.increment_version:
            latest = await self.get_latest(
                resource_id, resource_type, use_cache=not config.force_rebuild
            )

        new_version = config.version or (
            self._increment_version(latest.version_info.version)
            if latest and config.increment_version
            else "1.0.0"
        )

        # Create versioned instance
        model_class = self._get_model_class(resource_type)

        # Prepare constructor parameters
        constructor_params = {
            "resource_id": resource_id,
            "resource_type": resource_type,
            "namespace": namespace,
            "version_info": VersionInfo(
                version=new_version,
                data_hash=content_hash,
                is_latest=True,
                supersedes=latest.id if latest else None,
                dependencies=dependencies or [],
            ),
            "ttl": config.ttl,
        }

        # Handle metadata - extract model-specific fields vs generic metadata
        combined_metadata = {**config.metadata, **(metadata or {})}
        generic_metadata = {}

        # For corpus models, extract corpus-specific fields
        if resource_type == ResourceType.CORPUS:
            corpus_fields = [
                "corpus_name",
                "corpus_type",
                "language",
                "parent_corpus_id",
                "child_corpus_ids",
                "is_master",
            ]
            for field in corpus_fields:
                if field in combined_metadata:
                    # Convert enum values if needed
                    value = combined_metadata.pop(field)
                    if field == "corpus_type" and isinstance(value, str):
                        from ..corpus.models import CorpusType

                        value = CorpusType(value)
                    elif field == "language" and isinstance(value, str):
                        from ..models.base import Language

                        value = Language(value)
                    constructor_params[field] = value

            # Remaining metadata goes to generic metadata
            generic_metadata = combined_metadata
        elif resource_type == ResourceType.TRIE:
            # For trie models, extract corpus_id
            if "corpus_id" in combined_metadata:
                constructor_params["corpus_id"] = combined_metadata.pop("corpus_id")
            # Remaining metadata goes to generic metadata
            generic_metadata = combined_metadata
        else:
            # For other resource types, all metadata is generic
            generic_metadata = combined_metadata

        constructor_params["metadata"] = generic_metadata

        versioned = model_class(**constructor_params)

        # Set content with automatic storage strategy
        await versioned.set_content(content)

        # Atomic save with version chain update
        async with self.lock:
            if latest and config.increment_version:
                latest.version_info.is_latest = False
                latest.version_info.superseded_by = versioned.id
                await latest.save()

            await versioned.save()

            # Tree structures handled by TreeCorpusManager for corpus types

        # Cache if enabled
        if config.use_cache:
            if self.cache is None:
                self.cache = await get_global_cache()
            cache_key = f"{resource_type.value}:{resource_id}"
            await self.cache.set(namespace, cache_key, versioned, config.ttl)

        logger.info(f"Saved {resource_type.value} '{resource_id}' version {new_version}")
        return versioned

    async def get_latest(
        self,
        resource_id: str,
        resource_type: ResourceType,
        use_cache: bool = True,
        config: VersionConfig = VersionConfig(),
    ) -> BaseVersionedData | None:
        """Get latest version with proper typing."""
        namespace = self._get_namespace(resource_type)

        # Check cache unless forced
        if use_cache and not config.force_rebuild:
            cache_key = f"{resource_type.value}:{resource_id}"

            # Handle specific version request
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"

            if self.cache is None:
                self.cache = await get_global_cache()
            cached = await self.cache.get(namespace, cache_key)
            if cached:
                logger.debug(f"Cache hit for {cache_key}")
                return cached  # type: ignore[no-any-return]

        # Query database
        model_class = self._get_model_class(resource_type)

        if config.version:
            # Get specific version
            result = await model_class.find_one(
                {"resource_id": resource_id, "version_info.version": config.version}
            )
        else:
            # Get latest
            result = await model_class.find_one(
                {"resource_id": resource_id, "version_info.is_latest": True}
            )

        # Cache result
        if result and use_cache:
            cache_key = f"{resource_type.value}:{resource_id}"
            if config.version:
                cache_key = f"{cache_key}:v{config.version}"
            if self.cache is None:
                self.cache = await get_global_cache()
            await self.cache.set(namespace, cache_key, result, result.ttl)

        return result

    async def get_by_version(
        self,
        resource_id: str,
        resource_type: ResourceType,
        version: str,
        use_cache: bool = True,
    ) -> BaseVersionedData | None:
        """Get specific version of a resource."""
        config = VersionConfig(version=version, use_cache=use_cache)
        return await self.get_latest(resource_id, resource_type, use_cache, config)

    async def list_versions(self, resource_id: str, resource_type: ResourceType) -> list[str]:
        """List all versions of a resource."""
        model_class = self._get_model_class(resource_type)
        results = await model_class.find({"resource_id": resource_id}).to_list()
        return [r.version_info.version for r in results]

    async def delete_version(
        self, resource_id: str, resource_type: ResourceType, version: str
    ) -> bool:
        """Delete a specific version."""
        model_class = self._get_model_class(resource_type)
        result = await model_class.find_one(
            {"resource_id": resource_id, "version_info.version": version}
        )

        if result:
            # Update version chain
            if result.version_info.superseded_by:
                next_version = await model_class.get(result.version_info.superseded_by)
                if next_version:
                    next_version.version_info.supersedes = result.version_info.supersedes
                    await next_version.save()

            if result.version_info.supersedes:
                prev_version = await model_class.get(result.version_info.supersedes)
                if prev_version:
                    prev_version.version_info.superseded_by = result.version_info.superseded_by
                    if result.version_info.is_latest:
                        prev_version.version_info.is_latest = True
                    await prev_version.save()

            await result.delete()

            # Clear cache
            namespace = self._get_namespace(resource_type)
            cache_key = f"{resource_type.value}:{resource_id}:v{version}"
            if self.cache is None:
                self.cache = await get_global_cache()
            await self.cache.delete(namespace, cache_key)

            logger.info(f"Deleted {resource_type.value} '{resource_id}' v{version}")
            return True

        return False

    async def _find_by_hash(self, resource_id: str, content_hash: str) -> BaseVersionedData | None:
        """Find existing version with same content hash."""
        # Check all resource types for deduplication, but skip uninitialized collections
        for resource_type in ResourceType:
            try:
                model_class = self._get_model_class(resource_type)
                # Check if the collection is initialized
                collection = model_class.get_pymongo_collection()
                if collection is None:
                    continue  # Skip uninitialized collections

                result = await model_class.find_one(
                    {"resource_id": resource_id, "version_info.data_hash": content_hash}
                )
                if result:
                    return result
            except Exception:
                # Skip resource types that can't be queried
                continue
        return None

    def _get_model_class(self, resource_type: ResourceType) -> type[BaseVersionedData]:
        """Map resource type enum to model class using registry pattern."""
        return get_versioned_model_class(resource_type)

    def _get_namespace(self, resource_type: ResourceType) -> CacheNamespace:
        """Map resource type enum to namespace."""
        mapping = {
            ResourceType.DICTIONARY: CacheNamespace.DICTIONARY,
            ResourceType.CORPUS: CacheNamespace.CORPUS,
            ResourceType.LANGUAGE: CacheNamespace.LANGUAGE,
            ResourceType.SEMANTIC: CacheNamespace.SEMANTIC,
            ResourceType.LITERATURE: CacheNamespace.LITERATURE,
            ResourceType.TRIE: CacheNamespace.TRIE,
            ResourceType.SEARCH: CacheNamespace.SEARCH,
        }
        return mapping[resource_type]

    def _increment_version(self, version: str) -> str:
        """Increment patch version."""
        major, minor, patch = version.split(".")

        return f"{major}.{minor}.{int(patch) + 1}"

    def _json_encoder(self, obj: Any) -> str:
        """Custom JSON encoder for complex objects like PydanticObjectId."""
        from enum import Enum

        if isinstance(obj, PydanticObjectId):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# Global singleton instance
_version_manager: VersionedDataManager | None = None


def get_version_manager() -> VersionedDataManager:
    """Get the global version manager instance.

    Returns:
        VersionedDataManager singleton
    """
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionedDataManager()

    return _version_manager
