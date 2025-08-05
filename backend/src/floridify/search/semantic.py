"""Semantic search using sentence embeddings and vector similarity."""

from __future__ import annotations

import asyncio
import json
import pickle
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

from ..models.definition import Language
from ..text import lemmatize_word, normalize_comprehensive
from ..text.search import get_vocabulary_hash
from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory
from .constants import SearchMethod
from .corpus.semantic_cache import IndexType, SemanticIndexCache

logger = get_logger(__name__)


class SearchResult(BaseModel):
    """Simple search result."""

    word: str = Field(..., description="Matched word or phrase")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: SearchMethod = Field(..., description="Search method used")
    language: Language = Field(..., description="Language of the result")




class SemanticSearch:
    """ULTRATHINK: Modern semantic search using state-of-the-art sentence transformers."""

    def __init__(
        self,
        corpus_name: str = "default",
        model_name: str = "all-MiniLM-L6-v2",
        force_rebuild: bool = False,
        ttl_hours: float = 168.0,  # 7 days
    ):
        """
        Initialize semantic search with modern sentence transformers.

        Args:
            corpus_name: Name of the corpus for caching
            model_name: Sentence transformer model to use
            force_rebuild: Force rebuilding embeddings even if cached
            ttl_hours: Time-to-live for cached embeddings in hours
        """
        self.corpus_name = corpus_name
        self.model_name = model_name
        self.force_rebuild = force_rebuild
        self.ttl_hours = ttl_hours

        # Streamlined models - only sentence transformers
        self.sentence_model: SentenceTransformer | None = None
        self.sentence_embeddings: np.ndarray | None = None
        self.sentence_index: faiss.Index | None = None

        # Vocabulary mapping
        self.vocabulary: list[str] = []
        self.word_to_id: dict[str, int] = {}
        self.lemma_to_word: dict[str, str] = {}

        # Modern file-based caching (2025 optimization)
        self.cache_dir = get_cache_directory("semantic")

    async def initialize(self, vocabulary: list[str]) -> None:
        """
        Initialize semantic search with lemmatized and normalized vocabulary.

        Args:
            vocabulary: List of words and phrases to create embeddings for
        """
        logger.info(
            f"Initializing streamlined semantic search with {len(vocabulary)} words using {self.model_name}"
        )

        # Check if vocabulary has changed to avoid unnecessary rebuilding
        vocab_hash = get_vocabulary_hash(vocabulary)
        if (
            hasattr(self, "_vocab_hash")
            and self._vocab_hash == vocab_hash
            and not self.force_rebuild
        ):
            logger.debug("Vocabulary unchanged, skipping rebuild")
            return

        self._vocab_hash: str = vocab_hash

        # Try to load from file cache first (unless force rebuild)
        if not self.force_rebuild and await self._load_from_file_cache(vocabulary):
            logger.info("Loaded embeddings from file cache")
            return

        # Build embeddings from scratch - do lemmatization and build
        logger.info("Building modern semantic embeddings (sentence transformers only)")

        # ULTRATHINK: Lemmatize and normalize vocabulary in ONE pass for maximum performance
        semantic_vocab, self.lemma_to_word = self._create_semantic_vocabulary(vocabulary)
        logger.info(
            f"Vocabulary optimized for semantic search: {len(vocabulary)} → {len(semantic_vocab)} unique lemmas"
        )

        self.vocabulary = semantic_vocab
        self.word_to_id = {word: i for i, word in enumerate(semantic_vocab)}

        start_time = time.time()
        await self._build_embeddings()
        build_time_ms = (time.time() - start_time) * 1000

        # Save to file cache for future use
        await self._save_to_file_cache(build_time_ms, vocabulary)

        # Save reference to MongoDB (required)
        await self._save_mongodb_reference(vocab_hash, build_time_ms)

    def _create_semantic_vocabulary(
        self, vocabulary: list[str]
    ) -> tuple[list[str], dict[str, str]]:
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
        # Initialize sentence transformer model
        self.sentence_model = SentenceTransformer(self.model_name)

        # Process in batches for memory efficiency
        batch_size = 32
        all_embeddings: list[np.ndarray] = []

        for i in range(0, len(self.vocabulary), batch_size):
            batch = self.vocabulary[i : i + batch_size]

            # Run embedding in executor to avoid blocking
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda batch=batch: self.sentence_model.encode(batch, normalize_embeddings=True)
                if self.sentence_model
                else np.array([]),
            )
            if embeddings.size > 0:
                all_embeddings.append(embeddings)

        # Combine all embeddings
        self.sentence_embeddings = np.vstack(all_embeddings).astype("float32")

        # Build FAISS index for sentence embeddings
        dimension = self.sentence_embeddings.shape[1]
        self.sentence_index = faiss.IndexFlatL2(dimension)
        self.sentence_index.add(self.sentence_embeddings)

        logger.info(
            f"Built semantic index with {len(self.vocabulary)} embeddings (dimension: {dimension})"
        )

    async def _load_from_file_cache(self, vocabulary: list[str]) -> bool:
        """
        Load embeddings and indices from file cache using memory mapping.

        Returns:
            True if successfully loaded from cache, False otherwise
        """
        try:
            vocab_hash = get_vocabulary_hash(vocabulary)
            logger.debug(
                f"Attempting to load semantic indices from file cache for vocab hash: {vocab_hash}"
            )

            # Define cache file paths
            index_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_index.faiss"
            embeddings_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_embeddings.npy"
            metadata_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_metadata.json"
            lemma_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_lemma.pkl"

            # Check if all required files exist
            missing_files = [
                f
                for f in [index_file, embeddings_file, metadata_file, lemma_file]
                if not f.exists()
            ]
            if missing_files:
                logger.debug(f"Cache files missing: {[f.name for f in missing_files]}")
                return False

            logger.info(f"Found cache files for vocab hash {vocab_hash}")

            # Load metadata to check validity
            with open(metadata_file) as f:
                metadata = json.load(f)

            # Check if cache is still valid (TTL)
            cache_time = datetime.fromisoformat(metadata["created_at"])
            if datetime.now(UTC) > cache_time + timedelta(hours=self.ttl_hours):
                logger.debug("Cache expired, rebuilding")
                return False

            # Load FAISS index
            logger.debug(f"Loading FAISS index from {index_file.name}")
            self.sentence_index = faiss.read_index(str(index_file))

            # Load embeddings with memory mapping for zero-copy access
            logger.debug(f"Loading embeddings from {embeddings_file.name} (memory-mapped)")
            self.sentence_embeddings = np.load(embeddings_file, mmap_mode="r")  # Read+copy on write

            # Load lemmatization data
            logger.debug(f"Loading lemmatization data from {lemma_file.name}")
            with open(lemma_file, "rb") as f:
                lemma_data = pickle.load(f)
                self.vocabulary = lemma_data["vocabulary"]
                self.lemma_to_word = lemma_data["lemma_to_word"]
                self.word_to_id = {word: i for i, word in enumerate(self.vocabulary)}

            # Lazy-load sentence model for querying (defer initialization)
            self.sentence_model = None  # Will be loaded on first query

            logger.info(
                f"Loaded semantic cache from files: {metadata['vocabulary_size']} embeddings, {metadata['build_time_ms']:.1f}ms original build (memory-mapped)"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to load from file cache: {e}")
            return False

    async def _save_to_file_cache(self, build_time_ms: float, vocabulary: list[str]) -> None:
        """Save embeddings and indices to file cache with MongoDB metadata."""
        try:
            vocab_hash = get_vocabulary_hash(vocabulary)
            expires_at = datetime.now(UTC) + timedelta(hours=self.ttl_hours)

            # Define cache file paths
            index_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_index.faiss"
            embeddings_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_embeddings.npy"
            metadata_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_metadata.json"
            lemma_file = self.cache_dir / f"{vocab_hash}_{self.model_name}_lemma.pkl"

            # Save FAISS index
            logger.debug(f"Saving FAISS index to {index_file.name}")
            faiss.write_index(self.sentence_index, str(index_file))

            # Save embeddings
            if self.sentence_embeddings is not None:
                logger.debug(
                    f"Saving embeddings to {embeddings_file.name} ({self.sentence_embeddings.nbytes / 1024 / 1024:.1f}MB)"
                )
                np.save(embeddings_file, self.sentence_embeddings)

            # Save lemmatization data
            logger.debug(f"Saving lemmatization data to {lemma_file.name}")
            lemma_data = {"vocabulary": self.vocabulary, "lemma_to_word": self.lemma_to_word}
            with open(lemma_file, "wb") as f:
                pickle.dump(lemma_data, f)

            # Save metadata
            metadata = {
                "vocabulary_size": len(self.vocabulary),
                "embedding_dim": self.sentence_embeddings.shape[1]
                if self.sentence_embeddings is not None
                else 0,
                "model_name": self.model_name,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": expires_at.isoformat(),
                "build_time_ms": build_time_ms,
            }
            with open(metadata_file, "w") as f:
                json.dump(metadata, f)

            total_size_mb = (
                sum(
                    f.stat().st_size
                    for f in [index_file, embeddings_file, metadata_file, lemma_file]
                    if f.exists()
                )
                / 1024
                / 1024
            )
            logger.info(
                f"Saved semantic cache to files ({len(self.vocabulary)} embeddings, {total_size_mb:.1f}MB total)"
            )

        except Exception as e:
            logger.error(f"Failed to save to file cache: {e}")

    async def _save_mongodb_reference(self, vocab_hash: str, build_time_ms: float) -> None:
        """Save reference to cache files in MongoDB (required)."""
        # Define all file paths
        index_path = str(self.cache_dir / f"{vocab_hash}_{self.model_name}_index.faiss")
        embeddings_path = str(self.cache_dir / f"{vocab_hash}_{self.model_name}_embeddings.npy")
        metadata_path = str(self.cache_dir / f"{vocab_hash}_{self.model_name}_metadata.json")
        lemma_path = str(self.cache_dir / f"{vocab_hash}_{self.model_name}_lemma.pkl")

        # Calculate total size of cache files
        total_size = 0
        for file_path in [index_path, embeddings_path, metadata_path, lemma_path]:
            if Path(file_path).exists():
                total_size += Path(file_path).stat().st_size

        existing = await SemanticIndexCache.find_one(
            {
                "vocabulary_hash": vocab_hash,
                "model_name": self.model_name,
                "corpus_name": self.corpus_name,
                "index_type": IndexType.SENTENCE,
            }
        )

        if existing:
            # Update existing entry
            existing.index_file_path = index_path
            existing.embeddings_file_path = embeddings_path
            existing.metadata_file_path = metadata_path
            existing.lemma_file_path = lemma_path
            existing.vocabulary_size = len(self.vocabulary)
            existing.dimension = (
                self.sentence_embeddings.shape[1] if self.sentence_embeddings is not None else 0
            )
            existing.expires_at = datetime.now(UTC) + timedelta(hours=self.ttl_hours)
            existing.build_time_ms = build_time_ms
            existing.mark_updated()
            await existing.save()
            logger.info(f"Updated MongoDB reference for semantic cache: {vocab_hash}")
        else:
            # Create new entry
            cache_entry = SemanticIndexCache(
                corpus_name=self.corpus_name,
                corpus_id=None,  # Will be set by corpus manager
                vocabulary_hash=vocab_hash,
                vocabulary_size=len(self.vocabulary),
                model_name=self.model_name,
                index_type=IndexType.SENTENCE,
                dimension=self.sentence_embeddings.shape[1]
                if self.sentence_embeddings is not None
                else 0,
                index_file_path=index_path,
                embeddings_file_path=embeddings_path,
                metadata_file_path=metadata_path,
                lemma_file_path=lemma_path,
                expires_at=datetime.now(UTC) + timedelta(hours=self.ttl_hours),
                build_time_ms=build_time_ms,
                size_bytes=total_size if total_size > 0 else 1,  # Must be > 0
                original_size_bytes=self.sentence_embeddings.nbytes
                if self.sentence_embeddings is not None
                else 0,
            )
            await cache_entry.save()
            logger.info(f"Created MongoDB reference for semantic cache: {vocab_hash}")

    async def search(
        self, query: str, max_results: int = 20, min_score: float = 0.0
    ) -> list[SearchResult]:
        """
        Perform semantic similarity search using sentence embeddings.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of search results with scores
        """
        if not self.sentence_index or not self.sentence_model:
            logger.warning("Semantic search not initialized")
            return []

        try:
            # Normalize and lemmatize the query
            normalized_query = normalize_comprehensive(query)
            if not normalized_query:
                return []

            # Generate query embedding
            query_embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sentence_model.encode([normalized_query], normalize_embeddings=True)
                if self.sentence_model
                else None,
            )

            if query_embedding is None:
                return []

            # Search using FAISS
            distances, indices = self.sentence_index.search(
                query_embedding.astype("float32"),
                max_results * 2,  # Get extra results for filtering
            )

            # Convert distances to similarity scores (1 - normalized_distance)
            # L2 distance range is [0, 2] for normalized vectors
            similarities = 1 - (distances[0] / 2)

            # Create results
            results = []
            for idx, similarity in zip(indices[0], similarities):
                if idx < 0 or similarity < min_score:
                    continue

                lemma = self.vocabulary[idx]
                original_word = self.lemma_to_word.get(lemma, lemma)

                results.append(
                    SearchResult(
                        word=original_word,
                        score=float(similarity),
                        method=SearchMethod.SEMANTIC,
                        language=Language.ENGLISH,  # TODO: Support multiple languages
                    )
                )

                if len(results) >= max_results:
                    break

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the semantic search index."""
        return {
            "initialized": bool(self.sentence_index),
            "vocabulary_size": len(self.vocabulary),
            "embedding_dim": self.sentence_embeddings.shape[1]
            if self.sentence_embeddings is not None
            else 0,
            "model_name": self.model_name,
            "corpus_name": self.corpus_name,
            "cache_dir": str(self.cache_dir),
        }
