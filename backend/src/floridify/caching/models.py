"""Unified cache models for consistent metadata management.

This module provides base models for cache-aware metadata that can be
inherited by all metadata classes throughout the system.
"""

from __future__ import annotations

from datetime import timedelta
from enum import Enum

from pydantic import BaseModel, Field


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
    BINARY = "binary"  # Binary quantization (8x space savings, high accuracy loss)


class CacheNamespace(str, Enum):
    """Cache namespaces for organized storage."""

    DEFAULT = "default"

    DICTIONARY = "dictionary"

    SEARCH = "search"

    CORPUS = "corpus"

    SEMANTIC = "semantic"

    TRIE = "trie"

    LEXICON = "lexicon"

    API = "api"

    OPENAI = "openai_structured"


# Standardized TTL values based on data volatility
class CacheTTL(Enum):
    """Standardized TTL values for different cache types."""

    # Static data that rarely changes
    VOCABULARY = None  # No expiration for vocabulary
    CORPUS = timedelta(days=30)  # Corpus data refreshed monthly

    # Semi-static indices
    SEMANTIC = timedelta(days=7)  # Semantic search instances refreshed weekly
    TRIE = timedelta(days=7)  # Trie indices refreshed weekly

    # Dynamic search results
    SEARCH_RESULT = timedelta(hours=1)  # Search results cached for 1 hour
    API_RESPONSE = timedelta(hours=24)  # API responses cached for 24 hours

    # Computation results
    COMPUTATION = timedelta(days=7)  # Expensive computations cached for a week
    AI_GENERATION = timedelta(days=30)  # AI-generated content cached for a month


class CacheableMetadata(BaseModel):
    """Base model for metadata with caching information.

    This provides the standard cache fields that should be used
    consistently across all metadata models.
    """

    # Cache identification
    cache_key: str | None = Field(
        default=None,
        description="Unique cache key for this resource",
    )
    cache_namespace: CacheNamespace | None = Field(
        default=None,
        description="Cache namespace for organization",
    )

    # Cache control
    cache_ttl: timedelta | None = Field(
        default=None,
        description="TTL as timedelta (not seconds)",
    )
    cache_tags: list[str] = Field(
        default_factory=list,
        description="Tags for cache invalidation",
    )

    def get_ttl_seconds(self) -> int | None:
        """Get TTL in seconds for backward compatibility.

        Returns:
            TTL in seconds or None

        """
        if self.cache_ttl is None:
            return None
        return int(self.cache_ttl.total_seconds())

    def set_ttl(self, ttl: timedelta | None) -> None:
        """Set TTL value.

        Args:
            ttl: Timedelta TTL value or None

        """
        self.cache_ttl = ttl

    def generate_cache_key(
        self,
        resource_type: str,
        resource_id: str,
        version: str | None = None,
        hash_value: str | None = None,
    ) -> str:
        """Generate standardized cache key.

        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            version: Optional version string
            hash_value: Optional hash value

        Returns:
            Standardized cache key

        """
        # Sanitize resource_id to be URL-safe
        safe_id = resource_id.replace("/", "_").replace(" ", "_").replace(":", "_")
        parts = [resource_type, safe_id]

        if version:
            parts.append(f"v{version}")
        if hash_value:
            parts.append(hash_value[:8])

        self.cache_key = ":".join(parts)
        return self.cache_key


class CacheConfig(BaseModel):
    """Configuration for cache operations.

    This replaces various ad-hoc config patterns with a unified model.
    """

    use_cache: bool = Field(
        default=True,
        description="Whether to use caching",
    )
    force_refresh: bool = Field(
        default=False,
        description="Force cache refresh even if valid",
    )
    namespace: CacheNamespace = Field(
        default=CacheNamespace.API,
        description="Cache namespace to use",
    )
    ttl: timedelta | None = Field(
        default=None,
        description="TTL override as timedelta",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Additional cache tags",
    )
    compression: bool = Field(
        default=True,
        description="Whether to compress cached data",
    )

    @classmethod
    def for_api(cls) -> CacheConfig:
        """Create config for API responses."""
        return cls(
            namespace=CacheNamespace.API,
            ttl=CacheTTL.API_RESPONSE,
        )

    @classmethod
    def for_corpus(cls) -> CacheConfig:
        """Create config for corpus data."""
        return cls(
            namespace=CacheNamespace.CORPUS,
            ttl=CacheTTL.CORPUS,
        )

    @classmethod
    def for_semantic(cls) -> CacheConfig:
        """Create config for semantic indices."""
        return cls(
            namespace=CacheNamespace.SEMANTIC,
            ttl=CacheTTL.SEMANTIC,
        )

    @classmethod
    def for_computation(cls) -> CacheConfig:
        """Create config for computation results."""
        return cls(
            namespace=CacheNamespace.COMPUTE,
            ttl=CacheTTL.COMPUTATION,
        )


class CacheStats(BaseModel):
    """Statistics for cache operations."""

    hits: int = Field(default=0, description="Cache hits")
    misses: int = Field(default=0, description="Cache misses")
    evictions: int = Field(default=0, description="Items evicted")
    size_bytes: int = Field(default=0, description="Total size in bytes")
    item_count: int = Field(default=0, description="Number of items")
    namespaces: dict[str, int] = Field(
        default_factory=dict,
        description="Items per namespace",
    )

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


__all__ = [
    "CacheConfig",
    "CacheNamespace",
    "CacheStats",
    "CacheTTL",
    "CacheableMetadata",
    "CompressionType",
    "QuantizationType",
]
