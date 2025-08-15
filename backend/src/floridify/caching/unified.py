"""Unified caching system with integrated memory TTL and filesystem backends.

Provides a streamlined cache interface with automatic cascade:
Memory TTL → Filesystem → Cache Miss

KISS principle: Simple two-tier caching with per-namespace memory limits.
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import timedelta
from typing import Any

from ..utils.logging import get_logger
from .compression import (
    deserialize_with_decompression,
    serialize_with_compression,
)
from .core import CacheBackend, CacheMetadata
from .filesystem import FilesystemCacheBackend
from .models import CacheNamespace, CompressionType

logger = get_logger(__name__)


class NamespaceConfig:
    """Configuration for per-namespace memory limits and TTL."""

    def __init__(
        self,
        max_memory_items: int = 100,
        default_ttl: timedelta | None = None,
        compression_enabled: bool = True,
    ):
        """Initialize namespace configuration.

        Args:
            max_memory_items: Maximum items to keep in memory for this namespace
            default_ttl: Default TTL for items in this namespace
            compression_enabled: Whether to use compression for filesystem storage

        """
        self.max_memory_items = max_memory_items
        self.default_ttl = default_ttl
        self.compression_enabled = compression_enabled


class NamespaceMemoryCache:
    """Memory cache for a specific namespace with LRU eviction."""

    def __init__(self, namespace: str, config: NamespaceConfig):
        """Initialize namespace memory cache.

        Args:
            namespace: The namespace name
            config: Configuration for this namespace

        """
        self.namespace = namespace
        self.config = config
        self._cache: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        """Get value from namespace memory cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None

        """
        async with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache.pop(key)

            # Check expiry
            if expiry is not None:
                import time

                if time.time() > expiry:
                    return None

            # Move to end (most recently used)
            self._cache[key] = (value, expiry)
            return value

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Set value in namespace memory cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override

        """
        async with self._lock:
            # Calculate expiry
            expiry = None
            if ttl or self.config.default_ttl:
                import time

                ttl_to_use = ttl or self.config.default_ttl
                if ttl_to_use:
                    expiry = time.time() + ttl_to_use.total_seconds()

            # Remove if exists (to update position)
            if key in self._cache:
                del self._cache[key]

            # Add to end
            self._cache[key] = (value, expiry)

            # Evict oldest if over limit
            while len(self._cache) > self.config.max_memory_items:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> bool:
        """Delete key from namespace memory cache.

        Args:
            key: Cache key

        Returns:
            True if deleted

        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        """Clear all entries in this namespace.

        Returns:
            Number of entries cleared

        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed

        """
        import time

        current_time = time.time()

        async with self._lock:
            expired_keys = [
                key
                for key, (_, expiry) in self._cache.items()
                if expiry is not None and current_time > expiry
            ]

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics

        """
        return {
            "namespace": self.namespace,
            "size": len(self._cache),
            "max_size": self.config.max_memory_items,
            "has_default_ttl": self.config.default_ttl is not None,
        }


# Default namespace configurations
DEFAULT_NAMESPACE_CONFIGS = {
    CacheNamespace.SEMANTIC: NamespaceConfig(
        max_memory_items=50,
        default_ttl=timedelta(days=7),
        compression_enabled=True,
    ),
    CacheNamespace.CORPUS: NamespaceConfig(
        max_memory_items=100,
        default_ttl=timedelta(days=30),
        compression_enabled=True,
    ),
    CacheNamespace.VOCABULARY: NamespaceConfig(
        max_memory_items=200,
        default_ttl=None,  # No expiry for vocabulary
        compression_enabled=True,
    ),
    CacheNamespace.API: NamespaceConfig(
        max_memory_items=500,
        default_ttl=timedelta(hours=24),
        compression_enabled=True,
    ),
    CacheNamespace.SEARCH: NamespaceConfig(
        max_memory_items=300,
        default_ttl=timedelta(hours=1),
        compression_enabled=False,
    ),
    CacheNamespace.TRIE: NamespaceConfig(
        max_memory_items=50,
        default_ttl=timedelta(days=7),
        compression_enabled=True,
    ),
    CacheNamespace.COMPUTE: NamespaceConfig(
        max_memory_items=100,
        default_ttl=timedelta(days=7),
        compression_enabled=True,
    ),
    CacheNamespace.OPENAI: NamespaceConfig(
        max_memory_items=200,
        default_ttl=timedelta(days=30),
        compression_enabled=True,
    ),
}


