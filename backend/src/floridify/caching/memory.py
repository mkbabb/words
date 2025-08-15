"""In-memory TTL cache utilities for efficient instance management.

Provides robust TTL-based caching with automatic cleanup, instance limits,
and proper type safety for managing corpus and semantic search instances.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, TypeVar

from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry[T]:
    """Cache entry with TTL and metadata."""

    value: T
    created_at: float
    ttl_seconds: float
    last_accessed: float

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > (self.created_at + self.ttl_seconds)

    def touch(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = time.time()


class InMemoryTTLCache[T]:
    """High-performance in-memory TTL cache with automatic cleanup.

    Features:
    - Automatic TTL-based expiration
    - LRU eviction when instance limit is reached
    - Background cleanup of expired entries
    - Thread-safe operations
    - Comprehensive metrics and monitoring
    """

    def __init__(
        self,
        max_instances: int = 50,
        default_ttl_seconds: float = 3600.0,  # 1 hour
        cleanup_interval_seconds: float = 300.0,  # 5 minutes
        name: str = "cache",
    ) -> None:
        """Initialize TTL cache.

        Args:
            max_instances: Maximum number of instances to keep in cache
            default_ttl_seconds: Default TTL for entries
            cleanup_interval_seconds: How often to run cleanup
            name: Name for logging and metrics

        """
        self.max_instances = max_instances
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.name = name

        self._cache: dict[str, CacheEntry[T]] = {}
        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._cleanups = 0

        logger.info(
            f"Initialized {name} TTL cache (max_instances={max_instances}, ttl={default_ttl_seconds}s)",
        )

    async def get(self, key: str) -> T | None:
        """Get value from cache, returning None if expired or not found.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired

        """
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                logger.debug(f"{self.name} cache miss: {key}")
                return None

            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                logger.debug(f"{self.name} cache expired: {key}")
                return None

            # Touch entry and return value
            entry.touch()
            self._hits += 1
            logger.debug(f"{self.name} cache hit: {key}")
            return entry.value

    async def set(self, key: str, value: T, ttl_seconds: float | None = None) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds, uses default if None

        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

        async with self._lock:
            now = time.time()
            entry = CacheEntry(
                value=value,
                created_at=now,
                ttl_seconds=ttl,
                last_accessed=now,
            )

            # Check if we need to evict entries
            if len(self._cache) >= self.max_instances and key not in self._cache:
                await self._evict_lru()

            self._cache[key] = entry
            logger.debug(f"{self.name} cached: {key} (ttl={ttl}s)")

    async def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if entry was deleted, False if not found

        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"{self.name} deleted: {key}")
                return True
            return False

    async def clear(self) -> int:
        """Clear all entries from cache.

        Returns:
            Number of entries cleared

        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"{self.name} cleared {count} entries")
            return count

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed

        """
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                del self._cache[key]

            self._cleanups += 1
            if expired_keys:
                logger.debug(
                    f"{self.name} cleaned up {len(expired_keys)} expired entries",
                )

            return len(expired_keys)

    async def _evict_lru(self) -> None:
        """Evict least recently used entry to make space."""
        if not self._cache:
            return

        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)

        del self._cache[lru_key]
        self._evictions += 1
        logger.debug(f"{self.name} evicted LRU entry: {lru_key}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

        return {
            "name": self.name,
            "size": len(self._cache),
            "max_instances": self.max_instances,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "cleanups": self._cleanups,
            "total_requests": total_requests,
        }

    async def start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is not None:
            return

        async def cleanup_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval_seconds)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    logger.info(f"{self.name} cleanup task cancelled")
                    break
                except Exception as e:
                    logger.error(f"{self.name} cleanup error: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(
            f"{self.name} cleanup task started (interval={self.cleanup_interval_seconds}s)",
        )

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info(f"{self.name} cleanup task stopped")


__all__ = [
    "CacheEntry",
    "InMemoryTTLCache",
]
