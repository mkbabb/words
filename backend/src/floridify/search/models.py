"""Search models for corpus and semantic data storage.

Unified models for corpus storage, caching, and semantic indexing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..models.dictionary import Language
from ..models.versioned import VersionInfo
from .constants import SearchMethod


class SearchResult(BaseModel):
    """Unified search result across all search methods."""

    word: str = Field(..., description="Matched word or phrase")
    lemmatized_word: str | None = Field(
        None,
        description="Lemmatized form of the word if applicable",
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    method: SearchMethod = Field(
        ...,
        description="Search method used (exact, fuzzy, semantic)",
    )
    language: Language | None = Field(None, description="Language code if applicable")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    def __lt__(self, other: SearchResult) -> bool:
        """Compare by score for sorting (higher score is better)."""
        return self.score > other.score

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "word": "example",
                "score": 0.95,
                "method": "exact",
                "language": "en",
                "metadata": {"frequency": 1000},
            },
        }


@dataclass
class TrieIndex:
    """Versioned trie index data for serialization.

    Stores the trie structure, word frequencies, and metadata
    for efficient persistence and recovery.
    """

    # Core trie data
    trie_data: bytes = field(default_factory=bytes)
    word_frequencies: dict[str, int] = field(default_factory=dict)

    # Statistics
    word_count: int = 0
    max_frequency: int = 0
    vocabulary_hash: str | None = None

    # Version information
    version_info: VersionInfo | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    model_version: str = "trie_v1"

    # Corpus metadata
    corpus_name: str | None = None
    corpus_language: Language | None = None


@dataclass
class SemanticMetadata:
    """Metadata for semantic search indices.

    Stores configuration and statistics for FAISS indices
    and sentence embeddings.
    """

    # Model configuration
    model_name: str
    embedding_dimension: int

    # Index statistics
    num_embeddings: int
    index_type: str  # "Flat", "IVF", "HNSW", etc.

    # Performance metrics
    build_time_seconds: float | None = None
    memory_usage_mb: float | None = None

    # Version information
    version_info: VersionInfo | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Corpus metadata
    corpus_name: str | None = None
    corpus_hash: str | None = None


@dataclass
class IndexMetadata:
    """Base metadata for all search indices.

    Provides common fields for versioning and tracking
    across different index types.
    """

    # Index identification
    index_type: str  # "trie", "fuzzy", "semantic"
    index_version: str  # e.g., "v1.0.0"

    # Corpus information
    corpus_name: str
    corpus_hash: str
    corpus_size: int

    # Version tracking
    version_info: VersionInfo | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Performance metrics
    build_time_seconds: float | None = None
    last_access_time: datetime | None = None
    access_count: int = 0


__all__ = [
    "SearchResult",
    "TrieIndex",
    "SemanticMetadata",
    "IndexMetadata",
]
