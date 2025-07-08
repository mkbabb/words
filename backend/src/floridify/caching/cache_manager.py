"""Modern unified cache manager with TTL support and multiple backends."""

from __future__ import annotations

import hashlib
import pickle
import time
from pathlib import Path
from typing import Any, TypeVar

from ..utils.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, value: Any, ttl_seconds: float | None = None) -> None:
        self.value = value
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def __repr__(self) -> str:
        age = time.time() - self.created_at
        return f"CacheEntry(age={age:.1f}s, ttl={self.ttl_seconds}, expired={self.is_expired})"


class CacheManager:
    """Unified cache manager with multiple backends and TTL support."""

    def __init__(
        self,
        default_ttl_hours: float = 24.0,
        cache_dir: Path | None = None,
        max_memory_entries: int = 1000,
    ) -> None:
        """Initialize cache manager.
        
        Args:
            default_ttl_hours: Default TTL for cache entries in hours
            cache_dir: Directory for file-based cache (defaults to .cache/floridify)
            max_memory_entries: Maximum entries in memory cache
        """
        self.default_ttl_seconds = default_ttl_hours * 3600
        self.max_memory_entries = max_memory_entries
        
        # Setup cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "floridify"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for fast access
        self._memory_cache: dict[str, CacheEntry] = {}
        
        logger.info(f"🗄️  Cache manager initialized: {self.cache_dir}, TTL={default_ttl_hours}h")

    def _generate_cache_key(self, key_parts: tuple[Any, ...]) -> str:
        """Generate a deterministic cache key from parts."""
        # Convert all parts to strings and hash them
        key_str = "|".join(str(part) for part in key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _cleanup_memory_cache(self) -> None:
        """Remove expired entries and enforce size limits."""
        # Remove expired entries
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.is_expired
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            
        # Enforce size limit (LRU-style, remove oldest)
        if len(self._memory_cache) > self.max_memory_entries:
            # Sort by creation time and remove oldest
            sorted_entries = sorted(
                self._memory_cache.items(),
                key=lambda x: x[1].created_at
            )
            entries_to_remove = len(self._memory_cache) - self.max_memory_entries
            for key, _ in sorted_entries[:entries_to_remove]:
                del self._memory_cache[key]

    def get(
        self,
        key_parts: tuple[Any, ...],
        default: T | None = None,
        use_file_cache: bool = False,
    ) -> T | None:
        """Get cached value.
        
        Args:
            key_parts: Parts to generate cache key from
            default: Default value if not found
            use_file_cache: Whether to check file cache
            
        Returns:
            Cached value or default
        """
        cache_key = self._generate_cache_key(key_parts)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if not entry.is_expired:
                logger.debug(f"💨 Memory cache hit: {cache_key}")
                return entry.value
            else:
                # Remove expired entry
                del self._memory_cache[cache_key]
                logger.debug(f"⏰ Memory cache expired: {cache_key}")
        
        # Check file cache if requested
        if use_file_cache:
            file_path = self.cache_dir / f"{cache_key}.pkl"
            if file_path.exists():
                try:
                    with open(file_path, "rb") as f:
                        entry = pickle.load(f)
                    
                    if not entry.is_expired:
                        logger.debug(f"📁 File cache hit: {cache_key}")
                        # Promote to memory cache
                        self._memory_cache[cache_key] = entry
                        self._cleanup_memory_cache()
                        return entry.value
                    else:
                        # Remove expired file
                        file_path.unlink()
                        logger.debug(f"⏰ File cache expired: {cache_key}")
                        
                except Exception as e:
                    logger.warning(f"Failed to load cache file {file_path}: {e}")
        
        logger.debug(f"❌ Cache miss: {cache_key}")
        return default

    def set(
        self,
        key_parts: tuple[Any, ...],
        value: Any,
        ttl_hours: float | None = None,
        use_file_cache: bool = False,
    ) -> None:
        """Set cached value.
        
        Args:
            key_parts: Parts to generate cache key from
            value: Value to cache
            ttl_hours: TTL in hours (uses default if None)
            use_file_cache: Whether to persist to file cache
        """
        cache_key = self._generate_cache_key(key_parts)
        
        # Use default TTL if not specified
        if ttl_hours is None:
            ttl_seconds = self.default_ttl_seconds
        else:
            ttl_seconds = ttl_hours * 3600
            
        entry = CacheEntry(value, ttl_seconds)
        
        # Always store in memory cache
        self._memory_cache[cache_key] = entry
        self._cleanup_memory_cache()
        
        # Store in file cache if requested
        if use_file_cache:
            file_path = self.cache_dir / f"{cache_key}.pkl"
            try:
                with open(file_path, "wb") as f:
                    pickle.dump(entry, f)
                logger.debug(f"💾 Cached to file: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to save cache file {file_path}: {e}")
        
        logger.debug(f"✅ Cached: {cache_key} (TTL: {ttl_hours or self.default_ttl_seconds/3600}h)")

    def invalidate(self, key_parts: tuple[Any, ...]) -> bool:
        """Invalidate specific cache entry.
        
        Args:
            key_parts: Parts to generate cache key from
            
        Returns:
            True if entry was found and removed
        """
        cache_key = self._generate_cache_key(key_parts)
        
        # Remove from memory cache
        memory_removed = cache_key in self._memory_cache
        if memory_removed:
            del self._memory_cache[cache_key]
        
        # Remove from file cache
        file_path = self.cache_dir / f"{cache_key}.pkl"
        file_removed = False
        if file_path.exists():
            try:
                file_path.unlink()
                file_removed = True
            except Exception as e:
                logger.warning(f"Failed to remove cache file {file_path}: {e}")
        
        if memory_removed or file_removed:
            logger.info(f"🗑️  Invalidated cache: {cache_key}")
            return True
        
        return False

    def clear_all(self) -> None:
        """Clear all cached data."""
        # Clear memory cache
        memory_count = len(self._memory_cache)
        self._memory_cache.clear()
        
        # Clear file cache
        file_count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                cache_file.unlink()
                file_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove {cache_file}: {e}")
        
        logger.info(f"🧹 Cleared all cache: {memory_count} memory + {file_count} file entries")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        memory_entries = len(self._memory_cache)
        expired_memory = sum(1 for entry in self._memory_cache.values() if entry.is_expired)
        
        file_entries = len(list(self.cache_dir.glob("*.pkl")))
        
        return {
            "memory_entries": memory_entries,
            "expired_memory_entries": expired_memory,
            "file_entries": file_entries,
            "cache_dir": str(self.cache_dir),
            "default_ttl_hours": self.default_ttl_seconds / 3600,
        }


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def invalidate_cache(key_parts: tuple[Any, ...]) -> bool:
    """Convenience function to invalidate cache entry."""
    return get_cache_manager().invalidate(key_parts)


def clear_all_cache() -> None:
    """Convenience function to clear all cache."""
    get_cache_manager().clear_all()