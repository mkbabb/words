"""Global cache manager with two-tier caching (L1 memory + L2 filesystem)."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Generic, TypeVar

from ..utils.logging import get_logger
from .compression import compress_data, decompress_data
from .config import DEFAULT_CONFIGS
from .filesystem import FilesystemBackend
from .keys import generate_resource_key
from .models import (
    BaseVersionedData,
    CacheNamespace,
    CompressionType,
    ContentLocation,
    StorageType,
    VersionConfig,
)
from .serialize import CacheStats, estimate_binary_size, serialize_content

logger = get_logger(__name__)

# Type variable for backend
T = TypeVar("T", bound=FilesystemBackend)


class NamespaceConfig:
    """Configuration for a cache namespace.

    Uses OrderedDict for LRU cache with O(1) move_to_end operations.
    Oldest items are at the front, newest at the back.
    """

    def __init__(
        self,
        name: CacheNamespace,
        memory_limit: int = 100,
        memory_ttl: timedelta | None = None,
        disk_ttl: timedelta | None = None,
        compression: CompressionType | None = None,
    ):
        self.name = name
        self.memory_limit = memory_limit
        self.memory_ttl = memory_ttl
        self.disk_ttl = disk_ttl
        self.compression = compression
        # OrderedDict for O(1) LRU operations via move_to_end()
        self.memory_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.lock = asyncio.Lock()
        # Immutable cache stats for functional updates
        self.stats = CacheStats()


class GlobalCacheManager(Generic[T]):  # noqa: UP046
    """Two-tier cache: L1 memory + L2 filesystem.

    Optimized for minimal serialization overhead.
    """

    def __init__(self, l2_backend: T):
        """Initialize with filesystem backend.

        Args:
            l2_backend: Filesystem backend for L2 storage

        """
        self.namespaces: dict[CacheNamespace, NamespaceConfig] = {}
        self.l2_backend = l2_backend
        self._cleanup_task: asyncio.Task[None] | None = None
        self._init_default_namespaces()

    @staticmethod
    def _make_backend_key(namespace: CacheNamespace, key: str) -> str:
        """Construct backend cache key from namespace and key.

        Args:
            namespace: Cache namespace (enum or string from MongoDB)
            key: Cache key

        Returns:
            Formatted backend key string
        """
        # Handle both enum and string (from MongoDB serialization)
        if isinstance(namespace, str):
            return f"{namespace}:{key}"
        return f"{namespace.value}:{key}"

    def _evict_lru(self, ns: NamespaceConfig, count: int = 1) -> int:
        """Evict least recently used items from namespace.

        Uses OrderedDict.popitem(last=False) for O(1) eviction of oldest items.

        Args:
            ns: Namespace configuration
            count: Number of items to evict (default: 1, None = evict until under limit)

        Returns:
            Number of items evicted
        """
        evictions = 0
        if count is None:
            # Evict until under limit
            while len(ns.memory_cache) >= ns.memory_limit:
                # popitem(last=False) removes and returns oldest (first) item in O(1)
                ns.memory_cache.popitem(last=False)
                ns.stats = ns.stats.increment_evictions()
                evictions += 1
        else:
            # Evict exact count
            for _ in range(count):
                if ns.memory_cache:
                    # popitem(last=False) removes and returns oldest (first) item in O(1)
                    ns.memory_cache.popitem(last=False)
                    ns.stats = ns.stats.increment_evictions()
                    evictions += 1
        return evictions

    async def initialize(self) -> None:
        """Initialize the cache manager."""
        logger.info("GlobalCacheManager initialized")

    def _init_default_namespaces(self) -> None:
        """Initialize namespaces from centralized config.

        Uses immutable configuration from config.py (DEFAULT_CONFIGS).
        Creates mutable NamespaceConfig wrapper for each namespace.
        """
        for namespace, frozen_config in DEFAULT_CONFIGS.items():
            # Create mutable state wrapper from immutable config
            ns_config = NamespaceConfig(
                name=frozen_config.namespace,
                memory_limit=frozen_config.memory_limit,
                memory_ttl=frozen_config.memory_ttl,
                disk_ttl=frozen_config.disk_ttl,
                compression=frozen_config.compression,
            )
            self.namespaces[namespace] = ns_config

    async def get(
        self,
        namespace: CacheNamespace,
        key: str,
        loader: Callable[[], Any] | None = None,
        use_cache: bool = True,
    ) -> Any | None:
        """Two-tier get with optional loader.

        Args:
            namespace: Cache namespace
            key: Cache key
            loader: Optional loader function to call on cache miss
            use_cache: If False, skip cache lookup and call loader directly
        """
        # If use_cache=False, skip cache entirely and call loader
        if not use_cache:
            if loader:
                try:
                    logger.debug(f"Cache bypass: {namespace.value}:{key} (use_cache=False)")
                    return await loader()
                except Exception as e:
                    logger.error(f"Cache loader failed for {namespace.value}:{key}: {e}", exc_info=True)
                    return None
            return None

        ns = self.namespaces.get(namespace)
        if not ns:
            logger.warning(f"Unknown namespace: {namespace}")
            return None

        start_time = time.perf_counter()

        # L1: Memory cache
        async with ns.lock:
            if key in ns.memory_cache:
                entry = ns.memory_cache[key]

                # Check TTL
                if ns.memory_ttl:
                    age = time.time() - entry["timestamp"]
                    if age > ns.memory_ttl.total_seconds():
                        del ns.memory_cache[key]
                        ns.stats = ns.stats.increment_evictions()
                        logger.debug(f"L1 cache expired: {namespace.value}:{key} (age={age:.2f}s)")
                    else:
                        # Move to end for LRU using OrderedDict.move_to_end() - O(1)
                        ns.memory_cache.move_to_end(key)
                        ns.stats = ns.stats.increment_hits()
                        elapsed = (time.perf_counter() - start_time) * 1000
                        logger.debug(f"L1 cache HIT: {namespace.value}:{key} ({elapsed:.2f}ms)")
                        return entry["data"]
                else:
                    # Move to end for LRU using OrderedDict.move_to_end() - O(1)
                    ns.memory_cache.move_to_end(key)
                    ns.stats = ns.stats.increment_hits()
                    elapsed = (time.perf_counter() - start_time) * 1000
                    logger.debug(f"L1 cache HIT: {namespace.value}:{key} ({elapsed:.2f}ms)")
                    return entry["data"]

        # L2: Filesystem cache
        backend_key = self._make_backend_key(namespace, key)
        try:
            data = await self.l2_backend.get(backend_key)

            if data is not None:
                # Decompress if needed
                if ns.compression and isinstance(data, bytes):
                    data = await self._decompress_data(data, ns.compression)

                # Promote to L1
                await self._promote_to_memory(ns, key, data)
                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(f"L2 cache HIT: {namespace.value}:{key} ({elapsed:.2f}ms)")
                return data
        except Exception as e:
            logger.error(f"L2 cache error for {namespace.value}:{key}: {e}", exc_info=True)

        ns.stats = ns.stats.increment_misses()
        elapsed = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Cache MISS: {namespace.value}:{key} ({elapsed:.2f}ms)")

        # Cache miss - use loader
        if loader:
            try:
                data = await loader()
                if data is not None:
                    await self.set(namespace, key, data)
                return data
            except Exception as e:
                logger.error(f"Cache loader failed for {namespace.value}:{key}: {e}", exc_info=True)
                return None

        return None

    async def set(
        self,
        namespace: CacheNamespace,
        key: str,
        value: Any,
        ttl_override: timedelta | None = None,
    ) -> None:
        """Store in both tiers efficiently."""
        ns = self.namespaces.get(namespace)
        if not ns:
            logger.warning(f"Unknown namespace: {namespace}")
            return

        start_time = time.perf_counter()

        # L1: Memory cache
        async with ns.lock:
            # LRU eviction
            evictions = self._evict_lru(ns, count=None)
            if evictions > 0:
                logger.debug(f"L1 evicted {evictions} items from {namespace.value}")

            ns.memory_cache[key] = {"data": value, "timestamp": time.time()}

        # L2: Filesystem with compression
        backend_key = self._make_backend_key(namespace, key)
        ttl = ttl_override or ns.disk_ttl

        try:
            # Compress if configured
            store_value = value
            if ns.compression:
                store_value = await self._compress_data(value, ns.compression)

            await self.l2_backend.set(backend_key, store_value, ttl)

            elapsed = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"Cache SET: {namespace.value}:{key} ({elapsed:.2f}ms, "
                f"compressed={ns.compression is not None})"
            )
        except Exception as e:
            logger.error(f"Failed to set cache {namespace.value}:{key}: {e}", exc_info=True)

    async def delete(self, namespace: CacheNamespace, key: str) -> bool:
        """Delete from both tiers."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return False

        # Remove from L1
        async with ns.lock:
            if key in ns.memory_cache:
                del ns.memory_cache[key]

        # Remove from L2
        backend_key = self._make_backend_key(namespace, key)
        return await self.l2_backend.delete(backend_key)

    async def clear_namespace(self, namespace: CacheNamespace) -> None:
        """Clear all entries in a namespace."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return

        # Clear L1
        async with ns.lock:
            ns.memory_cache.clear()

        # Clear L2
        pattern = f"{namespace.value}:*"
        await self.l2_backend.clear_pattern(pattern)

    async def clear(self) -> None:
        """Clear all caches (both L1 and L2).

        This is for backwards compatibility with tests.
        """
        # Clear all namespace memory caches
        for ns in self.namespaces.values():
            async with ns.lock:
                ns.memory_cache.clear()
                ns.stats = CacheStats()  # Reset to zero

        # Clear L2 backend
        await self.l2_backend.clear_all()

    async def _promote_to_memory(self, ns: NamespaceConfig, key: str, data: Any) -> None:
        """Promote data from L2 to L1 with LRU eviction.

        Uses OrderedDict.popitem(last=False) for O(1) eviction.
        """
        async with ns.lock:
            # LRU eviction if needed - popitem(last=False) removes oldest in O(1)
            while len(ns.memory_cache) >= ns.memory_limit:
                ns.memory_cache.popitem(last=False)
                ns.stats = ns.stats.increment_evictions()

            ns.memory_cache[key] = {"data": data, "timestamp": time.time()}

    async def _compress_data(self, data: Any, compression: CompressionType) -> bytes:
        """Compress data with specified algorithm."""
        return compress_data(data, compression)

    async def _decompress_data(self, data: bytes, compression: CompressionType) -> Any:
        """Decompress data."""
        return decompress_data(data, compression)

    def get_stats(self, namespace: CacheNamespace | None = None) -> dict[str, Any]:
        """Get cache statistics."""
        if namespace:
            ns = self.namespaces.get(namespace)
            if ns:
                return {
                    "namespace": namespace.value,
                    "memory_count": len(ns.memory_cache),
                    "stats": ns.stats.to_dict(),
                }

        # Aggregate stats using functional approach
        total_stats = {"hits": 0, "misses": 0, "evictions": 0, "memory_count": 0}
        for ns in self.namespaces.values():
            total_stats["hits"] += ns.stats.hits
            total_stats["misses"] += ns.stats.misses
            total_stats["evictions"] += ns.stats.evictions
            total_stats["memory_count"] += len(ns.memory_cache)

        return total_stats

    async def cleanup_expired_entries(self) -> int:
        """Scan all namespaces and evict expired L1 entries.

        Returns:
            Total number of expired entries evicted across all namespaces.
        """
        total_evicted = 0
        now = time.time()

        for namespace, ns in self.namespaces.items():
            if ns.memory_ttl is None:
                continue

            ttl_seconds = ns.memory_ttl.total_seconds()
            expired_keys: list[str] = []

            async with ns.lock:
                for key, entry in ns.memory_cache.items():
                    age = now - entry["timestamp"]
                    if age > ttl_seconds:
                        expired_keys.append(key)

                for key in expired_keys:
                    del ns.memory_cache[key]
                    ns.stats = ns.stats.increment_evictions()

            evicted_count = len(expired_keys)
            if evicted_count > 0:
                total_evicted += evicted_count
                logger.debug(
                    f"TTL cleanup: evicted {evicted_count} expired entries "
                    f"from {namespace.value}"
                )

        if total_evicted > 0:
            logger.info(f"TTL cleanup complete: evicted {total_evicted} total expired entries")

        return total_evicted

    async def _run_periodic_cleanup(self, interval_seconds: float = 300.0) -> None:
        """Run cleanup_expired_entries periodically.

        Args:
            interval_seconds: Seconds between cleanup runs (default 300 = 5 minutes).
        """
        logger.info(f"Background TTL cleanup task started (interval={interval_seconds}s)")
        try:
            while True:
                await asyncio.sleep(interval_seconds)
                try:
                    await self.cleanup_expired_entries()
                except Exception as e:
                    logger.error(f"TTL cleanup error: {e}", exc_info=True)
        except asyncio.CancelledError:
            logger.info("Background TTL cleanup task cancelled")

    def start_ttl_cleanup_task(self, interval_seconds: float = 300.0) -> asyncio.Task[None]:
        """Start the periodic TTL cleanup background task.

        Args:
            interval_seconds: Seconds between cleanup runs (default 300 = 5 minutes).

        Returns:
            The asyncio.Task running the cleanup loop.
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("TTL cleanup task already running")
            return self._cleanup_task

        self._cleanup_task = asyncio.create_task(
            self._run_periodic_cleanup(interval_seconds),
            name="cache-ttl-cleanup",
        )
        return self._cleanup_task

    async def stop_ttl_cleanup_task(self) -> None:
        """Stop the periodic TTL cleanup background task."""
        if self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("TTL cleanup task stopped")
        self._cleanup_task = None


