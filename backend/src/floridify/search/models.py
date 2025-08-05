"""
Search models for corpus and semantic data storage.

Unified models for corpus storage, caching, and semantic indexing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field

from ..models.base import BaseMetadata


class CompressionType(str, Enum):
    """Compression method for storage - using ZSTD for optimal performance."""
    
    ZSTD = "zstd"  # Zstandard compression - best balance of speed and ratio


class CorpusData(Document, BaseMetadata):
    """
    MongoDB storage for corpus data.
    
    Stores words, phrases, and metadata for various corpus types.
    Supports bidirectional relationship with semantic indices.
    """
    
    # Identification
    corpus_name: str = Field(..., description="Unique corpus name (e.g., 'language_search_en-fr')")
    corpus_type: str = Field(..., description="Type of corpus")
    corpus_id: str = Field(..., description="Corpus ID")
    
    # Data
    words: list[str] = Field(default_factory=list, description="Word list")
    phrases: list[str] = Field(default_factory=list, description="Phrase list")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Semantic index reference (optional)
    semantic_index_id: PydanticObjectId | None = Field(None, description="Reference to semantic index")
    
    # TTL support
    expires_at: datetime = Field(..., description="Cache expiration")
    
    class Settings:
        name = "corpus_data"
        indexes = [
            [("corpus_name", 1)],  # Unique index on corpus name
            [("expires_at", 1)],  # TTL index
            [("corpus_type", 1), ("corpus_id", 1)],  # Compound index
            [("semantic_index_id", 1)],  # Index for semantic relationship
        ]
    
    def is_expired(self) -> bool:
        """Check if corpus has expired."""
        return datetime.now(UTC) > self.expires_at


class CorpusCacheEntry(Document, BaseMetadata):
    """
    MongoDB storage for compressed corpus data.
    
    Optimized for 270K+ word lookups with sub-millisecond performance.
    Uses ZSTD compression for optimal storage efficiency.
    """
    
    # Identification
    language: str = Field(..., description="Language of corpus")
    source_hash: str = Field(..., description="Hash of source configuration")
    corpus_version: str = Field(default="1.0", description="Corpus version")
    
    # Compressed data storage (ZSTD only)
    words_data: bytes = Field(..., description="Compressed words data")
    phrases_data: bytes = Field(..., description="Compressed phrases data")
    metadata_data: bytes = Field(..., description="Compressed metadata")
    
    # Compression metrics
    compression_ratio: float = Field(..., description="Overall compression ratio")
    original_size_bytes: int = Field(..., description="Original data size")
    compressed_size_bytes: int = Field(..., description="Compressed data size")
    
    # Corpus statistics
    word_count: int = Field(..., description="Number of words in corpus")
    phrase_count: int = Field(..., description="Number of phrases in corpus")
    total_entries: int = Field(..., description="Total entries (words + phrases)")
    
    # Performance metrics
    load_time_ms: float = Field(..., description="Time to load and decompress")
    compression_time_ms: float = Field(..., description="Time to compress data")
    
    # TTL support
    expires_at: datetime = Field(..., description="Cache expiration")
    
    class Settings:
        name = "corpus_cache"
        indexes = [
            [("language", 1), ("source_hash", 1)],  # Unique compound index
            [("expires_at", 1)],  # TTL index
            [("corpus_version", 1)],
        ]
    
    @classmethod
    async def get_cached_corpus(cls, language: str, source_hash: str) -> CorpusCacheEntry | None:
        """Get cached corpus data by language and source hash."""
        return await cls.find_one({
            "language": language,
            "source_hash": source_hash,
            "expires_at": {"$gt": datetime.now(UTC)}
        })
    
    @classmethod
    async def get_cache_stats(cls) -> dict[str, Any]:
        """Get cache statistics including compression ratios."""
        total_count = await cls.count()
        
        if total_count == 0:
            return {
                "total_entries": 0,
                "active_entries": 0,
                "expired_entries": 0,
                "average_compression_ratio": 0.0,
                "total_original_size_mb": 0.0,
                "total_compressed_size_mb": 0.0,
            }
        
        # Count expired entries
        now = datetime.now(UTC)
        expired_count = await cls.find(cls.expires_at < now).count()
        
        # Get compression statistics
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_original_size": {"$sum": "$original_size_bytes"},
                    "total_compressed_size": {"$sum": "$compressed_size_bytes"},
                    "avg_compression_ratio": {"$avg": "$compression_ratio"},
                }
            }
        ]
        
        stats = await cls.aggregate(pipeline).to_list()
        
        if stats:
            stat = stats[0]
            return {
                "total_entries": total_count,
                "active_entries": total_count - expired_count,
                "expired_entries": expired_count,
                "average_compression_ratio": round(stat["avg_compression_ratio"], 2),
                "total_original_size_mb": round(stat["total_original_size"] / 1024 / 1024, 2),
                "total_compressed_size_mb": round(stat["total_compressed_size"] / 1024 / 1024, 2),
            }
        
        return {
            "total_entries": total_count,
            "active_entries": total_count - expired_count,
            "expired_entries": expired_count,
            "average_compression_ratio": 0.0,
            "total_original_size_mb": 0.0,
            "total_compressed_size_mb": 0.0,
        }


class CorpusCompressionUtils:
    """Utilities for corpus data compression using ZSTD."""
    
    @staticmethod
    def compress_data(data: bytes) -> tuple[bytes, float]:
        """
        Compress data using ZSTD with fallback to zlib.
        
        Args:
            data: Raw data to compress
            
        Returns:
            Tuple of (compressed_data, compression_ratio)
        """
        import zlib
        
        original_size = len(data)
        
        try:
            import zstandard as zstd
            compressor = zstd.ZstdCompressor(level=3, threads=4)
            compressed = compressor.compress(data)
        except ImportError:
            # Fallback to zlib if zstd not available
            compressed = zlib.compress(data, level=6)
        
        compression_ratio = original_size / len(compressed) if len(compressed) > 0 else 1.0
        
        return compressed, compression_ratio
    
    @staticmethod
    def decompress_data(compressed_data: bytes) -> bytes:
        """
        Decompress data using ZSTD with fallback to zlib.
        
        Args:
            compressed_data: Compressed data
            
        Returns:
            Decompressed data
        """
        import zlib
        
        try:
            import zstandard as zstd
            decompressor = zstd.ZstdDecompressor()
            return decompressor.decompress(compressed_data)
        except ImportError:
            # Fallback to zlib
            return zlib.decompress(compressed_data)


class QuantizationType(str, Enum):
    """Quantization methods for embeddings to reduce memory usage."""
    
    NONE = "none"      # No quantization (float32)
    BINARY = "binary"  # Binary quantization (1-bit)
    SCALAR = "scalar"  # Scalar quantization (uint8)


class SemanticIndexCache(Document, BaseMetadata):
    """
    MongoDB storage for semantic search indices and embeddings.
    
    Supports corpus-specific caching with optional quantization.
    """
    
    # Identification
    vocabulary_hash: str = Field(..., description="Hash of vocabulary for cache validation")
    corpus_name: str = Field(..., description="Name of the corpus this index belongs to")
    corpus_id: str | None = Field(None, description="ID of corpus this index belongs to (for cascading deletion)")
    model_name: str = Field(..., description="Sentence transformer model used")
    
    # Corpus reference (bidirectional relationship)
    corpus_data_id: PydanticObjectId | None = Field(None, description="Reference to CorpusData document")
    
    # Index storage
    index_type: str = Field(..., description="Type of FAISS index")
    index_data: bytes = Field(..., description="Serialized FAISS index")
    embeddings_data: bytes | None = Field(None, description="Serialized embeddings")
    vocabulary_data: bytes = Field(..., description="Serialized vocabulary list")
    
    # Metadata
    vocabulary_size: int = Field(..., description="Number of items in vocabulary")
    dimension: int = Field(..., description="Embedding dimension")
    size_bytes: int = Field(..., description="Total size in bytes")
    build_time_ms: float = Field(..., description="Time to build index in milliseconds")
    
    # Quantization support
    quantization_type: QuantizationType = Field(
        default=QuantizationType.NONE,
        description="Type of quantization applied"
    )
    compression_ratio: float = Field(default=1.0, description="Compression ratio from quantization")
    original_size_bytes: int | None = Field(None, description="Original size before quantization")
    
    # TTL support
    expires_at: datetime = Field(..., description="When this cache expires")
    
    class Settings:
        name = "semantic_index_cache"
        indexes = [
            [("corpus_name", 1), ("vocabulary_hash", 1)],  # Unique compound index
            [("expires_at", 1)],  # TTL index
            [("model_name", 1)],
            [("corpus_id", 1)],  # For cascading deletion
            [("corpus_data_id", 1)],  # For bidirectional queries
        ]
    
    @classmethod
    async def invalidate_corpus(cls, corpus_name: str) -> int:
        """Invalidate all indices for a corpus."""
        result = await cls.find(cls.corpus_name == corpus_name).delete()
        return result.deleted_count if result else 0
    
    @classmethod
    async def invalidate_corpus_by_id(cls, corpus_id: str) -> int:
        """Invalidate all indices for a corpus by ID (for cascading deletion)."""
        result = await cls.find(cls.corpus_id == corpus_id).delete()
        return result.deleted_count if result else 0
    
    @classmethod
    async def get_cache_stats(cls) -> dict[str, Any]:
        """Get semantic cache statistics."""
        total_count = await cls.count()
        
        if total_count == 0:
            return {
                "total_indices": 0,
                "active_indices": 0,
                "expired_indices": 0,
                "quantized_indices": 0,
                "average_compression_ratio": 0.0,
                "total_size_mb": 0.0,
            }
        
        # Count expired entries
        now = datetime.now(UTC)
        expired_count = await cls.find(cls.expires_at < now).count()
        
        # Count quantized entries
        quantized_count = await cls.find(cls.quantization_type != QuantizationType.NONE).count()
        
        # Get size and compression statistics
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_size": {"$sum": "$size_bytes"},
                    "avg_compression_ratio": {"$avg": "$compression_ratio"},
                }
            }
        ]
        
        stats = await cls.aggregate(pipeline).to_list()
        
        if stats:
            stat = stats[0]
            return {
                "total_indices": total_count,
                "active_indices": total_count - expired_count,
                "expired_indices": expired_count,
                "quantized_indices": quantized_count,
                "average_compression_ratio": round(stat["avg_compression_ratio"], 2),
                "total_size_mb": round(stat["total_size"] / 1024 / 1024, 2),
            }
        
        return {
            "total_indices": total_count,
            "active_indices": total_count - expired_count,
            "expired_indices": expired_count,
            "quantized_indices": quantized_count,
            "average_compression_ratio": 0.0,
            "total_size_mb": 0.0,
        }


__all__ = [
    "CompressionType",
    "CorpusData",
    "CorpusCacheEntry",
    "CorpusCompressionUtils",
    "QuantizationType",
    "SemanticIndexCache",
]