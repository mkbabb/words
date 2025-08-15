"""Search models for corpus and semantic data storage.

Unified models for corpus storage, caching, and semantic indexing.
"""

from __future__ import annotations

from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.core import QuantizationType
from ..caching.models import CacheableMetadata
from ..models.base import BaseMetadata
from ..models.dictionary import Language
from .constants import SearchMethod


class SemanticMetadata(Document, BaseMetadata, CacheableMetadata):
    """MongoDB storage for semantic search metadata.

    Contains metadata about semantic search indices including vocabulary hash,
    model information, and corpus references for efficient caching and management.
    """

    # Corpus identification and bi-directional relationship
    corpus_id: PydanticObjectId | None = Field(
        None,
        description="Reference to CorpusMetadata document",
    )
    vocabulary_hash: str = Field(
        ...,
        description="Hash of the vocabulary for cache invalidation",
    )

    # Model information
    model_name: str = Field(..., description="Sentence transformer model used")
    embedding_dimension: int = Field(..., description="Dimension of the embeddings")

    # Corpus metadata
    vocabulary_size: int = Field(
        ...,
        description="Number of unique terms in vocabulary",
    )

    # Performance metrics
    build_time_ms: float = Field(..., description="Time taken to build embeddings")

    # Quantization settings
    quantization_type: QuantizationType = Field(
        default=QuantizationType.FLOAT32,
        description="Quantization type used for embeddings",
    )

    class Settings:
        name = "semantic_metadata"
        indexes = [
            [("corpus_id", 1)],  # Lookup by CorpusMetadata reference
            [
                ("vocabulary_hash", 1),
                ("model_name", 1),
            ],  # Compound index for cache lookup
        ]


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


__all__ = [
    "SearchResult",
    "SemanticMetadata",
]
