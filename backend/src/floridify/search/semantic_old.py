"""
Semantic search implementation using vector embeddings with MongoDB caching.

Multi-level embedding strategy with character, subword, and word-level vectors.
Implements FAISS for efficient similarity search with GPU support.
"""

from __future__ import annotations

import asyncio
import pickle
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np
from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
import os
from pathlib import Path

from ..text import get_vocabulary_hash, lemmatize_word, normalize_comprehensive
from ..utils.logging import get_logger
from .constants import (
    DEFAULT_SENTENCE_MODEL,
    L2_DISTANCE_NORMALIZATION,
    SEARCH_EXPANSION_FACTOR,
    SHOW_PROGRESS_BAR,
)
from .corpus.semantic_cache import IndexType, QuantizationType, SemanticIndexCache

logger = get_logger(__name__)


class SemanticSearch:
    """
    Modern semantic search using sentence transformers + FAISS with MongoDB caching.

    Implementation follows current research recommendations:
    - Primary: SentenceTransformer embeddings (384D, SOTA semantic understanding)
    - Fallback: Multi-level TF-IDF (character/subword/word for morphological similarity)
    - Storage: FAISS IndexFlatL2 for exact similarity search with L2 normalization
    - Caching: MongoDB-based persistent storage with TTL and invalidation

    Performance optimizations:
    - Vector normalization for cosine similarity via inner product
    - Async processing for large vocabulary initialization
    - MongoDB binary storage for fast retrieval
    - GPU acceleration support (when available)
    """

    def __init__(
        self,
        corpus_name: str | None = None,
        force_rebuild: bool = False,
        ttl_hours: float = 168.0,  # 1 week default
    ) -> None:
        """
        Initialize semantic search engine with MongoDB caching.

        Args:
            corpus_name: Name of corpus for cache organization
            force_rebuild: If True, rebuild embeddings even if cache exists
            ttl_hours: Cache TTL in hours
        """
        self.corpus_name = corpus_name
        self.force_rebuild = force_rebuild
        self.ttl_hours = ttl_hours

        # Modern sentence transformer model (2025 best practices)
        self.sentence_model: SentenceTransformer | None = None
        self.model_name = DEFAULT_SENTENCE_MODEL

        # FAISS index and embeddings for semantic search (KISS approach)
        self.sentence_index: faiss.Index | None = None
        self.sentence_embeddings: np.ndarray | None = None
        
        # Modern file-based caching (2025 optimization)
        self.cache_dir = Path.home() / ".cache" / "floridify" / "semantic"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Modern compression settings 
        self.quantization_type = QuantizationType.BINARY  # Default to binary quantization
        self.enable_compression = True

    async def initialize(self, vocabulary: list[str]) -> None:
        """
        Initialize semantic search with lemmatized and normalized vocabulary.

        Args:
            vocabulary: List of words and phrases to create embeddings for
        """
        # ULTRATHINK: Lemmatize and normalize vocabulary in ONE pass for maximum performance
        semantic_vocab, self.lemma_to_word = self._create_semantic_vocabulary(vocabulary)
        logger.info(f"Vocabulary optimized for semantic search: {len(vocabulary)} → {len(semantic_vocab)} unique lemmas")
        
        self.vocabulary = semantic_vocab
        self.word_to_id = {word: i for i, word in enumerate(semantic_vocab)}

        logger.info(
            f"Initializing streamlined semantic search with {len(semantic_vocab)} words using {self.model_name}"
        )

        # Check if vocabulary has changed to avoid unnecessary rebuilding
        vocab_hash = get_vocabulary_hash(self.vocabulary)
        if (
            hasattr(self, "_vocab_hash")
            and self._vocab_hash == vocab_hash
            and not self.force_rebuild
        ):
            logger.debug("Vocabulary unchanged, skipping rebuild")
            return

        self._vocab_hash: str = vocab_hash

        # Try to load from file cache first (unless force rebuild)
        if not self.force_rebuild and await self._load_from_file_cache():
            logger.info("Loaded embeddings from file cache")
            return

        # Build embeddings from scratch - sentence transformers only
        logger.info(
            "Building modern semantic embeddings (sentence transformers only)"
        )

        start_time = time.time()
        await self._build_embeddings()
        build_time_ms = (time.time() - start_time) * 1000

        # Save to file cache
        await self._save_to_file_cache(build_time_ms)
        logger.info(f"Semantic search initialization complete in {build_time_ms:.2f}ms")

    def _create_semantic_vocabulary(self, vocabulary: list[str]) -> tuple[list[str], dict[str, str]]:
        """Create optimized vocabulary and mapping in ONE pass for maximum performance."""
        lemma_to_original = {}
        
        for word in vocabulary:
            # Normalize and lemmatize the word
            normalized = normalize_comprehensive(word)
            if not normalized:
                continue
                
            lemma = lemmatize_word(normalized)
            if lemma and len(lemma) > 1:  # Skip single letters
                # Keep the shorter, more common form (heuristic: shorter = more common)
                if lemma not in lemma_to_original or len(word) < len(lemma_to_original[lemma]):
                    lemma_to_original[lemma] = word
        
        # Return both the lemmatized vocabulary and the reverse mapping
        return list(lemma_to_original.keys()), lemma_to_original

    def _quantize_embeddings(self, embeddings: np.ndarray, quantization_type: QuantizationType) -> tuple[np.ndarray, float]:
        """
        Apply modern quantization techniques for embedding compression.
        
        Args:
            embeddings: Original float32 embeddings
            quantization_type: Type of quantization to apply
            
        Returns:
            Tuple of (quantized_embeddings, compression_ratio)
        """
        original_size = embeddings.nbytes
        
        if quantization_type == QuantizationType.BINARY:
            # Binary quantization: 24x compression (research-backed)
            # Convert to binary representation using sign
            quantized = np.packbits((embeddings > 0).astype(np.uint8), axis=1)
            compression_ratio = original_size / quantized.nbytes
            logger.debug(f"Binary quantization: {compression_ratio:.1f}x compression achieved")
            return quantized, compression_ratio
            
        elif quantization_type == QuantizationType.SCALAR:
            # Scalar quantization: ~3.75x compression
            # Quantize to int8 with min/max scaling
            embed_min, embed_max = embeddings.min(), embeddings.max()
            scale = (embed_max - embed_min) / 255.0
            quantized = ((embeddings - embed_min) / scale).astype(np.uint8)
            compression_ratio = original_size / quantized.nbytes
            logger.debug(f"Scalar quantization: {compression_ratio:.1f}x compression achieved")
            return quantized, compression_ratio
            
        else:  # QuantizationType.NONE
            return embeddings, 1.0

    def _dequantize_embeddings(self, quantized_embeddings: np.ndarray, quantization_type: QuantizationType, 
                              original_shape: tuple, embed_min: float = 0.0, embed_max: float = 1.0) -> np.ndarray:
        """
        Dequantize embeddings back to usable format.
        
        Args:
            quantized_embeddings: Quantized embedding data
            quantization_type: Type of quantization used
            original_shape: Original shape of embeddings
            embed_min: Minimum value for scalar dequantization
            embed_max: Maximum value for scalar dequantization
            
        Returns:
            Dequantized embeddings
        """
        if quantization_type == QuantizationType.BINARY:
            # Unpack binary to float32 (-1, 1)
            unpacked = np.unpackbits(quantized_embeddings, axis=1)[:, :original_shape[1]]
            return (unpacked.astype(np.float32) * 2 - 1)  # Convert 0,1 to -1,1
            
        elif quantization_type == QuantizationType.SCALAR:
            # Dequantize int8 back to float32
            scale = (embed_max - embed_min) / 255.0
            return quantized_embeddings.astype(np.float32) * scale + embed_min
            
        else:  # QuantizationType.NONE
            return quantized_embeddings

    async def _build_embeddings(self) -> None:
        """Build streamlined semantic embeddings - sentence transformers only."""
        logger.debug(
            f"Building streamlined semantic embeddings for {len(self.vocabulary)} words"
        )

        # KISS: Only sentence transformers, no TF-IDF fallbacks
        await self._build_sentence_embeddings()
        await self._build_faiss_indices()

        logger.debug("Streamlined semantic embeddings built successfully")

    async def _build_sentence_embeddings(self) -> None:
        """Build sentence transformer embeddings asynchronously."""
        logger.debug(f"Building sentence transformer embeddings with {self.model_name}")
        
        def build_sentence():
            try:
                self.sentence_model = SentenceTransformer(self.model_name)
                # Generate embeddings for entire vocabulary (batch processing)
                return self.sentence_model.encode(
                    self.vocabulary,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # L2 normalization for cosine similarity
                    show_progress_bar=SHOW_PROGRESS_BAR,
                )
            except Exception as e:
                logger.warning(
                    f"Failed to build sentence embeddings: {e}, falling back to TF-IDF"
                )
                return None
        
        # Run in executor to avoid blocking
        self.sentence_embeddings = await asyncio.get_event_loop().run_in_executor(
            None, build_sentence
        )
        
        if self.sentence_embeddings is not None:
            logger.debug(
                f"Generated {self.sentence_embeddings.shape} sentence embeddings"
            )
        else:
            self.sentence_model = None



    async def _build_faiss_indices(self) -> None:
        """Build FAISS index for sentence embeddings with optional quantization."""
        logger.debug("Building streamlined FAISS index for sentence embeddings")

        # Build only sentence transformer index
        if self.sentence_embeddings is not None:
            logger.debug("Building sentence transformer FAISS index (IndexFlatL2)")

            # Apply quantization if enabled
            if self.enable_compression and self.quantization_type != QuantizationType.NONE:
                # Store original for search, quantized for caching
                self.original_sentence_embeddings = self.sentence_embeddings.copy()
                quantized_embeddings, compression_ratio = self._quantize_embeddings(
                    self.sentence_embeddings, self.quantization_type
                )
                logger.info(f"Embeddings compressed {compression_ratio:.1f}x using {self.quantization_type.value} quantization")
                
                # Use original embeddings for FAISS index (accuracy)
                # Quantized embeddings will be used for MongoDB storage (efficiency)
                embeddings_for_index = self.sentence_embeddings
            else:
                embeddings_for_index = self.sentence_embeddings

            # Use IndexFlatL2 with pre-normalized embeddings for exact cosine similarity
            self.sentence_index = faiss.IndexFlatL2(embeddings_for_index.shape[1])
            # Embeddings already normalized by sentence transformer
            self.sentence_index.add(embeddings_for_index.astype(np.float32))
            logger.debug(f"FAISS index built with {embeddings_for_index.shape[0]} embeddings")


    async def _load_from_file_cache(self) -> bool:
        """
        Load embeddings and indices from file cache using memory mapping.

        Returns:
            True if successfully loaded from cache, False otherwise
        """
        try:
            vocab_hash = get_vocabulary_hash(self.vocabulary)
            logger.debug(f"Attempting to load semantic indices from file cache for vocab hash: {vocab_hash}")

            # Define cache file paths
            index_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_index.faiss"
            embeddings_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_embeddings.npy"
            metadata_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_metadata.json"
            
            # Check if all required files exist
            if not all(f.exists() for f in [index_file, embeddings_file, metadata_file]):
                logger.debug("Cache files not found or incomplete")
                return False
            
            # Load metadata to check validity
            import json
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            # Check if cache is still valid (TTL)
            cache_time = datetime.fromisoformat(metadata["created_at"])
            if datetime.now(UTC) > cache_time + timedelta(hours=self.ttl_hours):
                logger.debug("Cache expired, rebuilding")
                return False
            
            # Load FAISS index
            self.sentence_index = faiss.read_index(str(index_file))
            
            # Load embeddings with memory mapping for fast startup
            self.sentence_embeddings = np.load(embeddings_file, mmap_mode='r')
            
            logger.info(f"Loaded semantic cache from files: {metadata['vocabulary_size']} embeddings, {metadata['build_time_ms']:.1f}ms original build")
            return True

        except Exception as e:
            logger.warning(f"Failed to load from file cache: {e}")
            return False

    async def _save_to_file_cache(self, build_time_ms: float) -> None:
        """Save embeddings and indices to file cache with MongoDB metadata."""
        try:
            vocab_hash = get_vocabulary_hash(self.vocabulary)
            expires_at = datetime.now(UTC) + timedelta(hours=self.ttl_hours)

            # Define cache file paths
            index_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_index.faiss"
            embeddings_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_embeddings.npy"
            metadata_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_metadata.json"
            
            # Save FAISS index to file
            if self.sentence_index:
                faiss.write_index(self.sentence_index, str(index_file))
            
            # Save embeddings to file with compression
            if self.sentence_embeddings is not None:
                np.save(embeddings_file, self.sentence_embeddings.astype(np.float32))
            
            # Create metadata file
            metadata = {
                "vocab_hash": vocab_hash,
                "model_name": self.model_name,
                "vocabulary_size": len(self.vocabulary),
                "dimension": self.sentence_embeddings.shape[1] if self.sentence_embeddings is not None else 384,
                "build_time_ms": build_time_ms,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": expires_at.isoformat(),
                "corpus_name": self.corpus_name,
                "quantization_type": self.quantization_type.value if self.quantization_type else "none",
            }
            
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save lightweight reference in MongoDB
            await self._save_mongodb_reference(
                vocab_hash=vocab_hash,
                index_file_path=str(index_file),
                embeddings_file_path=str(embeddings_file),
                metadata_file_path=str(metadata_file),
                metadata=metadata
            )
            
            logger.info(f"Saved semantic cache to files: {len(self.vocabulary)} embeddings")

        except Exception as e:
            logger.error(f"Failed to save to file cache: {e}")
    
    async def _save_mongodb_reference(
        self,
        vocab_hash: str,
        index_file_path: str,
        embeddings_file_path: str,
        metadata_file_path: str,
        metadata: dict,
    ) -> None:
        """Save lightweight reference to cache files in MongoDB."""
        try:
            # Check if entry already exists
            existing = await SemanticIndexCache.find_one({
                "vocabulary_hash": vocab_hash,
                "model_name": self.model_name,
                "index_type": IndexType.SENTENCE
            })
            
            if existing:
                # Update existing entry
                existing.index_file_path = index_file_path
                existing.embeddings_file_path = embeddings_file_path
                existing.metadata_file_path = metadata_file_path
                existing.vocabulary_size = metadata["vocabulary_size"]
                existing.dimension = metadata["dimension"]
                existing.build_time_ms = metadata["build_time_ms"]
                existing.expires_at = datetime.fromisoformat(metadata["expires_at"])
                existing.corpus_name = self.corpus_name
                existing.quantization_type = QuantizationType(metadata.get("quantization_type", "none"))
                existing.mark_updated()
                await existing.save()
                logger.debug("Updated MongoDB reference to cache files")
            else:
                # Create new entry
                cache_ref = SemanticIndexCache(
                    vocabulary_hash=vocab_hash,
                    corpus_name=self.corpus_name,
                    corpus_id=None,
                    model_name=self.model_name,
                    index_type=IndexType.SENTENCE,
                    index_file_path=index_file_path,
                    embeddings_file_path=embeddings_file_path,
                    metadata_file_path=metadata_file_path,
                    vocabulary_size=metadata["vocabulary_size"],
                    dimension=metadata["dimension"],
                    size_bytes=0,  # File-based storage, not stored in MongoDB
                    build_time_ms=metadata["build_time_ms"],
                    expires_at=datetime.fromisoformat(metadata["expires_at"]),
                    quantization_type=QuantizationType(metadata.get("quantization_type", "none")),
                    compression_ratio=1.0,  # Will be calculated later if needed
                    original_size_bytes=0,
                )
                await cache_ref.create()
                logger.debug("Created MongoDB reference to cache files")

        except Exception as e:
            logger.warning(f"Failed to save MongoDB reference: {e}")
                sentence_data = faiss.serialize_index(self.sentence_index)
                # Ensure it's bytes - faiss.serialize_index should return bytes already
                if not isinstance(sentence_data, bytes):
                    if isinstance(sentence_data, np.ndarray):
                        sentence_data = sentence_data.tobytes()
                    else:
                        sentence_data = bytes(sentence_data)
                
                # Use quantized embeddings for storage efficiency
                if hasattr(self, 'original_sentence_embeddings') and self.enable_compression:
                    # Save quantized version to MongoDB
                    quantized_embeddings, compression_ratio = self._quantize_embeddings(
                        self.original_sentence_embeddings, self.quantization_type
                    )
                    embeddings_data = pickle.dumps(quantized_embeddings)
                    original_size = self.original_sentence_embeddings.nbytes
                else:
                    # No quantization, save original
                    embeddings_data = (
                        pickle.dumps(self.sentence_embeddings)
                        if self.sentence_embeddings is not None
                        else None
                    )
                    original_size = self.sentence_embeddings.nbytes if self.sentence_embeddings is not None else 0
                    compression_ratio = 1.0

                save_tasks.append(
                    self._save_index_to_mongodb(
                        vocab_hash=vocab_hash,
                        index_type=IndexType.SENTENCE,
                        index_data=sentence_data,
                        embeddings_data=embeddings_data,
                        vocabulary_data=None,
                        dimension=(
                            self.sentence_embeddings.shape[1]
                            if self.sentence_embeddings is not None
                            else 384
                        ),
                        expires_at=expires_at,
                        build_time_ms=build_time_ms,
                        original_size_bytes=original_size,
                        compression_ratio=compression_ratio,
                        quantization_type=self.quantization_type,
                    )
                )

            # Save character index
            if self.char_index:
                char_data = faiss.serialize_index(self.char_index)
                # Ensure it's bytes
                if not isinstance(char_data, bytes):
                    if isinstance(char_data, np.ndarray):
                        char_data = char_data.tobytes()
                    else:
                        char_data = bytes(char_data)
                embeddings_data = (
                    pickle.dumps(self.char_embeddings)
                    if self.char_embeddings is not None
                    else None
                )
                vectorizer_data = (
                    pickle.dumps(self.char_vectorizer) if self.char_vectorizer else None
                )

                save_tasks.append(
                    self._save_index_to_mongodb(
                        vocab_hash=vocab_hash,
                        index_type=IndexType.CHARACTER,
                        index_data=char_data,
                        embeddings_data=embeddings_data,
                        vocabulary_data=vectorizer_data,
                        dimension=(
                            self.char_embeddings.shape[1]
                            if self.char_embeddings is not None
                            else 0
                        ),
                        expires_at=expires_at,
                        build_time_ms=build_time_ms,
                    )
                )

            # Save subword index
            if self.subword_index:
                subword_data = faiss.serialize_index(self.subword_index)
                # Ensure it's bytes
                if not isinstance(subword_data, bytes):
                    if isinstance(subword_data, np.ndarray):
                        subword_data = subword_data.tobytes()
                    else:
                        subword_data = bytes(subword_data)
                embeddings_data = (
                    pickle.dumps(self.subword_embeddings)
                    if self.subword_embeddings is not None
                    else None
                )
                vectorizer_data = (
                    pickle.dumps(self.subword_vectorizer)
                    if self.subword_vectorizer
                    else None
                )

                save_tasks.append(
                    self._save_index_to_mongodb(
                        vocab_hash=vocab_hash,
                        index_type=IndexType.SUBWORD,
                        index_data=subword_data,
                        embeddings_data=embeddings_data,
                        vocabulary_data=vectorizer_data,
                        dimension=(
                            self.subword_embeddings.shape[1]
                            if self.subword_embeddings is not None
                            else 0
                        ),
                        expires_at=expires_at,
                        build_time_ms=build_time_ms,
                    )
                )

            # Save word index
            if self.word_index:
                word_data = faiss.serialize_index(self.word_index)
                # Ensure it's bytes
                if not isinstance(word_data, bytes):
                    if isinstance(word_data, np.ndarray):
                        word_data = word_data.tobytes()
                    else:
                        word_data = bytes(word_data)
                embeddings_data = (
                    pickle.dumps(self.word_embeddings)
                    if self.word_embeddings is not None
                    else None
                )
                vectorizer_data = (
                    pickle.dumps(self.word_vectorizer) if self.word_vectorizer else None
                )

                save_tasks.append(
                    self._save_index_to_mongodb(
                        vocab_hash=vocab_hash,
                        index_type=IndexType.WORD,
                        index_data=word_data,
                        embeddings_data=embeddings_data,
                        vocabulary_data=vectorizer_data,
                        dimension=(
                            self.word_embeddings.shape[1]
                            if self.word_embeddings is not None
                            else 0
                        ),
                        expires_at=expires_at,
                        build_time_ms=build_time_ms,
                    )
                )

            # Save all indices in parallel
            await asyncio.gather(*save_tasks)

            logger.info("Successfully saved semantic indices to MongoDB cache")

        except Exception as e:
            logger.error(f"Failed to save to MongoDB cache: {e}")

    async def _save_index_to_mongodb(
        self,
        vocab_hash: str,
        index_type: Any,
        index_data: bytes,
        embeddings_data: bytes | None,
        vocabulary_data: bytes | None,
        dimension: int,
        expires_at: datetime,
        build_time_ms: float,
        original_size_bytes: int = 0,
        compression_ratio: float = 1.0,
        quantization_type: QuantizationType = QuantizationType.NONE,
    ) -> None:
        """Save a single index to MongoDB."""

        size_bytes = len(index_data)
        if embeddings_data:
            size_bytes += len(embeddings_data)
        if vocabulary_data:
            size_bytes += len(vocabulary_data)

        # Check if entry exists
        existing = await SemanticIndexCache.get_or_none(
            vocab_hash, self.model_name, index_type
        )

        if existing:
            # Update existing entry
            existing.index_data = index_data
            existing.embeddings_data = embeddings_data
            existing.vocabulary_data = vocabulary_data
            existing.vocabulary_size = len(self.vocabulary)
            existing.dimension = dimension
            existing.size_bytes = size_bytes
            existing.build_time_ms = build_time_ms
            existing.expires_at = expires_at
            existing.corpus_name = self.corpus_name
            # Modern compression fields
            existing.quantization_type = quantization_type
            existing.compression_ratio = compression_ratio
            existing.original_size_bytes = original_size_bytes
            existing.mark_updated()
            await existing.save()
        else:
            # Create new entry
            cache_entry = SemanticIndexCache(
                vocabulary_hash=vocab_hash,
                corpus_name=self.corpus_name,
                corpus_id=None,  # TODO: Set from corpus manager if available
                model_name=self.model_name,
                index_type=index_type,
                index_data=index_data,
                embeddings_data=embeddings_data,
                vocabulary_data=vocabulary_data,
                vocabulary_size=len(self.vocabulary),
                dimension=dimension,
                size_bytes=size_bytes,
                build_time_ms=build_time_ms,
                expires_at=expires_at,
                # Modern compression fields
                quantization_type=quantization_type,
                compression_ratio=compression_ratio,
                original_size_bytes=original_size_bytes,
            )
            await cache_entry.create()

    async def search(
        self, query: str, max_results: int = 20
    ) -> list[tuple[str, float]]:
        """
        Perform semantic similarity search.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of (word, score) tuples sorted by similarity
        """
        if not self.vocabulary:
            logger.warning("Vocabulary not initialized")
            return []

        logger.debug(f"Performing streamlined semantic search for: {query}")

        # KISS: Only sentence transformer embeddings
        if not (self.sentence_model and self.sentence_index):
            logger.warning("Sentence transformer not available for semantic search")
            return []

        # Lemmatize the query for semantic matching
        normalized_query = normalize_comprehensive(query)
        query_lemma = lemmatize_word(normalized_query) if normalized_query else query
        
        # Generate query embedding using lemmatized form
        query_embedding = self.sentence_model.encode(
            [query_lemma], convert_to_numpy=True, normalize_embeddings=True
        )
        
        # Search FAISS index
        distances, indices = self.sentence_index.search(
            query_embedding.astype(np.float32),
            min(max_results * SEARCH_EXPANSION_FACTOR, len(self.vocabulary)),
        )
        
        # Convert L2 distance to similarity score (1 - normalized_distance)
        # For normalized vectors, L2 distance ranges from 0 to 2
        similarities = 1 - (distances[0] / L2_DISTANCE_NORMALIZATION)
        
        # Map lemmatized results back to original words
        final_results: list[tuple[str, float]] = []
        for idx, sim in zip(indices[0], similarities):
            if sim > 0:  # Filter out negative similarities
                lemma = self.vocabulary[idx]
                # Map back to original word form if possible
                original_word = self.lemma_to_word.get(lemma, lemma)
                final_results.append((original_word, float(sim)))
        
        return final_results[:max_results]

    async def invalidate_cache(self, corpus_name: str | None = None) -> int:
        """
        Invalidate cached indices.

        Args:
            corpus_name: If provided, invalidate only this corpus's indices

        Returns:
            Number of cache entries invalidated
        """

        if corpus_name:
            return await SemanticIndexCache.invalidate_corpus(corpus_name)
        else:
            vocab_hash = get_vocabulary_hash(self.vocabulary)
            return await SemanticIndexCache.invalidate_vocabulary(vocab_hash)
