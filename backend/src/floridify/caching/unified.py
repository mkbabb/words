"""
Unified caching system with integrated memory TTL and filesystem backends.

Provides a streamlined cache interface with automatic cascade:
Memory TTL → Filesystem → Cache Miss

KISS principle: Simple two-tier caching with no pluggable backends.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from ..utils.logging import get_logger
from .compression import (
    deserialize_with_decompression,
    serialize_with_compression,
)
from .core import CacheBackend, CacheMetadata, CompressionType
from .filesystem import FilesystemCacheBackend
from .memory import InMemoryTTLCache

logger = get_logger(__name__)


class UnifiedCache(CacheBackend[Any]):
    """
    Streamlined unified cache with integrated memory TTL and filesystem backends.
    
    Architecture: Memory TTL (L1) → Filesystem (L2) → Cache Miss
    
    Features:
    - Integrated L1 memory cache with TTL
    - L2 filesystem persistence 
    - Automatic cascade and promotion
    - Namespace isolation
    - Tag-based invalidation
    - Built-in statistics and monitoring
    """

    def __init__(self) -> None:
        """Initialize unified cache with memory TTL and filesystem backends."""
        # L1: Fast in-memory TTL cache
        self._memory_cache = InMemoryTTLCache[Any](
            max_instances=200,  # Higher limit for unified cache
            default_ttl_seconds=3600.0,  # 1 hour default
            name="unified_l1"
        )
        
        # L2: Persistent filesystem cache
        self._filesystem_backend: FilesystemCacheBackend[Any] = FilesystemCacheBackend()
        
        # Initialize cleanup task
        self._cleanup_started = False
        self._init_lock = asyncio.Lock()
        
        logger.info("Initialized unified cache (Memory TTL + Filesystem)")

    async def _ensure_cleanup_started(self) -> None:
        """Ensure cleanup task is started."""
        if not self._cleanup_started:
            async with self._init_lock:
                if not self._cleanup_started:
                    await self._memory_cache.start_cleanup_task()
                    self._cleanup_started = True

    def _make_cache_key(self, namespace: str, key: str) -> str:
        """Create unified cache key from namespace and key."""
        return f"{namespace}:{key}"

    async def get(self, namespace: str, key: str, default: Any | None = None) -> Any | None:
        """
        Get value from cache with cascade: Memory TTL → Filesystem → Miss.
        
        Args:
            namespace: Cache namespace (e.g., 'vocabulary', 'semantic')
            key: Cache key within namespace
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        await self._ensure_cleanup_started()
        
        cache_key = self._make_cache_key(namespace, key)
        
        # L1: Check memory TTL cache first
        memory_value = await self._memory_cache.get(cache_key)
        if memory_value is not None:
            logger.debug(f"L1 cache hit: {namespace}:{key}")
            return memory_value
        
        # L2: Check filesystem cache
        fs_value = await self._filesystem_backend.get(namespace, key, default)
        if fs_value is not default:
            # Promote to memory cache
            await self._memory_cache.set(cache_key, fs_value)
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
        """
        Set value in both cache layers.
        
        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            value: Value to cache
            ttl: Time to live
            tags: Optional tags for batch operations
        """
        await self._ensure_cleanup_started()
        
        cache_key = self._make_cache_key(namespace, key)
        ttl_seconds = ttl.total_seconds() if ttl else None
        
        # Set in both layers
        await self._memory_cache.set(cache_key, value, ttl_seconds)
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
        """
        Set value with compression in filesystem layer only.
        
        Args:
            namespace: Cache namespace
            key: Cache key within namespace  
            value: Value to cache
            compression_type: Type of compression to use
            ttl: Time to live
            tags: Optional tags for batch operations
        """
        await self._ensure_cleanup_started()
        
        # Serialize and compress the value
        compressed_data, metadata = serialize_with_compression(value, compression_type)
        
        # Store compressed data with metadata
        cache_entry = {
            'data': compressed_data,
            'metadata': metadata
        }
        
        cache_key = self._make_cache_key(namespace, key)
        ttl_seconds = ttl.total_seconds() if ttl else None
        
        # Store uncompressed in memory for fast access
        await self._memory_cache.set(cache_key, value, ttl_seconds)
        
        # Store compressed in filesystem
        await self._filesystem_backend.set(namespace, f"{key}_compressed", cache_entry, ttl, tags)
        
        logger.debug(f"Cached compressed (L1+L2): {namespace}:{key} (ratio: {metadata.compression_ratio:.2f})")

    async def get_compressed(self, namespace: str, key: str, default: Any | None = None) -> Any | None:
        """
        Get value with compression support.
        
        Args:
            namespace: Cache namespace
            key: Cache key within namespace
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        await self._ensure_cleanup_started()
        
        cache_key = self._make_cache_key(namespace, key)
        
        # L1: Check memory cache first  
        memory_value = await self._memory_cache.get(cache_key)
        if memory_value is not None:
            logger.debug(f"L1 cache hit: {namespace}:{key}")
            return memory_value
        
        # L2: Check filesystem cache for compressed data
        cache_entry = await self._filesystem_backend.get(namespace, f"{key}_compressed", None)
        if cache_entry is not None:
            try:
                # Decompress and deserialize
                compressed_data = cache_entry['data']
                metadata = CacheMetadata(**cache_entry['metadata']) if isinstance(cache_entry['metadata'], dict) else cache_entry['metadata']
                
                value = deserialize_with_decompression(compressed_data, metadata)
                
                # Promote to memory cache
                await self._memory_cache.set(cache_key, value)
                logger.debug(f"L2 compressed cache hit (promoted): {namespace}:{key}")
                return value
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Failed to decompress cache entry {namespace}:{key}: {e}")
        
        # Cache miss
        logger.debug(f"Cache miss: {namespace}:{key}")
        return default

    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete specific cache entry from both layers.
        
        Args:
            namespace: Cache namespace
            key: Cache key
            
        Returns:
            True if entry was deleted from either layer
        """
        cache_key = self._make_cache_key(namespace, key)
        
        # Delete from both layers
        memory_deleted = await self._memory_cache.delete(cache_key)
        fs_deleted = await self._filesystem_backend.delete(namespace, key)
        
        deleted = memory_deleted or fs_deleted
        if deleted:
            logger.debug(f"Deleted (L1+L2): {namespace}:{key}")
        
        return deleted

    async def invalidate_namespace(self, namespace: str) -> int:
        """
        Invalidate all entries in a namespace.
        
        Args:
            namespace: Namespace to invalidate
            
        Returns:
            Number of entries invalidated
        """
        # Clear memory cache entries with this namespace prefix
        memory_count = 0
        memory_keys = list(self._memory_cache._cache.keys())
        for cache_key in memory_keys:
            if cache_key.startswith(f"{namespace}:"):
                await self._memory_cache.delete(cache_key)
                memory_count += 1
        
        # Clear filesystem entries
        fs_count = await self._filesystem_backend.invalidate_namespace(namespace)
        
        total_count = memory_count + fs_count
        logger.info(f"Invalidated {total_count} entries in namespace: {namespace} (L1: {memory_count}, L2: {fs_count})")
        
        return total_count

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """
        Invalidate entries by tags (filesystem only - memory cache doesn't support tags).
        
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
        await self._memory_cache.clear()
        await self._filesystem_backend.clear()
        logger.info("Cache cleared (L1+L2)")

    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Args:
            namespace: Optional namespace to filter stats
            
        Returns:
            Combined cache statistics
        """
        memory_stats = self._memory_cache.get_stats()
        fs_stats = await self._filesystem_backend.get_stats(namespace)
        
        return {
            "memory_l1": memory_stats,
            "filesystem_l2": fs_stats,
            "total_layers": 2,
            "architecture": "Memory TTL + Filesystem",
        }

    async def exists(self, namespace: str, key: str) -> bool:
        """Check if key exists in either cache layer."""
        cache_key = self._make_cache_key(namespace, key)
        
        # Check memory first (faster)
        memory_exists = await self._memory_cache.get(cache_key) is not None
        if memory_exists:
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
        await self._memory_cache.stop_cleanup_task()
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
    """
    Get or create global unified cache instance.
    
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
    """
    Invalidate all entries in a namespace.
    
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
    "UnifiedCache",
    "get_unified",
    "invalidate_cache_namespace",
    "clear_all_cache",
    "shutdown_unified",
]