"""Core caching infrastructure with abstract backend and unified types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CacheNamespace(str, Enum):
    """Cache namespaces for organized storage."""

    SEMANTIC = "semantic"
    TRIE = "trie"
    VOCABULARY = "vocabulary"
    SEARCH = "search"
    API = "api"
    COMPUTE = "compute"
    OPENAI = "openai_structured"
    CORPUS = "corpus"


# Standardized TTL values based on data volatility
class CacheTTL:
    """Standardized TTL values for different cache types."""

    # Static data that rarely changes
    VOCABULARY = None  # No expiration for vocabulary
    CORPUS = timedelta(days=30)  # Corpus data refreshed monthly

    # Semi-static indices
    SEMANTIC = timedelta(days=7)  # Semantic search instances refreshed weekly
    SEMANTIC_INDEX = timedelta(days=7)  # Semantic indices refreshed weekly
    TRIE_INDEX = timedelta(days=7)  # Trie indices refreshed weekly

    # Dynamic search results
    SEARCH_RESULT = timedelta(hours=1)  # Search results cached for 1 hour
    API_RESPONSE = timedelta(hours=24)  # API responses cached for 24 hours

    # Computation results
    COMPUTATION = timedelta(days=7)  # Expensive computations cached for a week
    AI_GENERATION = timedelta(days=30)  # AI-generated content cached for a month


class CompressionType(str, Enum):
    """Compression algorithms for cache data."""

    NONE = "none"  # No compression
    ZLIB = "zlib"  # Standard zlib compression (default)
    GZIP = "gzip"  # Gzip compression (for compatibility)


class QuantizationType(str, Enum):
    """Quantization types for semantic embeddings."""

    FLOAT32 = "float32"  # Full precision (default)
    FLOAT16 = "float16"  # Half precision (2x space savings)
    INT8 = "int8"  # 8-bit quantization (4x space savings, some accuracy loss)
    UINT8 = "uint8"  # Unsigned 8-bit (4x space savings, positive values only)


@dataclass
class CacheMetadata:
    """Metadata for cached items with compression and quantization info."""

    compression_type: CompressionType = CompressionType.NONE
    quantization_type: QuantizationType = QuantizationType.FLOAT32
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 1.0


class CacheBackend[T](ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, namespace: str, key: str, default: T | None = None) -> T | None:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(
        self,
        namespace: str,
        key: str,
        value: T,
        ttl: timedelta | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Set value in cache with optional TTL and tags."""
        pass

    @abstractmethod
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete specific cache entry."""
        pass

    @abstractmethod
    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all entries in a namespace."""
        pass

    @abstractmethod
    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """Invalidate entries by tags."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear entire cache."""
        pass

    @abstractmethod
    async def exists(self, namespace: str, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]:
        """Get cache statistics."""
        pass

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


__all__ = [
    "CacheBackend",
    "CacheNamespace",
    "CacheTTL",
    "CompressionType",
    "QuantizationType",
    "CacheMetadata",
]
