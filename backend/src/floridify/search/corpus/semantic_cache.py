"""
MongoDB models for semantic search index caching.

Stores FAISS indices and embeddings in MongoDB for fast retrieval.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum

from beanie import Document
from beanie.operators import RegEx
from pydantic import Field

from ...models.base import BaseMetadata


class IndexType(str, Enum):
    """Types of semantic indices."""

    SENTENCE = "sentence"
    CHARACTER = "char"
    SUBWORD = "subword"
    WORD = "word"


class QuantizationType(str, Enum):
    """Quantization methods for embedding compression."""

    NONE = "none"  # No quantization (float32)
    BINARY = "binary"  # Binary quantization (24x compression)
    SCALAR = "scalar"  # Scalar quantization (3.75x compression)
    PRODUCT = "product"  # Product quantization (variable compression)


class SemanticIndexCache(Document, BaseMetadata):
    """
    MongoDB storage for FAISS indices with TTL support.

    Follows existing patterns from ImageMedia for binary storage.
    """

    # Index identification
    vocabulary_hash: str = Field(..., description="Hash of vocabulary for cache validation")
    corpus_name: str | None = Field(None, description="Name of corpus this index belongs to")
    corpus_id: str | None = Field(
        None, description="ID of corpus this index belongs to (for cascading deletion)"
    )
    model_name: str = Field(..., description="Sentence transformer model name")
    index_type: IndexType = Field(..., description="Type of index (sentence/char/subword/word)")

    # File paths for cached data (hybrid approach)
    index_file_path: str = Field(..., description="Path to FAISS index file")
    embeddings_file_path: str = Field(..., description="Path to embeddings file")
    metadata_file_path: str = Field(..., description="Path to metadata file")
    lemma_file_path: str = Field(..., description="Path to lemmatization data file")

    # Modern compression features (2025 optimization)
    quantization_type: QuantizationType = Field(
        default=QuantizationType.BINARY, description="Compression method used"
    )
    compression_ratio: float = Field(default=1.0, description="Actual compression ratio achieved")
    original_size_bytes: int = Field(gt=0, description="Size before compression")

    # Metadata
    vocabulary_size: int = Field(gt=0, description="Number of items in vocabulary")
    dimension: int = Field(gt=0, description="Embedding dimensions")
    size_bytes: int = Field(gt=0, description="Total size of binary data (after compression)")

    # Performance metadata
    build_time_ms: float = Field(ge=0, description="Time taken to build index in milliseconds")

    # TTL support
    expires_at: datetime = Field(..., description="Expiration timestamp")

    class Settings:
        name = "semantic_index_cache"
        indexes = [
            "vocabulary_hash",
            "corpus_name",
            "corpus_id",
            "model_name",
            "index_type",
            [("vocabulary_hash", 1), ("model_name", 1), ("index_type", 1)],
            [("corpus_name", 1), ("model_name", 1)],
            [("corpus_id", 1)],  # For efficient cascading deletion
            [("expires_at", 1)],  # TTL index for automatic cleanup
        ]

    @classmethod
    async def get_or_none(
        cls, vocabulary_hash: str, model_name: str, index_type: IndexType
    ) -> SemanticIndexCache | None:
        """Get index from cache if it exists and hasn't expired."""
        cache_entry = await cls.find_one(
            cls.vocabulary_hash == vocabulary_hash,
            cls.model_name == model_name,
            cls.index_type == index_type,
            cls.expires_at > datetime.now(UTC),
        )
        return cache_entry

    @classmethod
    async def invalidate_corpus(cls, corpus_name: str) -> int:
        """Invalidate all indices for a corpus by name."""
        result = await cls.find(cls.corpus_name == corpus_name).delete()
        return result.deleted_count if result else 0

    @classmethod
    async def invalidate_corpus_by_id(cls, corpus_id: str) -> int:
        """Invalidate all indices for a corpus by ID (for cascading deletion)."""
        result = await cls.find(cls.corpus_id == corpus_id).delete()
        return result.deleted_count if result else 0

    @classmethod
    async def invalidate_vocabulary(cls, vocabulary_hash: str) -> int:
        """Invalidate all indices for a vocabulary hash."""
        result = await cls.find(cls.vocabulary_hash == vocabulary_hash).delete()
        return result.deleted_count if result else 0

    @classmethod
    async def cleanup_expired(cls) -> int:
        """Remove expired cache entries."""
        result = await cls.find(cls.expires_at < datetime.now(UTC)).delete()
        return result.deleted_count if result else 0

    @classmethod
    async def cleanup_by_pattern(cls, corpus_name_pattern: str) -> int:
        """Remove cache entries matching a corpus name pattern."""
        result = await cls.find(RegEx(cls.corpus_name, corpus_name_pattern, "i")).delete()
        return result.deleted_count if result else 0

    def refresh_ttl(self, ttl_hours: float = 168.0) -> None:
        """Refresh the TTL for this cache entry."""
        self.expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        self.mark_updated()
