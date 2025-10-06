"""Global cache manager with two-tier caching (L1 memory + L2 filesystem)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import pickle
import time
from collections.abc import Callable
from datetime import timedelta
from enum import Enum
from typing import Any, Generic, TypeVar

from beanie import PydanticObjectId
from pydantic import BaseModel

from ..utils.logging import get_logger
from .compression import compress_data, decompress_data
from .filesystem import FilesystemBackend
from .models import (
    BaseVersionedData,
    CacheNamespace,
    CompressionType,
    ContentLocation,
    StorageType,
)
from .protocols import VersionedContent

logger = get_logger(__name__)

# Type variable for backend
T = TypeVar("T", bound=FilesystemBackend)


class NamespaceConfig:
    """Configuration for a cache namespace."""

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
        self.memory_cache: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}


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
        self.l1_caches: dict[CacheNamespace, NamespaceConfig] = {}
        self._init_default_namespaces()

    async def initialize(self) -> None:
        """Initialize the cache manager.

        Sets up L1 cache references and prepares the system for operations.
        """
        # Set up L1 cache references (aliases to namespaces for backwards compatibility)
        self.l1_caches = self.namespaces
        logger.info("GlobalCacheManager initialized")

    def _init_default_namespaces(self) -> None:
        """Initialize namespaces with optimized configs."""
        configs = [
            NamespaceConfig(
                CacheNamespace.DEFAULT,
                memory_limit=200,
                memory_ttl=timedelta(hours=6),
                disk_ttl=timedelta(days=1),
            ),
            NamespaceConfig(
                CacheNamespace.DICTIONARY,
                memory_limit=500,
                memory_ttl=timedelta(hours=24),
                disk_ttl=timedelta(days=7),
            ),
            NamespaceConfig(
                CacheNamespace.CORPUS,
                memory_limit=100,
                memory_ttl=timedelta(days=30),
                disk_ttl=timedelta(days=90),
                compression=CompressionType.ZSTD,
            ),
            NamespaceConfig(
                CacheNamespace.SEMANTIC,
                memory_limit=50,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30),
            ),
            NamespaceConfig(
                CacheNamespace.SEARCH,
                memory_limit=300,
                memory_ttl=timedelta(hours=1),
                disk_ttl=timedelta(hours=6),
            ),
            NamespaceConfig(
                CacheNamespace.TRIE,
                memory_limit=50,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30),
                compression=CompressionType.LZ4,
            ),
            NamespaceConfig(
                CacheNamespace.LITERATURE,
                memory_limit=50,
                memory_ttl=timedelta(days=30),
                disk_ttl=timedelta(days=90),
                compression=CompressionType.GZIP,
            ),
            NamespaceConfig(
                CacheNamespace.SCRAPING,
                memory_limit=100,
                memory_ttl=timedelta(hours=1),
                disk_ttl=timedelta(hours=24),
                compression=CompressionType.ZSTD,
            ),
            # Add commonly used namespaces that might not be explicitly configured
            NamespaceConfig(
                CacheNamespace.API,
                memory_limit=100,
                memory_ttl=timedelta(hours=1),
                disk_ttl=timedelta(hours=12),
            ),
            NamespaceConfig(
                CacheNamespace.LANGUAGE,
                memory_limit=100,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30),
                compression=CompressionType.ZSTD,
            ),
            NamespaceConfig(
                CacheNamespace.OPENAI,
                memory_limit=200,
                memory_ttl=timedelta(hours=24),
                disk_ttl=timedelta(days=7),
                compression=CompressionType.ZSTD,
            ),
            NamespaceConfig(
                CacheNamespace.LEXICON,
                memory_limit=100,
                memory_ttl=timedelta(days=7),
                disk_ttl=timedelta(days=30),
            ),
            NamespaceConfig(
                CacheNamespace.WOTD,
                memory_limit=50,
                memory_ttl=timedelta(days=1),
                disk_ttl=timedelta(days=7),
            ),
        ]

        for config in configs:
            self.namespaces[config.name] = config

    async def get(
        self,
        namespace: CacheNamespace,
        key: str,
        loader: Callable[[], Any] | None = None,
    ) -> Any | None:
        """Two-tier get with optional loader."""
        ns = self.namespaces.get(namespace)
        if not ns:
            return None

        # L1: Memory cache
        async with ns.lock:
            if key in ns.memory_cache:
                entry = ns.memory_cache[key]

                # Check TTL
                if ns.memory_ttl:
                    age = time.time() - entry["timestamp"]
                    if age > ns.memory_ttl.total_seconds():
                        del ns.memory_cache[key]
                        ns.stats["evictions"] += 1
                    else:
                        # Move to end for LRU (dict preserves order)
                        del ns.memory_cache[key]
                        ns.memory_cache[key] = entry
                        ns.stats["hits"] += 1
                        return entry["data"]
                else:
                    ns.stats["hits"] += 1
                    return entry["data"]

        # L2: Filesystem cache
        backend_key = f"{namespace.value}:{key}"
        data = await self.l2_backend.get(backend_key)

        if data is not None:
            # Decompress if needed
            if ns.compression and isinstance(data, bytes):
                data = await self._decompress_data(data, ns.compression)

            # Promote to L1
            await self._promote_to_memory(ns, key, data)
            return data

        ns.stats["misses"] += 1

        # Cache miss - use loader
        if loader:
            data = await loader()
            if data is not None:
                await self.set(namespace, key, data)
            return data

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
            return

        # L1: Memory cache
        async with ns.lock:
            # LRU eviction
            while len(ns.memory_cache) >= ns.memory_limit:
                # Remove first item (oldest)
                first_key = next(iter(ns.memory_cache))
                del ns.memory_cache[first_key]
                ns.stats["evictions"] += 1

            ns.memory_cache[key] = {"data": value, "timestamp": time.time()}

        # L2: Filesystem with compression
        backend_key = f"{namespace.value}:{key}"
        ttl = ttl_override or ns.disk_ttl

        # Compress if configured
        store_value = value
        if ns.compression:
            store_value = await self._compress_data(value, ns.compression)

        await self.l2_backend.set(backend_key, store_value, ttl)

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
        backend_key = f"{namespace.value}:{key}"
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
                ns.stats = {"hits": 0, "misses": 0, "evictions": 0}

        # Clear L2 backend
        await self.l2_backend.clear_all()

    async def _promote_to_memory(self, ns: NamespaceConfig, key: str, data: Any) -> None:
        """Promote data from L2 to L1."""
        async with ns.lock:
            # LRU eviction if needed
            while len(ns.memory_cache) >= ns.memory_limit:
                first_key = next(iter(ns.memory_cache))
                del ns.memory_cache[first_key]
                ns.stats["evictions"] += 1

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
                    "stats": ns.stats.copy(),
                }

        # Aggregate stats
        total_stats = {"hits": 0, "misses": 0, "evictions": 0, "memory_count": 0}
        for ns in self.namespaces.values():
            total_stats["hits"] += ns.stats["hits"]
            total_stats["misses"] += ns.stats["misses"]
            total_stats["evictions"] += ns.stats["evictions"]
            total_stats["memory_count"] += len(ns.memory_cache)

        return total_stats


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


async def get_versioned_content(versioned_data: Any) -> dict[str, Any] | None:
    """Retrieve content from a versioned data object.

    This is a standalone function that retrieves content from BaseVersionedData objects.
    Handles both inline and external storage strategies.

    Args:
        versioned_data: A BaseVersionedData instance (or subclass)

    Returns:
        The content dictionary or None if not found

    """
    # Check if it's a versioned data object with content
    # Accept both VersionedContent and BaseVersionedData subclasses
    from .models import BaseVersionedData
    if not isinstance(versioned_data, (VersionedContent, BaseVersionedData)):
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
            cached_content = await cache.get(
                namespace=location.cache_namespace, key=location.cache_key
            )
            # Cast to expected return type
            if isinstance(cached_content, dict):
                return cached_content
            return None if cached_content is None else dict(cached_content)

    return None


def _json_default(obj: Any) -> str:
    """Serialize enums and Pydantic types in a stable way."""
    if isinstance(obj, PydanticObjectId):
        return str(obj)
    if isinstance(obj, Enum):
        return str(obj.value)
    return str(obj)


async def set_versioned_content(
    versioned_data: BaseVersionedData,
    content: Any,
    *,
    force_external: bool = False,
) -> None:
    """Store versioned content using inline or external storage."""
    content_str = json.dumps(content, sort_keys=True, default=_json_default)
    content_size = len(content_str.encode())

    inline_threshold = 16 * 1024

    if not force_external and content_size < inline_threshold:
        versioned_data.content_inline = content
        versioned_data.content_location = None
        return

    cache = await get_global_cache()
    cache_key = (
        f"{versioned_data.resource_type.value}:{versioned_data.resource_id}:"
        f"content:{versioned_data.version_info.data_hash[:8]}"
    )

    await cache.set(
        namespace=versioned_data.namespace,
        key=cache_key,
        value=content,
        ttl_override=versioned_data.ttl,
    )

    versioned_data.content_location = ContentLocation(
        cache_namespace=versioned_data.namespace,
        cache_key=cache_key,
        storage_type=StorageType.CACHE,
        size_bytes=content_size,
        checksum=hashlib.sha256(content_str.encode()).hexdigest(),
    )
    versioned_data.content_inline = None


# ============================================================================
# EXTERNAL CONTENT STORAGE - Moved from models/storage.py
# ============================================================================


async def load_external_content(location: ContentLocation) -> Any:
    """Load content from external storage location.

    Handles decompression and deserialization efficiently.

    Args:
        location: ContentLocation object with storage metadata

    Returns:
        Deserialized content from external storage

    """
    if location.storage_type == StorageType.CACHE:
        # Load from cache backend
        cache = await get_global_cache()
        backend_key = f"{location.cache_namespace}:{location.cache_key}"
        data = await cache.l2_backend.get(backend_key)

    elif location.storage_type == StorageType.S3:
        # Load from S3 (implement when needed)
        raise NotImplementedError("S3 backend not yet implemented")

    else:
        raise ValueError(f"Unsupported storage type: {location.storage_type}")

    # Decompress if needed
    if location.compression and isinstance(data, bytes):
        data = decompress_data(data, location.compression)

    # Deserialize based on content type hint
    if isinstance(data, bytes):
        # Check pickle magic bytes for fast path
        if len(data) >= 2 and data[:2] in (b"\x80\x04", b"\x80\x05"):
            return pickle.loads(data)
        # Otherwise assume JSON
        return json.loads(data.decode("utf-8"))

    return data


async def store_external_content(
    content: Any,
    namespace: CacheNamespace,
    key: str,
    compression: CompressionType | None = None,
) -> ContentLocation:
    """Store content externally with optimal serialization.

    Returns ContentLocation metadata for retrieval.

    Args:
        content: Content to store
        namespace: Cache namespace for organization
        key: Unique key for the content
        compression: Optional compression type (auto-selected if None)

    Returns:
        ContentLocation object with storage metadata

    """
    # Serialize efficiently based on type
    if isinstance(content, BaseModel):
        # Pydantic models: use model_dump for dict conversion
        serialized = json.dumps(content.model_dump(), sort_keys=True).encode()
    elif isinstance(content, dict | list):
        # JSON-serializable types
        serialized = json.dumps(content, sort_keys=True).encode()
    else:
        # Everything else: use pickle (fastest for complex objects)
        serialized = pickle.dumps(content, protocol=pickle.HIGHEST_PROTOCOL)

    size_bytes = len(serialized)

    # Auto-select compression if not specified
    if compression is None:
        # If the content is below 1KB, no compression (fastest)
        if size_bytes < 1024:
            compression = None
        # If the content is below 10MB, use ZSTD (faster)
        elif size_bytes < 10_000_000:
            compression = CompressionType.ZSTD
        # Else, use GZIP (slowest)
        else:
            compression = CompressionType.GZIP

    # Compress
    compressed = compress_data(serialized, compression) if compression else serialized

    # Store in cache backend
    cache = await get_global_cache()

    backend_key = f"{namespace.value}:{key}"

    await cache.l2_backend.set(backend_key, compressed)

    return ContentLocation(
        storage_type=StorageType.CACHE,
        cache_namespace=namespace,
        cache_key=key,
        compression=compression,
        size_bytes=size_bytes,
        size_compressed=len(compressed) if compression else None,
        checksum=hashlib.sha256(serialized).hexdigest(),
    )


# ============================================================================
# REMOVED: Deprecated CacheManager - use get_global_cache() instead
# ============================================================================