# Global instance management
_global_cache: GlobalCacheManager[FilesystemBackend] | None = None


async def get_global_cache(
    force_new: bool = False,
) -> GlobalCacheManager[FilesystemBackend]:
    """Get the global cache manager instance.

    Args:
        force_new: Force creation of new instance

    Returns:
        GlobalCacheManager singleton

    """
    global _global_cache

    if _global_cache is None or force_new:
        # Create filesystem backend
        l2_backend = FilesystemBackend()

        # Create global cache manager
        _global_cache = GlobalCacheManager(l2_backend)

        logger.info("Global cache manager initialized")

    return _global_cache


async def shutdown_global_cache() -> None:
    """Shutdown the global cache manager."""
    global _global_cache

    if _global_cache:
        _global_cache.l2_backend.close()
        _global_cache = None
        logger.info("Global cache manager shut down")


# ============================================================================
# VERSIONED DATA CONTENT OPERATIONS
# ============================================================================


async def get_versioned_content(
    versioned_data: Any, config: VersionConfig | None = None
) -> dict[str, Any] | None:
    """Retrieve content from a versioned data object.

    This is a standalone function that retrieves content from BaseVersionedData objects.
    Handles both inline and external storage strategies.

    Args:
        versioned_data: A BaseVersionedData instance (or subclass)
        config: Optional VersionConfig to control cache behavior

    Returns:
        The content dictionary or None if not found

    """
    # Check if it's a versioned data object with content
    if not isinstance(versioned_data, BaseVersionedData):
        return None

    # Inline content takes precedence
    if versioned_data.content_inline is not None:
        # Ensure it's a dict
        content = versioned_data.content_inline
        if isinstance(content, dict):
            return content
        return None

    # External content
    if versioned_data.content_location:
        location = versioned_data.content_location
        if location.cache_key and location.cache_namespace:
            cache = await get_global_cache()
            # Ensure namespace is CacheNamespace enum (handle string from MongoDB)
            namespace = location.cache_namespace
            if isinstance(namespace, str):
                namespace = CacheNamespace(namespace)

            # Respect use_cache flag from config
            use_cache = True if not config else config.use_cache
            cached_content = await cache.get(
                namespace=namespace, key=location.cache_key, use_cache=use_cache
            )
            # Cast to expected return type
            if isinstance(cached_content, dict):
                return cached_content
            return None if cached_content is None else dict(cached_content)

    return None


