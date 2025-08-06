"""
Search models for corpus and semantic data storage.

Unified models for corpus storage, caching, and semantic indexing.
"""

from __future__ import annotations

from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.core import QuantizationType
from ..models.base import BaseMetadata
from ..models.definition import Language
from .constants import SearchMethod


class CorpusMetadata(Document, BaseMetadata):
    """
    Lightweight MongoDB storage for corpus metadata.
    
    Contains only metadata about corpus instances, similar to SemanticMetadata.
    The actual vocabulary data is stored in Corpus objects and cached separately.
    """

    # Identification
    corpus_name: str = Field(
        ..., description="Unique corpus name (e.g., 'language_search_en-fr')"
    )

    # Vocabulary metadata for cache management
    vocabulary_hash: str = Field(
        ..., description="Content-based hash for cache invalidation"
    )
    
    vocabulary_stats: dict[str, int] = Field(
        default_factory=dict,
        description="Vocabulary statistics (word_count, phrase_count, avg_length, etc.)",
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Semantic data reference (optional)
    semantic_data_id: PydanticObjectId | None = Field(
        None, description="Reference to semantic data"
    )

    class Settings:
        name = "corpus_metadata"
        indexes = [
            [("corpus_name", 1)],  # Unique index on corpus name
            [("semantic_data_id", 1)],  # Index for semantic relationship
            [("vocabulary_hash", 1)],  # Index for cache invalidation
        ]


class SemanticMetadata(Document, BaseMetadata):
    """
    MongoDB storage for semantic search metadata.

    Contains metadata about semantic search indices including vocabulary hash,
    model information, and corpus references for efficient caching and management.
    """

    # Corpus identification and bi-directional relationship
    corpus_data_id: PydanticObjectId | None = Field(
        None, description="Reference to CorpusData document"
    )
    vocabulary_hash: str = Field(
        ..., description="Hash of the vocabulary for cache invalidation"
    )

    # Model information
    model_name: str = Field(..., description="Sentence transformer model used")
    embedding_dimension: int = Field(..., description="Dimension of the embeddings")

    # Corpus metadata
    vocabulary_size: int = Field(
        ..., description="Number of unique terms in vocabulary"
    )

    # Performance metrics  
    build_time_ms: float = Field(..., description="Time taken to build embeddings")

    # Quantization settings
    quantization_type: QuantizationType = Field(
        default=QuantizationType.FLOAT32, description="Quantization type used for embeddings"
    )

    class Settings:
        name = "semantic_metadata"
        indexes = [
            [("corpus_data_id", 1)],  # Lookup by CorpusMetadata reference
            [
                ("vocabulary_hash", 1),
                ("model_name", 1),
            ],  # Compound index for cache lookup
        ]


class SearchResult(BaseModel):
    """Unified search result across all search methods."""

    word: str = Field(..., description="Matched word or phrase")
    lemmatized_word: str | None = Field(
        None, description="Lemmatized form of the word if applicable"
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    method: SearchMethod = Field(
        ..., description="Search method used (exact, fuzzy, semantic)"
    )
    is_phrase: bool = Field(
        default=False, description="True if this is a multi-word phrase"
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
                "is_phrase": False,
                "language": "en",
                "metadata": {"frequency": 1000},
            }
        }


__all__ = [
    "CorpusMetadata",
    "SemanticMetadata", 
    "SearchResult",
]
