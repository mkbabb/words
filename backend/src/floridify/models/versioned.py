"""Unified versioning models for all data types.

This module provides the core versioning infrastructure used throughout
the application for managing different versions of data with deduplication,
caching, and storage flexibility.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

from beanie import Document
from floridify.providers.literature.models import AuthorInfo
from pydantic import BaseModel, Field

from ..caching.models import CompressionType
from .base import BaseMetadata, PydanticObjectId
from .dictionary import CorpusType, DictionaryProvider, Language, LiteratureSource
import json


class StorageType(str, Enum):
    """Storage location type."""

    CACHE = "cache"
    DISK = "disk"
    MEMORY = "memory"
    DATABASE = "database"


class ContentLocation(BaseModel):
    """Location and metadata for stored content."""

    storage_type: StorageType
    cache_namespace: str | None = None
    cache_key: str | None = None
    file_path: str | None = None
    content_type: str = "json"
    compression_type: CompressionType = CompressionType.ZLIB
    size_bytes: int | None = None


class VersionInfo(BaseModel):
    """Version information for any versioned data."""

    version: str = Field(default="1.0.0", description="Semantic version")
    data_hash: str = Field(description="SHA256 hash of content for deduplication")
    is_latest: bool = Field(
        default=True, description="Whether this is the latest version"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    superseded_by: PydanticObjectId | None = None
    supersedes: PydanticObjectId | None = None


class VersionedData(Document, BaseMetadata):
    """Base class for all versioned data in the system."""

    # Core identification
    resource_id: str = Field(description="Unique identifier for the resource")
    resource_type: str = Field(
        description="Type of resource (word, corpus, semantic_index, etc.)"
    )

    # Versioning
    version_info: VersionInfo

    # Content storage
    content_location: ContentLocation | None = None
    content_inline: dict[str, Any] | None = None  # For small data

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    class Settings:
        name = "versioned_data"
        is_root = True
        indexes = [
            [("resource_id", 1), ("resource_type", 1), ("version_info.is_latest", -1)],
            [("resource_type", 1), ("version_info.is_latest", -1)],
            "version_info.data_hash",
            [("created_at", -1)],
            "tags",
        ]

    @classmethod
    def compute_hash(cls, content: Any) -> str:
        """Compute SHA256 hash of content."""
        if isinstance(content, dict) or isinstance(content, list | tuple):
            content_str = json.dumps(content, sort_keys=True)
        else:
            content_str = str(content)

        return hashlib.sha256(content_str.encode()).hexdigest()

    async def update_version_chain(self) -> None:
        """Update version chain when inserting new data."""
        if self.version_info.is_latest:
            # Mark previous versions as not latest
            await VersionedData.find(
                {
                    "resource_id": self.resource_id,
                    "resource_type": self.resource_type,
                    "version_info.is_latest": True,
                    "_id": {"$ne": self.id},
                },
            ).update_many(
                {
                    "$set": {
                        "version_info.is_latest": False,
                        "version_info.superseded_by": self.id,
                    }
                },
            )


# Specialized versioned data types


class DictionaryVersionedData(VersionedData):
    """Versioned data for dictionary providers."""

    word_id: PydanticObjectId | None = None
    word_text: str
    provider: DictionaryProvider
    language: Language = Language.ENGLISH

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "dictionary")
        super().__init__(**data)


class CorpusVersionedData(VersionedData):
    """Versioned data for corpus/lexicon data."""

    corpus_name: str
    language: Language
    corpus_type: CorpusType = Field(
        default=CorpusType.LEXICON, description="Type of corpus"
    )

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "corpus")
        super().__init__(**data)


class SemanticVersionedData(VersionedData):
    """Versioned data for semantic search indices."""

    corpus_id: PydanticObjectId | None = None
    model_name: str = Field(..., description="Sentence transformer model used")
    embedding_dimension: int = Field(..., description="Dimension of the embeddings")

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "semantic")
        super().__init__(**data)


class LiteratureVersionedData(VersionedData):
    """Versioned data for literature works."""

    corpus_id: PydanticObjectId
    author: AuthorInfo
    source: LiteratureSource

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", "literature")
        super().__init__(**data)


T = TypeVar("T", bound=VersionedData)


class VersionConfig(BaseModel):
    """Configuration for version management."""

    force_rebuild: bool = False
    check_cache: bool = True
    save_versions: bool = True
    max_versions: int | None = None  # None means keep all
    ttl: timedelta | None = None  # None means no expiration
