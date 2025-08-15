"""Versioned data models for caching and content management.

This module implements the V4 caching architecture with unified versioning,
automatic storage strategy selection, and content deduplication.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.models import CacheNamespace, CompressionType, QuantizationType
from ..models.base import BaseMetadata
from ..models.dictionary import CorpusType, Language
from ..models.literature import AuthorInfo, Genre, LiteratureSource, Period

# ============================================================================
# CORE ENUMS - Resource Types and Storage Configuration
# ============================================================================


class ResourceType(str, Enum):
    """Types of versioned resources in the system.

    Each resource type maps to a specific namespace and storage strategy.
    This enum drives the polymorphic behavior of the versioning system.
    """

    DICTIONARY = "dictionary"  # Dictionary entries from various providers
    CORPUS = "corpus"  # Vocabulary corpora for language processing
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


class BaseVersionedData(Document, BaseMetadata):
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
    access_count: int = 0
    last_accessed: datetime | None = None

    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            [("resource_id", 1), ("version_info.is_latest", -1)],
            [("namespace", 1), ("resource_type", 1)],
            [("version_info.created_at", -1)],
            "version_info.data_hash",
        ]

    async def get_content(self) -> Any | None:
        """Retrieve content whether inline or external.

        Provides unified access to content regardless of storage location.
        Handles decompression and deserialization transparently.
        """
        if self.content_inline is not None:
            return self.content_inline

        if self.content_location:
            # Delegate to storage backend to retrieve
            from ..caching.core import load_external_content

            return await load_external_content(self.content_location)

        return None

    async def set_content(self, content: Any, force_external: bool = False) -> None:
        """Store content with automatic strategy selection.

        Automatically determines inline vs external storage based on size.
        Large content is automatically compressed and stored externally.

        Args:
            content: Content to store
            force_external: Force external storage regardless of size
        """
        content_str = (
            json.dumps(content, sort_keys=True)
            if isinstance(content, dict | list)
            else str(content)
        )
        size_bytes = len(content_str.encode())

        # Threshold for external storage (1MB)
        if size_bytes > 1_000_000 or force_external:
            from ..caching.core import store_external_content

            self.content_location = await store_external_content(
                content,
                self.namespace,
                f"{self.resource_type.value}:{self.resource_id}:{self.version_info.version}",
            )
            self.content_inline = None
        else:
            self.content_inline = content
            self.content_location = None


class DictionaryEntryMetadata(BaseVersionedData):
    """Dictionary entry with versioning support.

    Can represent either raw provider data or AI-synthesized entries.
    Synthesized entries have model_info and source_provider_data_ids populated.
    """
    
    # Core identification
    word: str
    provider: str
    language: Language = Language.ENGLISH
    
    # For synthesized entries
    source_provider_data_ids: list[PydanticObjectId] = Field(default_factory=list)
    model_info: dict[str, Any] | None = None  # AI model info for synthesized entries
    
    # Provider-specific metadata
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Etymology and raw data location (external storage for large content)
    raw_data_location: ContentLocation | None = None

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.DICTIONARY)
        data.setdefault("namespace", CacheNamespace.DICTIONARY)
        super().__init__(**data)

    class Settings:
        pass


class CorpusMetadata(BaseVersionedData):
    """Corpus metadata with tree hierarchy for vocabulary management."""

    corpus_type: CorpusType
    language: Language

    # Tree hierarchy
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False

    # Vocabulary (external if large)
    vocabulary_size: int
    vocabulary_hash: str
    vocabulary: ContentLocation | None = None  # External storage for large vocabs

    # Statistics (external)
    word_frequencies: ContentLocation | None = None
    metadata_stats: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.CORPUS)
        data.setdefault("namespace", CacheNamespace.CORPUS)
        super().__init__(**data)


class LanguageCorpusMetadata(CorpusMetadata):
    """Language-level master corpus metadata."""

    # Aggregated statistics
    total_documents: int = 0
    total_tokens: int = 0
    unique_sources: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LANGUAGE
        data["is_master"] = True
        super().__init__(**data)


class LiteratureCorpusMetadata(CorpusMetadata):
    """Literature-based corpus metadata."""

    literature_data_ids: list[PydanticObjectId] = Field(default_factory=list)
    authors: list[AuthorInfo] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LITERATURE
        super().__init__(**data)


class SemanticIndexMetadata(BaseVersionedData):
    """FAISS semantic search index metadata."""

    corpus_id: PydanticObjectId
    corpus_version: str

    # Model configuration
    model_name: str
    embedding_dimension: int
    index_type: str = "faiss"
    quantization: QuantizationType | None = None

    # Metrics
    build_time_seconds: float
    memory_usage_mb: float
    num_vectors: int

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.SEMANTIC)
        data.setdefault("namespace", CacheNamespace.SEMANTIC)
        super().__init__(**data)


class LiteratureEntryMetadata(BaseVersionedData):
    """Literature work metadata with external content storage."""

    # Metadata
    title: str
    authors: list[AuthorInfo]  # Rich author information
    publication_year: int | None = None
    source: LiteratureSource
    language: Language
    
    # Genre and period classification
    primary_genre: Genre | None = None
    secondary_genres: list[Genre] = Field(default_factory=list)
    period: Period | None = None

    # Metrics
    text_hash: str
    text_size_bytes: int
    word_count: int
    unique_words: int
    readability_score: float | None = None

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.LITERATURE)
        data.setdefault("namespace", CacheNamespace.LITERATURE)
        super().__init__(**data)


class TrieIndexMetadata(BaseVersionedData):
    """Trie index metadata for prefix search."""

    corpus_ids: list[PydanticObjectId]
    node_count: int
    max_depth: int
    supports_fuzzy: bool = False
    memory_usage_bytes: int

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.TRIE)
        data.setdefault("namespace", CacheNamespace.TRIE)
        super().__init__(**data)


class SearchIndexMetadata(BaseVersionedData):
    """Composite search index metadata."""

    trie_index_id: PydanticObjectId | None = None
    semantic_index_id: PydanticObjectId | None = None
    corpus_id: PydanticObjectId

    # Configuration
    search_config: dict[str, Any] = Field(default_factory=dict)
    supported_languages: list[Language] = Field(default_factory=list)
    max_results: int = 100

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.SEARCH)
        data.setdefault("namespace", CacheNamespace.SEARCH)
        super().__init__(**data)
