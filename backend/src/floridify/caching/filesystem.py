"""Filesystem cache backend using diskcache for L2 storage."""

from __future__ import annotations

import asyncio
import pickle
from datetime import timedelta
from pathlib import Path
from typing import Any

import diskcache as dc

from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory

logger = get_logger(__name__)

# Constants
DEFAULT_SIZE_LIMIT = 1024 * 1024 * 1024 * 10  # 10GB
DEFAULT_TTL = timedelta(days=7)


class FilesystemBackend:
    """Filesystem backend using diskcache for L2 storage.
    
    Optimized for performance with minimal serialization overhead.
    """
    
    def __init__(
        self,
        cache_dir: Path | None = None,
        size_limit: int = DEFAULT_SIZE_LIMIT,
        default_ttl: timedelta = DEFAULT_TTL,
    ):
        """Initialize with configurable size limit and TTL.
        
        Args:
            cache_dir: Directory for cache storage (defaults to system cache dir)
            size_limit: Maximum cache size in bytes (default 10GB)
            default_ttl: Default time-to-live for cached items
        """
        if cache_dir is None:
            cache_dir = get_cache_directory() / "unified"
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        
        self.cache = dc.Cache(
            directory=str(self.cache_dir),
            size_limit=size_limit,
            eviction_policy="least-recently-used",
            statistics=True,
            tag_index=False,
            timeout=60
        )
        
        logger.info(f"FilesystemBackend initialized at {cache_dir} with {size_limit / (1024**3):.1f}GB limit")
    
    async def get(self, key: str) -> Any | None:
        """Get with minimal deserialization overhead."""
        loop = asyncio.get_event_loop()
        
        def _get() -> Any | None:
            data = self.cache.get(key)
            if data is None:
                return None
            
            # For bytes, attempt pickle deserialization (most performant)
            if isinstance(data, bytes):
                # Check for pickle magic bytes (protocol 4 or 5)
                if data[:2] in (b'\x80\x04', b'\x80\x05'):
                    return pickle.loads(data)
                # Otherwise it's likely compressed or JSON
            
            return data
        
        return await loop.run_in_executor(None, _get)
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: timedelta | None = None
    ) -> None:
        """Set with optimized serialization."""
        loop = asyncio.get_event_loop()
        
        def _set() -> None:
            # Serialize complex types with pickle for performance
            # Only use raw value for simple types already supported by diskcache
            data: Any
            if isinstance(value, str | int | float | bool | type(None)):
                data = value
            elif isinstance(value, dict | list):
                # Keep JSON types as-is for diskcache's native handling
                data = value
            else:
                # Use pickle for all complex objects (Pydantic models, etc.)
                data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            
            expire = ttl.total_seconds() if ttl else self.default_ttl.total_seconds()
            self.cache.set(key, data, expire=expire)
        
        await loop.run_in_executor(None, _set)
    
    async def delete(self, key: str) -> bool:
        """Remove key from cache."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.cache.delete, key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: key in self.cache)
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        import fnmatch
        loop = asyncio.get_event_loop()
        
        def _clear() -> int:
            count = 0
            for key in list(self.cache.iterkeys()):
                if fnmatch.fnmatch(key, pattern):
                    del self.cache[key]
                    count += 1
            return count
        
        return await loop.run_in_executor(None, _clear)
    
    async def clear_all(self) -> None:
        """Clear all cached items."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.cache.clear)
    
    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        loop = asyncio.get_event_loop()
        
        def _stats() -> dict[str, Any]:
            return {
                "hits": self.cache.stats()["hits"],
                "misses": self.cache.stats()["misses"],
                "size": self.cache.volume(),
                "count": len(self.cache),
            }
        
        return await loop.run_in_executor(None, _stats)
    
    def close(self) -> None:
        """Close the cache connection."""
        self.cache.close()