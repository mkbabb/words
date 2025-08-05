"""
Modern semantic search implementation with file-based caching.

KISS approach: Only sentence transformers, file-based caching, memory mapping.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np
from sentence_transformers import SentenceTransformer

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
    Modern semantic search using sentence transformers + FAISS with file-based caching.
    
    Clean 2025 implementation:
    - KISS: Only sentence transformers, no TF-IDF fallbacks
    - File-based caching with memory mapping for fast startup
    - MongoDB stores lightweight references to cache files
    - Optimized vocabulary with lemmatization and deduplication
    """

    def __init__(
        self,
        corpus_name: str | None = None,
        force_rebuild: bool = False,
        ttl_hours: float = 168.0,  # 1 week default
    ) -> None:
        """
        Initialize semantic search engine with file-based caching.

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
        lemma_to_original: dict[str, str] = {}
        
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
        
        def build_sentence() -> np.ndarray | None:
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
                logger.error(f"Failed to build sentence embeddings: {e}")
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
            raise RuntimeError("Failed to build sentence embeddings")

    async def _build_faiss_indices(self) -> None:
        """Build FAISS index for sentence embeddings."""
        logger.debug("Building streamlined FAISS index for sentence embeddings")

        # Build only sentence transformer index
        if self.sentence_embeddings is not None:
            logger.debug("Building sentence transformer FAISS index (IndexFlatL2)")

            # Use IndexFlatL2 with pre-normalized embeddings for exact cosine similarity
            self.sentence_index = faiss.IndexFlatL2(self.sentence_embeddings.shape[1])
            # Embeddings already normalized by sentence transformer
            self.sentence_index.add(self.sentence_embeddings.astype(np.float32))
            logger.debug(f"FAISS index built with {self.sentence_embeddings.shape[0]} embeddings")

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
            
            # Initialize sentence model for querying
            self.sentence_model = SentenceTransformer(self.model_name)
            
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
                "quantization_type": "none",  # File-based storage, no quantization needed
            }
            
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
        metadata: dict[str, Any],
    ) -> None:
        """Save lightweight reference to cache files in MongoDB (optional)."""
        try:
            # Try to save MongoDB reference - gracefully handle if DB not available
            from beanie.exceptions import CollectionWasNotInitialized
            
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
                    existing.quantization_type = QuantizationType.NONE
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
                        quantization_type=QuantizationType.NONE,
                        compression_ratio=1.0,
                        original_size_bytes=0,
                    )
                    await cache_ref.create()
                    logger.debug("Created MongoDB reference to cache files")
                    
            except CollectionWasNotInitialized:
                logger.debug("MongoDB collections not initialized, skipping reference save (file cache still works)")
            except Exception as mongo_error:
                logger.debug(f"MongoDB reference save failed: {mongo_error} (file cache still works)")

        except Exception as e:
            logger.debug(f"Failed to save MongoDB reference: {e} (file cache still works)")

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
        Invalidate cached indices and files.

        Args:
            corpus_name: If provided, invalidate only this corpus's indices

        Returns:
            Number of cache entries invalidated
        """
        count = 0
        
        if corpus_name:
            # Find and delete MongoDB references
            entries = await SemanticIndexCache.find({"corpus_name": corpus_name}).to_list()
            for entry in entries:
                # Delete cache files
                for file_path in [entry.index_file_path, entry.embeddings_file_path, entry.metadata_file_path]:
                    if file_path and Path(file_path).exists():
                        Path(file_path).unlink()
                        logger.debug(f"Deleted cache file: {file_path}")
                
                # Delete MongoDB reference
                await entry.delete()
                count += 1
        else:
            # Delete all files for this vocabulary
            vocab_hash = get_vocabulary_hash(self.vocabulary)
            pattern = f"{vocab_hash}_{self.model_name}_*"
            
            for cache_file in self.cache_dir.glob(pattern):
                cache_file.unlink()
                logger.debug(f"Deleted cache file: {cache_file}")
                count += 1
        
        logger.info(f"Invalidated {count} cache entries")
        return count