async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    """Store versioned content using inline or external storage."""
    # CRITICAL FIX: Skip expensive JSON encoding when force_external=True
    # This prevents hanging on large binary data (e.g., 1290MB embeddings)
    if force_external:
        # Store externally without size check
        cache = await get_global_cache()
        # Use pure function from keys module
        cache_key = generate_resource_key(
            versioned_data.resource_type,
            versioned_data.resource_id,
            "content",
            versioned_data.version_info.data_hash[:8],
        )

        # Ensure namespace is CacheNamespace enum (handle string from MongoDB)
        namespace = versioned_data.namespace
        if isinstance(namespace, str):
            namespace = CacheNamespace(namespace)

        await cache.set(
            namespace=namespace,
            key=cache_key,
            value=content,
            ttl_override=versioned_data.ttl,
        )

        # Calculate size and checksum efficiently using pure functions
        # For large binary data, estimate without full JSON encoding
        content_size, checksum = estimate_binary_size(content)

        versioned_data.content_location = ContentLocation(
            cache_namespace=versioned_data.namespace,
            cache_key=cache_key,
            storage_type=StorageType.CACHE,
            size_bytes=content_size,
            checksum=checksum,
        )
        versioned_data.content_inline = None
        return

    # Normal path: serialize once and decide storage strategy
    serialized = serialize_content(content)

    inline_threshold = 16 * 1024

    if serialized.size_bytes < inline_threshold:
        versioned_data.content_inline = content
        versioned_data.content_location = None
        return

    cache = await get_global_cache()
    # Use pure function from keys module
    cache_key = generate_resource_key(
        versioned_data.resource_type,
        versioned_data.resource_id,
        "content",
        versioned_data.version_info.data_hash[:8],
    )

    # Ensure namespace is CacheNamespace enum (handle string from MongoDB)
    namespace = versioned_data.namespace
    if isinstance(namespace, str):
        namespace = CacheNamespace(namespace)

    await cache.set(
        namespace=namespace,
        key=cache_key,
        value=content,
        ttl_override=versioned_data.ttl,
    )

    versioned_data.content_location = ContentLocation(
        cache_namespace=versioned_data.namespace,
        cache_key=cache_key,
        storage_type=StorageType.CACHE,
        size_bytes=serialized.size_bytes,
        checksum=serialized.content_hash,
    )
    versioned_data.content_inline = None
