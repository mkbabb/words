"""Abstract base manager class for resource management with versioning support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import TypeVar

from floridify.caching.models import CacheTTL

from .unified import CacheNamespace, UnifiedCache, get_unified
from ..models.versioned import VersionedData
from ..utils.logging import get_logger
from .versioned import VersionConfig, VersionedDataManager

logger = get_logger(__name__)

# Generic types for resource and metadata
T = TypeVar("T")  # Resource type
M = TypeVar("M")  # Metadata type
V = TypeVar("V", bound=VersionedData)  # Versioned data type


class BaseManager[T, M](ABC):
    """Abstract base class for resource managers with unified versioning.

    Provides common functionality for all resource managers including:
    - Version management through VersionedDataManager
    - Cache configuration with appropriate TTLs
    - Common cleanup and resource reconstruction patterns
    - KISS principle - lean and practical implementation
    """

    def __init__(self) -> None:
        """Initialize the base manager."""
        self._initialized = False
        self._cache: UnifiedCache | None = None

    async def _get_cache(self) -> UnifiedCache:
        """Get the unified cache instance."""
        if self._cache is None:
            self._cache = await get_unified()
        return self._cache

    @property
    @abstractmethod
    def cache_namespace(self) -> CacheNamespace:
        """Get the cache namespace this manager handles."""

    @property
    def cache_ttl(self) -> timedelta | None:
        return CacheTTL[self.cache_namespace.name].value

    @abstractmethod
    def _get_version_manager(self) -> VersionedDataManager:
        """Get the version manager for this resource type."""

    @abstractmethod
    async def _reconstruct_resource(self, versioned_data: V) -> T | None:
        """Reconstruct the resource from versioned data.

        Args:
            versioned_data: The versioned data to reconstruct from

        Returns:
            Reconstructed resource or None if failed

        """

    async def get(
        self,
        resource_id: str,
        use_ttl: bool = True,
    ) -> T | None:
        """Get a resource by ID with caching support.

        Args:
            resource_id: The resource identifier
            use_ttl: Whether to use TTL for caching

        Returns:
            Resource instance or None if not found

        """
        # Get cache instance
        cache = await self._get_cache()

        # Check cache first
        cached = await cache.get(self.cache_namespace, resource_id)
        if cached is not None:
            return cached

        # Configure versioning
        config = self._create_version_config(use_ttl)

        # Load from versioned storage
        version_manager = self._get_version_manager()
        versioned = await version_manager.get_latest(
            resource_id=resource_id,
            resource_type=self.cache_namespace.value,
            config=config,
        )

        if versioned:
            # Reconstruct resource from versioned data
            resource = await self._reconstruct_resource(versioned)
            if resource:
                # Cache the resource
                ttl = self.cache_ttl if use_ttl else None
                await cache.set(self.cache_namespace, resource_id, resource, ttl=ttl)
                return resource

        return None

    async def cleanup_versions(
        self,
        resource_id: str | None = None,
        keep_count: int = 5,
    ) -> int:
        """Clean up old versions of resources.

        Args:
            resource_id: Optional resource ID to clean up (None for all)
            keep_count: Number of versions to keep

        Returns:
            Total number of versions deleted

        """
        version_manager = self._get_version_manager()

        if resource_id:
            return await version_manager.cleanup_versions(
                resource_id=resource_id,
                resource_type=self.cache_namespace.value,
                keep_count=keep_count,
            )
        # Clean up all resources of this type
        return await version_manager.cleanup_all_versions(
            resource_type=self.cache_namespace.value,
            keep_count=keep_count,
        )

    def _create_version_config(self, use_ttl: bool = True) -> VersionConfig:
        """Create version configuration with appropriate TTL.

        Args:
            use_ttl: Whether to use TTL for caching

        Returns:
            Configured VersionConfig instance

        """
        ttl = self.cache_ttl if use_ttl else None
        return VersionConfig(
            save_versions=False,
            ttl=ttl,
        )


__all__ = [
    "BaseManager",
]