class UnifiedCache(CacheBackend[Any]):
    """Streamlined unified cache with per-namespace memory limits.

    Architecture: Namespace Memory (L1) → Filesystem (L2) → Cache Miss

    Features:
    - Per-namespace memory cache with configurable limits
    - L2 filesystem persistence
    - Automatic cascade and promotion
    - Namespace isolation
    - Tag-based invalidation
    - Built-in statistics and monitoring
    """

    def __init__(
        self,
        namespace_configs: dict[str, NamespaceConfig] | None = None,
    ) -> None:
        """Initialize unified cache with per-namespace configuration.

        Args:
            namespace_configs: Optional custom namespace configurations

        """
        # Merge default and custom configs
        self._namespace_configs: dict[CacheNamespace | str, NamespaceConfig] = {}
        # Add default configs
        for k, v in DEFAULT_NAMESPACE_CONFIGS.items():
            self._namespace_configs[k] = v
        # Add custom configs
        if namespace_configs:
            for key, value in namespace_configs.items():
                self._namespace_configs[key] = value

        # L1: Per-namespace memory caches
        self._memory_caches: dict[str, NamespaceMemoryCache] = {}
        self._cache_lock = asyncio.Lock()

        # L2: Persistent filesystem cache
        self._filesystem_backend: FilesystemCacheBackend[Any] = FilesystemCacheBackend()

        # Cleanup task
        self._cleanup_task: asyncio.Task[None] | None = None
        self._cleanup_interval = 300.0  # 5 minutes

        logger.info("Initialized unified cache with per-namespace memory limits")

    def _get_namespace_config(self, namespace: str) -> NamespaceConfig:
        """Get configuration for a namespace.

        Args:
            namespace: Namespace name

        Returns:
            Namespace configuration

        """
        # Try to match enum value
        for ns_enum in CacheNamespace:
            if ns_enum.value == namespace:
                if ns_enum in self._namespace_configs:
                    return self._namespace_configs[ns_enum]
                break

        # Default configuration for unknown namespaces
        return NamespaceConfig(
            max_memory_items=100,
            default_ttl=timedelta(hours=1),
            compression_enabled=False,
        )

    async def _get_memory_cache(self, namespace: str) -> NamespaceMemoryCache:
        """Get or create memory cache for namespace.

        Args:
            namespace: Namespace name

        Returns:
            Memory cache for namespace

        """
        if namespace not in self._memory_caches:
            async with self._cache_lock:
                if namespace not in self._memory_caches:
                    config = self._get_namespace_config(namespace)
                    self._memory_caches[namespace] = NamespaceMemoryCache(namespace, config)
                    logger.debug(f"Created memory cache for namespace: {namespace}")

        return self._memory_caches[namespace]

    async def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("Started cache cleanup task")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)

                total_cleaned = 0
                for cache in self._memory_caches.values():
                    cleaned = await cache.cleanup_expired()
                    total_cleaned += cleaned

                if total_cleaned > 0:
                    logger.debug(f"Cleaned up {total_cleaned} expired cache entries")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")

    async def get(self, namespace: str, key: str, default: Any | None = None) -> Any | None:
        """Get value from cache with cascade: Memory → Filesystem → Miss.

        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            default: Default value if not found

        Returns:
            Cached value or default

        """
        # Ensure cleanup task is running
        await self._start_cleanup_task()

        # L1: Check namespace memory cache
        memory_cache = await self._get_memory_cache(namespace)
        memory_value = await memory_cache.get(key)
        if memory_value is not None:
            logger.debug(f"L1 cache hit: {namespace}:{key}")
            return memory_value

        # L2: Check filesystem cache
        fs_value = await self._filesystem_backend.get(namespace, key, default)
        if fs_value is not default:
            # Promote to memory cache
            await memory_cache.set(key, fs_value)
            logger.debug(f"L2 cache hit (promoted): {namespace}:{key}")
            return fs_value

        # Cache miss
        logger.debug(f"Cache miss: {namespace}:{key}")
        return default

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: timedelta | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set value in both cache layers.

        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            value: Value to cache
            ttl: Time to live (must be timedelta)
            tags: Optional tags for batch operations

        """
        # Ensure cleanup task is running
        await self._start_cleanup_task()

        # Get namespace memory cache
        memory_cache = await self._get_memory_cache(namespace)

        # Set in both layers
        await memory_cache.set(key, value, ttl)
        await self._filesystem_backend.set(namespace, key, value, ttl, tags)

        logger.debug(f"Cached (L1+L2): {namespace}:{key}")

    async def set_compressed(
        self,
        namespace: str,
        key: str,
        value: Any,
        compression_type: CompressionType = CompressionType.ZLIB,
        ttl: timedelta | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set value with compression in filesystem layer.

        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            value: Value to cache
            compression_type: Type of compression to use
            ttl: Time to live (must be timedelta)
            tags: Optional tags for batch operations

        """
        # Ensure cleanup task is running
        await self._start_cleanup_task()

        # Get namespace config
        config = self._get_namespace_config(namespace)

        if config.compression_enabled:
            # Serialize and compress the value
            compressed_data, metadata = serialize_with_compression(value, compression_type)

            # Store compressed data with metadata
            cache_entry = {"data": compressed_data, "metadata": metadata}

            # Store uncompressed in memory for fast access
            memory_cache = await self._get_memory_cache(namespace)
            await memory_cache.set(key, value, ttl)

            # Store compressed in filesystem
            await self._filesystem_backend.set(
                namespace, f"{key}_compressed", cache_entry, ttl, tags
            )

            logger.debug(
                f"Cached compressed (L1+L2): {namespace}:{key} (ratio: {metadata.compression_ratio:.2f})",
            )
        else:
            # No compression, store normally
            await self.set(namespace, key, value, ttl, tags)

    async def get_compressed(
        self,
        namespace: str,
        key: str,
        default: Any | None = None,
    ) -> Any | None:
        """Get value with compression support.

        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            default: Default value if not found

        Returns:
            Cached value or default

        """
        # Ensure cleanup task is running
        await self._start_cleanup_task()

        # L1: Check memory cache first
        memory_cache = await self._get_memory_cache(namespace)
        memory_value = await memory_cache.get(key)
        if memory_value is not None:
            logger.debug(f"L1 cache hit: {namespace}:{key}")
            return memory_value

        # L2: Check filesystem cache for compressed data
        cache_entry = await self._filesystem_backend.get(namespace, f"{key}_compressed", None)
        if cache_entry is not None:
            try:
                # Decompress and deserialize
                compressed_data = cache_entry["data"]
                metadata = (
                    CacheMetadata(**cache_entry["metadata"])
                    if isinstance(cache_entry["metadata"], dict)
                    else cache_entry["metadata"]
                )

                value = deserialize_with_decompression(compressed_data, metadata)

                # Promote to memory cache
                await memory_cache.set(key, value)
                logger.debug(f"L2 compressed cache hit (promoted): {namespace}:{key}")
                return value
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Failed to decompress cache entry {namespace}:{key}: {e}")

        # Try regular get as fallback
        return await self.get(namespace, key, default)

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete specific cache entry from both layers.

        Args:
            namespace: Cache namespace
            key: Cache key

        Returns:
            True if entry was deleted from either layer

        """
        # Delete from memory cache
        memory_deleted = False
        if namespace in self._memory_caches:
            memory_cache = self._memory_caches[namespace]
            memory_deleted = await memory_cache.delete(key)

        # Delete from filesystem
        fs_deleted = await self._filesystem_backend.delete(namespace, key)
        # Also try to delete compressed version
        fs_compressed_deleted = await self._filesystem_backend.delete(
            namespace, f"{key}_compressed"
        )

        deleted = memory_deleted or fs_deleted or fs_compressed_deleted
        if deleted:
            logger.debug(f"Deleted (L1+L2): {namespace}:{key}")

        return deleted

    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all entries in a namespace.

        Args:
            namespace: Namespace to invalidate

        Returns:
            Number of entries invalidated

        """
        memory_count = 0

        # Clear namespace memory cache
        if namespace in self._memory_caches:
            memory_cache = self._memory_caches[namespace]
            memory_count = await memory_cache.clear()

        # Clear filesystem entries
        fs_count = await self._filesystem_backend.invalidate_namespace(namespace)

        total_count = memory_count + fs_count
        logger.info(
            f"Invalidated {total_count} entries in namespace: {namespace} (L1: {memory_count}, L2: {fs_count})",
        )

        return total_count

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """Invalidate entries by tags (filesystem only).

        Args:
            tags: Tags to invalidate

        Returns:
            Number of entries invalidated

        """
        count = 0
        for tag in tags:
            count += await self._filesystem_backend.invalidate_tag(tag)

        if count > 0:
            logger.info(f"Invalidated {count} entries with tags: {tags}")

        return count

    async def clear(self) -> None:
        """Clear both cache layers completely."""
        # Clear all memory caches
        for cache in self._memory_caches.values():
            await cache.clear()
        self._memory_caches.clear()

        # Clear filesystem
        await self._filesystem_backend.clear()

        logger.info("Cache cleared (L1+L2)")

    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]:
        """Get comprehensive cache statistics.

        Args:
            namespace: Optional namespace to filter stats

        Returns:
            Combined cache statistics

        """
        if namespace:
            memory_stats = {}
            if namespace in self._memory_caches:
                memory_stats = self._memory_caches[namespace].get_stats()
        else:
            memory_stats = {ns: cache.get_stats() for ns, cache in self._memory_caches.items()}

        fs_stats = await self._filesystem_backend.get_stats(namespace)

        return {
            "memory_l1": memory_stats,
            "filesystem_l2": fs_stats,
            "total_namespaces": len(self._memory_caches),
            "architecture": "Per-namespace Memory + Filesystem",
        }

    async def exists(self, namespace: str, key: str) -> bool:
        """Check if key exists in either cache layer."""
        # Check memory first (faster)
        if namespace in self._memory_caches:
            memory_cache = self._memory_caches[namespace]
            if await memory_cache.get(key) is not None:
                return True

        # Check filesystem
        return await self._filesystem_backend.exists(namespace, key)

    async def get_or_set(
        self,
        namespace: str,
        key: str,
        factory: Any,
        ttl: timedelta | None = None,
        tags: list[str] | None = None,
    ) -> Any:
        """Get value from cache or compute and set if not found."""
        value = await self.get(namespace, key)
        if value is None:
            if callable(factory):
                value = await factory() if hasattr(factory, "__await__") else factory()
            else:
                value = factory
            await self.set(namespace, key, value, ttl, tags)
        return value

    async def close(self) -> None:
        """Close cache connections and cleanup tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if hasattr(self._filesystem_backend, "close"):
            await self._filesystem_backend.close()

        logger.info("Unified cache closed")

    async def __aenter__(self) -> UnifiedCache:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


# Global cache instance
_cache: UnifiedCache | None = None
_cache_lock = asyncio.Lock()


async def get_unified(force_new: bool = False) -> UnifiedCache:
    """Get or create global unified cache instance.

    Args:
        force_new: Force creation of new instance

    Returns:
        Global UnifiedCache instance

    """
    global _cache

    if force_new:
        if _cache:
            await _cache.close()
        _cache = None

    if _cache is None:
        async with _cache_lock:
            if _cache is None:
                _cache = UnifiedCache()
                logger.info("Created global unified cache instance")

    return _cache


async def invalidate_cache_namespace(namespace: str) -> int:
    """Invalidate all entries in a namespace.

    Args:
        namespace: Namespace to invalidate

    Returns:
        Number of entries invalidated

    """
    cache = await get_unified()
    return await cache.invalidate_namespace(namespace)


async def clear_all_cache() -> None:
    """Clear entire cache."""
    cache = await get_unified()
    await cache.clear()


async def shutdown_unified() -> None:
    """Shutdown global unified cache."""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None
        logger.info("Shutdown global unified cache")


__all__ = [
    "DEFAULT_NAMESPACE_CONFIGS",
    "NamespaceConfig",
    "UnifiedCache",
    "clear_all_cache",
    "get_unified",
    "invalidate_cache_namespace",
    "shutdown_unified",
]
