"""Core caching infrastructure with abstract backend and unified types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from .models import (
    CacheNamespace,
    CacheTTL,
    CompressionType,
    QuantizationType,
)

T = TypeVar("T")


class CacheMetadata(BaseModel):
    """Metadata for cached items with compression and quantization info."""

    compression_type: CompressionType = Field(
        default=CompressionType.NONE,
        description="Compression algorithm used",
    )
    quantization_type: QuantizationType = Field(
        default=QuantizationType.FLOAT32,
        description="Quantization type for embeddings",
    )
    original_size: int = Field(
        default=0,
        description="Original size in bytes",
    )
    compressed_size: int = Field(
        default=0,
        description="Compressed size in bytes",
    )
    compression_ratio: float = Field(
        default=1.0,
        description="Compression ratio achieved",
    )


class CacheBackend[T](ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, namespace: str, key: str, default: T | None = None) -> T | None:
        """Get value from cache."""

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

    @abstractmethod
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete specific cache entry."""

    @abstractmethod
    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all entries in a namespace."""

    @abstractmethod
    async def invalidate_by_tags(self, tags: list[str]) -> int:
        """Invalidate entries by tags."""

    @abstractmethod
    async def clear(self) -> None:
        """Clear entire cache."""

    @abstractmethod
    async def exists(self, namespace: str, key: str) -> bool:
        """Check if key exists in cache."""

    @abstractmethod
    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]:
        """Get cache statistics."""

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
    "CacheMetadata",
    "CacheNamespace",
    "CacheTTL",
    "CompressionType",
    "QuantizationType",
]

# Re-export for backward compatibility
from .models import CacheableMetadata, CacheConfig, CacheStats  # noqa: E402

__all__ += ["CacheConfig", "CacheStats", "CacheableMetadata"]
