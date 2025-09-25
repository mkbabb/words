"""Unified cache models for consistent metadata management.

This module provides base models for cache-aware metadata that can be
inherited by all metadata classes throughout the system.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, model_validator


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, values: Any) -> Any:
        """Populate missing defaults for new metadata documents."""
        if not isinstance(values, dict):
            return values

        if "version_info" not in values:
            content = values.get("content_inline") or {}
            content_str = json.dumps(content, sort_keys=True, default=str)
            values["version_info"] = VersionInfo(
                version="1.0.0",
                created_at=datetime.now(UTC),
                data_hash=hashlib.sha256(content_str.encode()).hexdigest(),
            )

        return values
