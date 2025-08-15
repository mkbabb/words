"""Filesystem-based cache backend using diskcache."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any, TypeVar, cast

import diskcache as dc

from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory
from .core import CacheBackend

logger = get_logger(__name__)
T = TypeVar("T")



class FilesystemCacheBackend(CacheBackend[T]):
    """High-performance filesystem cache using diskcache."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        size_limit: int = 1024 * 1024 * 1024 * 10,  # 10GB
        default_ttl: timedelta = timedelta(days=7),
    ):
        if cache_dir is None:
            cache_dir = get_cache_directory() / "unified"

        cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_dir = cache_dir
        self.size_limit = size_limit
        self.default_ttl = default_ttl

        # Initialize cache with retry logic for development hot reloading
        self.cache = self._initialize_cache()

    def _initialize_cache(self) -> dc.Cache:
        """Initialize diskcache with proper error handling and cleanup."""
        import shutil

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                cache = dc.Cache(
                    directory=str(self.cache_dir),
                    size_limit=self.size_limit,
                    eviction_policy="least-recently-used",
                    statistics=True,
                    tag_index=True,
                    timeout=60,
                )

                # Test the cache to ensure it's working
                test_key = "__init_test__"
                cache[test_key] = "test_value"
                if cache.get(test_key) == "test_value":
                    cache.delete(test_key)
                    logger.info(f"Initialized filesystem cache at: {self.cache_dir}")
                    return cache
                raise RuntimeError("Cache test failed - get/set not working")

            except Exception as e:
                logger.warning(f"Cache initialization attempt {attempt + 1} failed: {e}")
                if attempt < max_attempts - 1:
                    # Clean up corrupted cache files
                    try:
                        shutil.rmtree(self.cache_dir, ignore_errors=True)
                        self.cache_dir.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Cleaned up corrupted cache directory: {self.cache_dir}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup cache directory: {cleanup_error}")
                else:
                    raise RuntimeError(
                        f"Failed to initialize cache after {max_attempts} attempts: {e}",
                    )

        raise RuntimeError("Unreachable code")

    async def get(self, namespace: str, key: str, default: T | None = None) -> T | None:
        """Get value from cache with error recovery."""
        cache_key = f"{namespace}:{key}"
        loop = asyncio.get_event_loop()

        try:
            value = await loop.run_in_executor(None, self.cache.get, cache_key, default)
            return cast("T", value)
        except Exception as e:
            logger.warning(f"Cache get failed for {cache_key}: {e}")
            # Try to reinitialize cache if SQLite error
            if "no such table" in str(e).lower() or "database is locked" in str(e).lower():
                logger.info("Attempting cache reinitialization due to SQLite error")
                try:
                    self.cache.close()
                    self.cache = self._initialize_cache()
                    value = await loop.run_in_executor(None, self.cache.get, cache_key, default)
                    return cast("T", value)
                except Exception as reinit_error:
                    logger.error(f"Cache reinitialization failed: {reinit_error}")
            return cast("T", default)

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: timedelta | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set value in cache with error recovery."""
        cache_key = f"{namespace}:{key}"
        expire = (ttl or self.default_ttl).total_seconds() if ttl or self.default_ttl else None

        all_tags = [namespace]
        if tags:
            all_tags.extend(tags)

        loop = asyncio.get_event_loop()
        # diskcache only supports single tag per entry, use first tag
        tag = all_tags[0] if all_tags else None

        try:
            await loop.run_in_executor(None, self.cache.set, cache_key, value, expire, False, tag)
        except Exception as e:
            logger.warning(f"Cache set failed for {cache_key}: {e}")
            # Try to reinitialize cache if SQLite error
            if "no such table" in str(e).lower() or "database is locked" in str(e).lower():
                logger.info("Attempting cache reinitialization due to SQLite error")
                try:
                    self.cache.close()
                    self.cache = self._initialize_cache()
                    await loop.run_in_executor(
                        None,
                        self.cache.set,
                        cache_key,
                        value,
                        expire,
                        False,
                        tag,
                    )
                except Exception as reinit_error:
                    logger.error(f"Cache reinitialization failed: {reinit_error}")
                    # Don't raise - just log and continue without caching
            else:
                logger.error(f"Non-SQLite cache error: {e}")
                # Don't raise - just log and continue without caching

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete specific cache entry."""
        cache_key = f"{namespace}:{key}"
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.cache.delete, cache_key)
        return bool(result)

    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all entries in a namespace."""
        loop = asyncio.get_event_loop()
        # Get all keys in namespace
        count = 0
        for key in list(self.cache):
            if key.startswith(f"{namespace}:"):
                await loop.run_in_executor(None, self.cache.delete, key)
                count += 1
        return count

    async def clear(self) -> None:
        """Clear entire cache."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.cache.clear)

    async def exists(self, namespace: str, key: str) -> bool:
        """Check if key exists."""
        cache_key = f"{namespace}:{key}"
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: cache_key in self.cache)
        return bool(result)

    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]:
        """Get cache statistics."""
        loop = asyncio.get_event_loop()

        if namespace:
            # Count entries in namespace
            count = 0
            total_size = 0
            for key in list(self.cache):
                if key.startswith(f"{namespace}:"):
                    count += 1
                    # Get size if available
                    try:
                        value = self.cache.get(key)
                        if value:
                            total_size += len(str(value).encode())
                    except Exception:
                        pass

            return {
                "namespace": namespace,
                "count": count,
                "size_bytes": total_size,
            }
        # Get overall stats
        stats = await loop.run_in_executor(None, lambda: self.cache.stats())
        return {
            "size": len(self.cache),
            "size_limit": self.cache.size_limit,
            "eviction_policy": self.cache.eviction_policy,
            "stats": stats,
        }

    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """Invalidate entries by tags (required abstract method)."""
        total_count = 0
        for tag in tags:
            count = await self.invalidate_tag(tag)
            total_count += count
        return total_count

    async def invalidate_tag(self, tag: str) -> int:
        """Invalidate all entries with a specific tag."""
        loop = asyncio.get_event_loop()
        # diskcache evict by tag
        count = await loop.run_in_executor(None, self.cache.evict, tag)
        return count or 0

    async def close(self) -> None:
        """Close the cache connection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.cache.close)
