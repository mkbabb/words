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
from pydantic import BaseModel, Field, field_validator, model_validator
from pymongo import IndexModel
from uuid import uuid4
import hashlib


class CompressionType(str, Enum):
    """Compression algorithms for cache data.

    Algorithm selection is automatic based on content size:
    - < 1KB: No compression (None)
    - 1KB-10MB: ZSTD (best balance of speed and ratio)
    - > 10MB: GZIP (maximum compression)
    """

    ZSTD = "zstd"  # Zstandard - fast with good compression
    LZ4 = "lz4"  # LZ4 - extremely fast, moderate compression
    GZIP = "gzip"  # GZIP - slower but maximum compression


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

    # Metadata versioning control
    metadata_comparison_fields: list[str] | None = (
        None  # Fields that trigger new version if changed
    )

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

    def __eq__(self, other: object) -> bool:
        """Allow comparison with strings for backward compatibility."""
        if isinstance(other, str):
            return self.path == other
        return super().__eq__(other)


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
    # uuid: Immutable UUID that never changes across versions
    # CRITICAL: Required field, auto-generated if not provided via validator
    uuid: str = Field(description="Immutable UUID that persists across versions")
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

    # Pydantic configuration for MongoDB storage
    # CRITICAL: use_enum_values=True ensures enums are stored as strings in MongoDB
    # (MongoDB doesn't support Python enum objects natively)
    model_config = {
        "use_enum_values": True,  # Store enums as strings for MongoDB compatibility
        "arbitrary_types_allowed": True,
    }

    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            # UUID: Primary identifier that never changes across versions
            # Covers: uuid lookups (most common after migration)
            IndexModel([("uuid", 1)], unique=False, name="uuid_idx"),
            # UUID + Latest: Fast lookup of latest version by UUID
            IndexModel([("uuid", 1), ("version_info.is_latest", 1)], name="uuid_latest_idx"),
            # PRIMARY: Latest version lookup (most frequent query)
            # Covers: resource_id + is_latest filter + _id sort
            [("resource_id", 1), ("version_info.is_latest", 1), ("_id", -1)],
            # Specific version lookup
            # Covers: resource_id + exact version query
            [("resource_id", 1), ("version_info.version", 1)],
            # Content hash deduplication
            # Covers: resource_id + hash-based dedup during save
            [("resource_id", 1), ("version_info.data_hash", 1)],
            # Corpus.Metadata indices (sparse - only for Corpus documents)
            IndexModel([("corpus_name", 1)], sparse=True, name="corpus_name_sparse"),
            IndexModel([("vocabulary_hash", 1)], sparse=True, name="vocabulary_hash_sparse"),
            IndexModel([("parent_corpus_id", 1)], sparse=True, name="parent_corpus_id_sparse"),
            # Index metadata indices (sparse - for TrieIndex, SearchIndex, SemanticIndex)
            IndexModel([("corpus_id", 1)], sparse=True, name="corpus_id_sparse"),
        ]

    def __init_subclass__(
        cls,
        default_resource_type: ResourceType | None = None,
        default_namespace: CacheNamespace | None = None,
        **kwargs: Any,
    ) -> None:
        """Set field defaults for child classes to avoid field shadowing warnings.

        Child classes can specify their resource_type and namespace like:
            class MyMetadata(BaseVersionedData,
                           default_resource_type=ResourceType.CORPUS,
                           default_namespace=CacheNamespace.CORPUS):
                pass
        """
        super().__init_subclass__(**kwargs)

        # Set field defaults at class creation time
        if default_resource_type is not None:
            cls.model_fields["resource_type"].default = default_resource_type
        if default_namespace is not None:
            cls.model_fields["namespace"].default = default_namespace

        # Ensure polymorphic class identifier is unique per subclass
        # Only set _class_id if not explicitly annotated IN THIS CLASS (not inherited)
        # Note: All classes in Python 3.10+ have __annotations__ dict by default
        if "_class_id" not in cls.__annotations__:
            cls._class_id = cls.__qualname__

        # Keep Beanie's settings in sync so writes persist the correct discriminator
        try:
            settings = cls.get_settings()
            settings.class_id = "_class_id"
        except Exception:
            # get_settings may fail before Beanie initialization; best-effort update only
            pass

    @field_validator("namespace", mode="before")
    @classmethod
    def validate_namespace(cls, v: Any) -> CacheNamespace:
        """Convert string namespace back to enum when loading from MongoDB.

        MongoDB stores enums as strings due to use_enum_values=True.
        This validator ensures they're converted back to enums on load.
        """
        if isinstance(v, CacheNamespace):
            return v
        if isinstance(v, str):
            return CacheNamespace(v)
        return v

    @field_validator("content_location", mode="before")
    @classmethod
    def validate_content_location(cls, v: Any) -> ContentLocation | None:
        """Convert string paths to ContentLocation objects."""
        if v is None:
            return None
        if isinstance(v, ContentLocation):
            return v
        if isinstance(v, str):
            # Create a minimal ContentLocation for external paths

            return ContentLocation(
                storage_type=StorageType.S3 if v.startswith("s3://") else StorageType.CACHE,
                path=v,
                size_bytes=0,  # Unknown size
                checksum=hashlib.sha256(v.encode()).hexdigest(),
            )
        if isinstance(v, dict):
            return ContentLocation(**v)
        return v

    @model_validator(mode="before")
    @classmethod
    def _apply_defaults(cls, values: Any) -> Any:
        """Populate missing defaults for new metadata documents.

        CRITICAL: Ensures uuid is ALWAYS present. This prevents all hasattr/getattr hacks.
        """
        if not isinstance(values, dict):
            return values

        # CRITICAL FIX: Ensure uuid is always set
        if "uuid" not in values or not values["uuid"]:
            values["uuid"] = str(uuid4())

        if "version_info" not in values:
            content = values.get("content_inline") or {}
            content_str = json.dumps(content, sort_keys=True, default=str)
            values["version_info"] = VersionInfo(
                version="1.0.0",
                created_at=datetime.now(UTC),
                data_hash=hashlib.sha256(content_str.encode()).hexdigest(),
            )

        return values
