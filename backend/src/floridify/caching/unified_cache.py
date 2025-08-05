"""Unified multi-level cache for search operations with intelligent promotion."""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from ..utils.logging import get_logger
from .cache_manager import CacheEntry, get_cache_manager

logger = get_logger(__name__)


class UnifiedSearchCache:
    """Multi-level cache optimized for search patterns with query frequency tracking."""

    def __init__(self) -> None:
        # L1: Ultra-fast in-memory cache (1000 entries, 1 hour)
        self.l1_cache: dict[str, CacheEntry] = {}
        self.l1_max_size = 1000
        self.l1_ttl = 3600  # 1 hour

        # L2: Extended memory cache (10000 entries, 24 hours)
        self.l2_cache: dict[str, CacheEntry] = {}
        self.l2_max_size = 10000
        self.l2_ttl = 86400  # 24 hours

        # L3: Persistent cache (unlimited, 7 days)
        self.l3_cache = get_cache_manager()

        # Query frequency tracking for promotion decisions
        self.query_frequency: dict[str, int] = defaultdict(int)
        self.query_performance: dict[str, float] = {}  # Track query performance

        # Cache statistics
        self.stats = {"l1_hits": 0, "l2_hits": 0, "l3_hits": 0, "misses": 0, "promotions": 0}

    async def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable[[], Any],
        cache_level: int = 2,
        force_compute: bool = False,
    ) -> Any:
        """Get cached result or compute with intelligent caching and promotion."""

        if force_compute:
            result = await compute_fn()
            self._cache_at_appropriate_level(cache_key, result, cache_level)
            return result

        # Track query frequency
        self.query_frequency[cache_key] += 1

        # Check L1 first (fastest)
        if cache_key in self.l1_cache:
            entry = self.l1_cache[cache_key]
            if not entry.is_expired:
                self.stats["l1_hits"] += 1
                self._track_hit(cache_key)
                return entry.value
            else:
                del self.l1_cache[cache_key]

        # Check L2 (extended memory)
        if cache_level >= 2 and cache_key in self.l2_cache:
            entry = self.l2_cache[cache_key]
            if not entry.is_expired:
                self.stats["l2_hits"] += 1
                # Promote to L1 for frequently accessed items
                if self._should_promote_to_l1(cache_key):
                    self._promote_to_l1(cache_key, entry.value)
                return entry.value
            else:
                del self.l2_cache[cache_key]

        # Check L3 (persistent) - Skip for fast operations to avoid MongoDB overhead
        if cache_level >= 3:
            # Skip L3 lookup for search operations that should be fast
            cache_key_str = str(cache_key)
            is_fast_search = any(op in cache_key_str for op in ["search:", "exact:", "fuzzy:"])
            
            if not is_fast_search:
                result = self.l3_cache.get((cache_key,))
                if result is not None:
                    self.stats["l3_hits"] += 1
                    # Promote to memory if frequently accessed
                    if self._should_promote_to_memory(cache_key):
                        self._promote_to_memory(cache_key, result)
                    return result
            else:
                self.stats["l3_skipped"] = self.stats.get("l3_skipped", 0) + 1

        # Cache miss - compute result
        self.stats["misses"] += 1
        start_time = time.time()

        result = await compute_fn()

        # Track performance for caching decisions
        compute_time = time.time() - start_time
        self.query_performance[cache_key] = compute_time

        # Cache at appropriate level based on performance and frequency
        self._cache_at_appropriate_level(cache_key, result, cache_level, compute_time)

        return result

    def _should_promote_to_l1(self, cache_key: str) -> bool:
        """Decide if query should be promoted to L1 cache."""
        frequency = self.query_frequency[cache_key]
        return frequency >= 3  # Promote after 3 accesses

    def _should_promote_to_memory(self, cache_key: str) -> bool:
        """Decide if query should be promoted to memory caches."""
        frequency = self.query_frequency[cache_key]
        performance = self.query_performance.get(cache_key, 0)

        # Promote frequent queries or expensive queries
        return frequency >= 2 or performance > 0.1  # 100ms+

    def _promote_to_l1(self, cache_key: str, value: Any) -> None:
        """Promote entry to L1 cache."""
        self._ensure_l1_capacity()
        self.l1_cache[cache_key] = CacheEntry(value, self.l1_ttl)
        self.stats["promotions"] += 1
        logger.debug(f"Promoted to L1: {cache_key}")

    def _promote_to_memory(self, cache_key: str, value: Any) -> None:
        """Promote entry to memory caches (L2 and possibly L1)."""
        # Always promote to L2
        self._ensure_l2_capacity()
        self.l2_cache[cache_key] = CacheEntry(value, self.l2_ttl)

        # Promote to L1 if very frequent
        if self._should_promote_to_l1(cache_key):
            self._promote_to_l1(cache_key, value)

        self.stats["promotions"] += 1
        logger.debug(f"Promoted to memory: {cache_key}")

    def _cache_at_appropriate_level(
        self, cache_key: str, value: Any, requested_level: int, compute_time: float | None = None
    ) -> None:
        """Cache at appropriate level based on performance and frequency."""
        frequency = self.query_frequency[cache_key]

        # Expensive queries get cached at higher levels
        if compute_time and compute_time > 0.05:  # 50ms+
            requested_level = max(requested_level, 3)

        # Frequent queries get cached in memory
        if frequency >= 2:
            self._ensure_l2_capacity()
            self.l2_cache[cache_key] = CacheEntry(value, self.l2_ttl)

            if frequency >= 3:
                self._promote_to_l1(cache_key, value)

        # Always cache in L3 for persistence if requested
        if requested_level >= 3:
            # Determine TTL based on performance
            ttl_hours = (
                168 if compute_time and compute_time > 0.1 else 24
            )  # 7 days for expensive, 1 day for cheap
            self.l3_cache.set((cache_key,), value, ttl_hours=ttl_hours)

    def _ensure_l1_capacity(self) -> None:
        """Ensure L1 cache doesn't exceed capacity."""
        if len(self.l1_cache) >= self.l1_max_size:
            # Remove oldest entries
            sorted_items = sorted(self.l1_cache.items(), key=lambda x: x[1].created_at)
            for key, _ in sorted_items[: self.l1_max_size // 4]:  # Remove 25%
                del self.l1_cache[key]

    def _ensure_l2_capacity(self) -> None:
        """Ensure L2 cache doesn't exceed capacity."""
        if len(self.l2_cache) >= self.l2_max_size:
            # Remove oldest entries
            sorted_items = sorted(self.l2_cache.items(), key=lambda x: x[1].created_at)
            for key, _ in sorted_items[: self.l2_max_size // 4]:  # Remove 25%
                del self.l2_cache[key]

    def _track_hit(self, cache_key: str) -> None:
        """Track successful cache hit for optimization."""
        # Update access time for frequency-based eviction
        pass

    def invalidate(self, cache_key: str) -> None:
        """Invalidate cache entry across all levels."""
        if cache_key in self.l1_cache:
            del self.l1_cache[cache_key]
        if cache_key in self.l2_cache:
            del self.l2_cache[cache_key]
        # Note: CacheManager doesn't have delete method - could implement if needed

        # Reset frequency tracking
        if cache_key in self.query_frequency:
            del self.query_frequency[cache_key]
        if cache_key in self.query_performance:
            del self.query_performance[cache_key]

    def clear_all(self) -> None:
        """Clear all cache levels."""
        self.l1_cache.clear()
        self.l2_cache.clear()
        self.query_frequency.clear()
        self.query_performance.clear()
        # Note: L3 cache (file/MongoDB) not cleared for persistence

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = sum(self.stats.values())
        hit_rate = (self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["l3_hits"]) / max(
            1, total_requests
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "l1_size": len(self.l1_cache),
            "l2_size": len(self.l2_cache),
            "tracked_queries": len(self.query_frequency),
            "avg_query_frequency": sum(self.query_frequency.values())
            / max(1, len(self.query_frequency)),
        }

    def cleanup_expired(self) -> int:
        """Clean up expired entries and return count of removed entries."""
        removed = 0

        # Cleanup L1
        expired_l1 = [key for key, entry in self.l1_cache.items() if entry.is_expired]
        for key in expired_l1:
            del self.l1_cache[key]
            removed += 1

        # Cleanup L2
        expired_l2 = [key for key, entry in self.l2_cache.items() if entry.is_expired]
        for key in expired_l2:
            del self.l2_cache[key]
            removed += 1

        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired cache entries")

        return removed


# Global unified cache instance
_unified_cache: UnifiedSearchCache | None = None


def get_unified_cache() -> UnifiedSearchCache:
    """Get global unified cache instance."""
    global _unified_cache
    if _unified_cache is None:
        _unified_cache = UnifiedSearchCache()
    return _unified_cache
