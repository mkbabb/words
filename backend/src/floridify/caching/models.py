"""Unified cache models for consistent metadata management.

This module provides base models for cache-aware metadata that can be
inherited by all metadata classes throughout the system.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class CompressionType(str, Enum):
    """Compression algorithms for cache data.

    Algorithm selection is automatic based on content size:
    - < 1KB: No compression
    - 1KB-10MB: ZSTD (best balance of speed and ratio)
    - > 10MB: GZIP (maximum compression)
    """

    ZSTD = "zstd"  # Zstandard - fast with good compression
    LZ4 = "lz4"  # LZ4 - extremely fast, moderate compression
    GZIP = "gzip"  # GZIP - slower but maximum compression
    NONE = "none"  # No compression
    ZLIB = "zlib"  # Standard zlib compression (legacy)


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

    LANGUAGE = "language"

    SEMANTIC = "semantic"

    TRIE = "trie"

    LITERATURE = "literature"

    LEXICON = "lexicon"

    API = "api"

    OPENAI = "openai_structured"

    SCRAPING = "scraping"

    WOTD = "wotd"


class ResourceType(str, Enum):
    """Types of versioned resources in the system.

    Each resource type maps to a specific namespace and storage strategy.
    This enum drives the polymorphic behavior of the versioning system.
    """

    DICTIONARY = "dictionary"  # Dictionary entries from various providers
    CORPUS = "corpus"  # Vocabulary corpora for language processing
    LANGUAGE = "language"  # Language provider entries and vocabulary
    SEMANTIC = "semantic"  # FAISS indices for semantic search
    LITERATURE = "literature"  # Full literary texts and metadata
    SEARCH = "search"  # Search indices and metadata
    TRIE = "trie"  # Trie indices for prefix search


class StorageType(str, Enum):
    """Backend storage types for content location.

    Determines where and how content is physically stored.
    The system automatically selects the appropriate storage based on size.
    """

    MEMORY = "memory"  # In-memory storage (for hot data)
    CACHE = "cache"  # Filesystem cache (default for most content)
    DATABASE = "database"  # MongoDB storage (for metadata)
    S3 = "s3"  # Cloud storage (future expansion)


# ============================================================================
# VERSION CONFIGURATION AND METADATA
# ============================================================================


class VersionConfig(BaseModel):
    """Configuration for version operations.

    Controls caching behavior, version management, and storage optimization
    for all versioned data operations.
    """

    # Cache control
    force_rebuild: bool = False  # Skip cache, force fresh fetch/rebuild
    use_cache: bool = True  # Whether to check cache first

    # Version control
    version: str | None = None  # Fetch specific version (None = latest)
    increment_version: bool = True  # Auto-increment version on save

    # Storage options
    ttl: timedelta | None = None
    compression: CompressionType | None = None  # None = auto-select

    # Operation metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContentLocation(BaseModel):
    """Metadata for externally stored content.

    Tracks where large content is stored when it exceeds the inline threshold.
    Provides all information needed to retrieve and verify external content.
    """

    storage_type: StorageType
    cache_namespace: CacheNamespace | None = None
    cache_key: str | None = None
    path: str | None = None
    compression: CompressionType | None = None
    size_bytes: int
    size_compressed: int | None = None
    checksum: str


class VersionInfo(BaseModel):
    """Version tracking with chain management.

    Implements a doubly-linked list of versions for complete history tracking.
    Supports dependency graphs for complex version relationships.
    """

    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data_hash: str
    is_latest: bool = True
    superseded_by: PydanticObjectId | None = None
    supersedes: PydanticObjectId | None = None
    dependencies: list[PydanticObjectId] = Field(default_factory=list)


# ============================================================================
# BASE VERSIONED DATA MODEL
# ============================================================================


class BaseVersionedData(Document):
    """Base class for all versioned data with content management.

    Provides automatic storage strategy selection, content deduplication,
    and version chain management. All versioned resources inherit from this.

    Storage Strategy:
    - Inline: Content < 1MB stored directly in document
    - External: Content >= 1MB stored in filesystem/S3 with reference
    """

    # Identification
    resource_id: str
    resource_type: ResourceType
    namespace: CacheNamespace

    # Versioning
    version_info: VersionInfo

    # Content storage
    content_location: ContentLocation | None = None
    content_inline: dict[str, Any] | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    ttl: timedelta | None = None

    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            [("resource_id", 1), ("version_info.is_latest", -1)],
            [("namespace", 1), ("resource_type", 1)],
            [("version_info.created_at", -1)],
            "version_info.data_hash",
        ]

    # get_content method removed - use get_versioned_content() from caching.core instead

    async def set_content(self, content: Any, force_external: bool = False) -> None:
        """Store content with automatic strategy selection.

        Args:
            content: The content to store
            force_external: If True, force external storage regardless of size

        Storage strategy:
        - Small content (< 16KB): Inline storage
        - Large content (>= 16KB) or force_external: External storage
        """
        import json

        from ..caching import get_global_cache

        # Serialize to measure size with ObjectId handling
        def json_encoder(obj: Any) -> str:
            from enum import Enum

            from beanie import PydanticObjectId

            if isinstance(obj, PydanticObjectId):
                return str(obj)
            elif isinstance(obj, Enum):
                return str(obj.value)
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        content_str = json.dumps(content, sort_keys=True, default=json_encoder)
        content_size = len(content_str.encode())

        # Size threshold for inline vs external storage (16KB)
        size_threshold = 16 * 1024

        if not force_external and content_size < size_threshold:
            # Store inline
            self.content_inline = content
            self.content_location = None
        else:
            # Store externally
            cache = await get_global_cache()
            cache_key = f"{self.resource_type.value}:{self.resource_id}:content:{self.version_info.data_hash[:8]}"

            await cache.set(
                namespace=self.namespace, key=cache_key, value=content, ttl_override=self.ttl
            )

            import hashlib

            self.content_location = ContentLocation(
                cache_namespace=self.namespace,
                cache_key=cache_key,
                storage_type=StorageType.CACHE,
                size_bytes=content_size,
                checksum=hashlib.sha256(content_str.encode()).hexdigest(),
            )
            self.content_inline = None
