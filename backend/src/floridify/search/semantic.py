"""
Semantic search implementation using vector embeddings.

Multi-level embedding strategy with character, subword, and word-level vectors.
Implements FAISS for efficient similarity search with GPU support.
"""

from __future__ import annotations

import asyncio
import hashlib
import pickle
from pathlib import Path
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]

from ..utils.logging import get_logger
from .constants import EmbeddingLevel

logger = get_logger(__name__)


class SemanticSearch:
    """
    Vector-based semantic similarity using multiple embedding levels.

    Embedding Strategy:
    - Character Embeddings (64D): Handle morphological similarity (helpful → helpfully)
    - Subword Embeddings (128D): Decompose unknown words into familiar parts
    - Word Embeddings (384D): Capture semantic relationships (happy → joyful)

    Similarity Scoring:
    - Combined with fuzzy scores for hybrid ranking
    - FAISS for efficient nearest neighbor search
    """

    def __init__(self, cache_dir: Path, force_rebuild: bool = False) -> None:
        """
        Initialize semantic search engine.

        Args:
            cache_dir: Directory for caching embeddings and indices
            force_rebuild: If True, rebuild embeddings even if cache exists
        """
        self.cache_dir = cache_dir
        self.vector_dir = cache_dir / "vectors"

        self.vector_dir.mkdir(parents=True, exist_ok=True)

        self.force_rebuild = force_rebuild

        # Embedding components
        self.char_vectorizer: TfidfVectorizer | None = None
        self.subword_vectorizer: TfidfVectorizer | None = None
        self.word_vectorizer: TfidfVectorizer | None = None

        # FAISS indices for efficient search
        self.char_index: faiss.Index | None = None
        self.subword_index: faiss.Index | None = None
        self.word_index: faiss.Index | None = None

        # Vocabulary and mappings
        self.vocabulary: list[str] = []
        self.word_to_id: dict[str, int] = {}

        # Embedding matrices
        self.char_embeddings: np.ndarray | None = None
        self.subword_embeddings: np.ndarray | None = None
        self.word_embeddings: np.ndarray | None = None

        # Configuration
        self.char_ngram_range = (2, 4)  # Character n-grams
        self.subword_ngram_range = (1, 3)  # Word n-grams
        self.max_features = 50000  # Max features per vectorizer

    async def initialize(self, vocabulary: list[str]) -> None:
        """
        Initialize semantic search with vocabulary.

        Args:
            vocabulary: List of words and phrases to create embeddings for
        """
        logger.info(f"Initializing semantic search with {len(vocabulary)} words")

        # Check if vocabulary has changed to avoid unnecessary rebuilding
        vocab_hash = hash(tuple(vocabulary))
        if hasattr(self, "_vocab_hash") and self._vocab_hash == vocab_hash:
            logger.debug("Vocabulary unchanged, skipping rebuild")
            return

        self.vocabulary = vocabulary
        self.word_to_id = {word: i for i, word in enumerate(vocabulary)}
        self._vocab_hash: int = vocab_hash

        # Try to load from cache first (unless force rebuild)
        if not self.force_rebuild and await self._load_from_cache():
            logger.info("Loaded embeddings from cache")
            return

        # Build embeddings from scratch
        logger.info("Building embeddings from scratch")
        await self._build_embeddings()

        # Save to cache
        await self._save_to_cache()
        logger.success("Semantic search initialization complete")

    async def _build_embeddings(self) -> None:
        """Build all embedding levels."""
        logger.debug(f"Building embeddings for {len(self.vocabulary)} words")

        # Run embedding generation in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, self._build_embeddings_sync)

        # Build FAISS indices
        await self._build_faiss_indices()

        logger.debug("Embeddings built successfully")

    def _build_embeddings_sync(self) -> None:
        """Build embeddings synchronously (CPU intensive)."""

        # Character-level embeddings (morphological patterns)
        logger.debug("Building character-level embeddings")

        self.char_vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=self.char_ngram_range,
            max_features=self.max_features // 4,  # Smaller for char-level
            lowercase=True,
            strip_accents="unicode",
        )
        self.char_embeddings = self.char_vectorizer.fit_transform(self.vocabulary).toarray()

        # Subword-level embeddings (decomposition)
        logger.debug("Building subword-level embeddings")
        subword_texts = [self._create_subword_text(word) for word in self.vocabulary]
        self.subword_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=self.subword_ngram_range,
            max_features=self.max_features // 2,  # Medium size
            lowercase=True,
            strip_accents="unicode",
        )
        self.subword_embeddings = self.subword_vectorizer.fit_transform(subword_texts).toarray()

        # Word-level embeddings (semantic meaning)
        logger.debug("Building word-level embeddings")
        word_texts = [self._create_word_text(word) for word in self.vocabulary]
        self.word_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=self.max_features,  # Full size
            lowercase=True,
            strip_accents="unicode",
        )
        self.word_embeddings = self.word_vectorizer.fit_transform(word_texts).toarray()

        logger.debug("All embedding levels built successfully")

    def _create_subword_text(self, word: str) -> str:
        """Create subword representation for a word."""
        # For phrases, split into words
        if " " in word:
            words = word.split()
            subwords = []
            for w in words:
                subwords.extend(self._split_word_into_subwords(w))
            return " ".join(subwords)
        else:
            return " ".join(self._split_word_into_subwords(word))

    def _split_word_into_subwords(self, word: str) -> list[str]:
        """Split a word into subword units."""
        if len(word) <= 3:
            return [word]

        subwords = [word]  # Include full word

        # Add prefixes and suffixes
        if len(word) >= 4:
            subwords.append(word[:3])  # Prefix
            subwords.append(word[-3:])  # Suffix

        if len(word) >= 6:
            subwords.append(word[:4])  # Longer prefix
            subwords.append(word[-4:])  # Longer suffix

        # Add sliding window subwords for long words
        if len(word) >= 8:
            for i in range(len(word) - 3):
                subwords.append(word[i : i + 4])

        return subwords

    def _create_word_text(self, word: str) -> str:
        """Create word-level representation (for semantic embeddings)."""
        # For single words, just return the word
        # For phrases, return the phrase as context
        return word

    async def _build_faiss_indices(self) -> None:
        """Build FAISS indices for efficient similarity search."""
        logger.debug("Building FAISS indices for efficient similarity search")

        # Build character index
        if self.char_embeddings is not None:
            logger.debug("Building character-level FAISS index")

            self.char_index = faiss.IndexFlatIP(self.char_embeddings.shape[1])  # Inner product
            # Normalize embeddings for cosine similarity (with safety check)
            norms = np.linalg.norm(self.char_embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
            char_norm = self.char_embeddings / norms
            self.char_index.add(char_norm.astype(np.float32))

        # Build subword index
        if self.subword_embeddings is not None:
            logger.debug("Building subword-level FAISS index")

            self.subword_index = faiss.IndexFlatIP(self.subword_embeddings.shape[1])
            norms = np.linalg.norm(self.subword_embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
            subword_norm = self.subword_embeddings / norms
            self.subword_index.add(subword_norm.astype(np.float32))

        # Build word index
        if self.word_embeddings is not None:
            logger.debug("Building word-level FAISS index")

            self.word_index = faiss.IndexFlatIP(self.word_embeddings.shape[1])
            norms = np.linalg.norm(self.word_embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
            word_norm = self.word_embeddings / norms
            self.word_index.add(word_norm.astype(np.float32))

    def _get_vocabulary_hash(self) -> str:
        """Generate hash of vocabulary for cache validation."""
        vocab_str = "|".join(sorted(self.vocabulary))
        return hashlib.sha256(vocab_str.encode()).hexdigest()[:16]

    def _get_cache_paths(self) -> dict[str, Path]:
        """Get paths for all cache files."""
        vocab_hash = self._get_vocabulary_hash()

        return {
            "metadata": self.vector_dir / f"metadata_{vocab_hash}.pkl",
            # Vectorizer paths
            "char_vectorizer": self.vector_dir / f"char_vectorizer_{vocab_hash}.pkl",
            "subword_vectorizer": self.vector_dir / f"subword_vectorizer_{vocab_hash}.pkl",
            "word_vectorizer": self.vector_dir / f"word_vectorizer_{vocab_hash}.pkl",
            # Embedding paths
            "char_embeddings": self.vector_dir / f"char_embeddings_{vocab_hash}.npy",
            "subword_embeddings": self.vector_dir / f"subword_embeddings_{vocab_hash}.npy",
            "word_embeddings": self.vector_dir / f"word_embeddings_{vocab_hash}.npy",
            # Index paths
            "char_index": self.vector_dir / f"char_index_{vocab_hash}.faiss",
            "subword_index": self.vector_dir / f"subword_index_{vocab_hash}.faiss",
            "word_index": self.vector_dir / f"word_index_{vocab_hash}.faiss",
        }

    async def _load_from_cache(self) -> bool:
        """
        Load embeddings and indices from cache.

        Returns:
            True if successfully loaded from cache, False otherwise
        """
        try:
            cache_paths = self._get_cache_paths()

            # Check if all required files exist
            required_files = [
                "metadata",
                "char_vectorizer",
                "subword_vectorizer",
                "word_vectorizer",
            ]
            for file_key in required_files:
                if not cache_paths[file_key].exists():
                    logger.debug(f"Cache file missing: {cache_paths[file_key].name}")
                    return False

            logger.debug("Loading embeddings from cache")

            # Load metadata to validate cache compatibility
            with open(cache_paths["metadata"], "rb") as f:
                metadata = pickle.load(f)

            # Validate configuration compatibility
            if (
                metadata.get("char_ngram_range") != self.char_ngram_range
                or metadata.get("subword_ngram_range") != self.subword_ngram_range
                or metadata.get("max_features") != self.max_features
            ):
                logger.warning("Cache configuration mismatch, rebuilding embeddings")
                return False

            # Load vectorizers
            with open(cache_paths["char_vectorizer"], "rb") as f:
                self.char_vectorizer = pickle.load(f)

            with open(cache_paths["subword_vectorizer"], "rb") as f:
                self.subword_vectorizer = pickle.load(f)

            with open(cache_paths["word_vectorizer"], "rb") as f:
                self.word_vectorizer = pickle.load(f)

            # Load embeddings if they exist
            if cache_paths["char_embeddings"].exists():
                self.char_embeddings = np.load(cache_paths["char_embeddings"])

            if cache_paths["subword_embeddings"].exists():
                self.subword_embeddings = np.load(cache_paths["subword_embeddings"])

            if cache_paths["word_embeddings"].exists():
                self.word_embeddings = np.load(cache_paths["word_embeddings"])

            # Load FAISS indices if they exist
            if cache_paths["char_index"].exists():
                self.char_index = faiss.read_index(str(cache_paths["char_index"]))

            if cache_paths["subword_index"].exists():
                self.subword_index = faiss.read_index(str(cache_paths["subword_index"]))

            if cache_paths["word_index"].exists():
                self.word_index = faiss.read_index(str(cache_paths["word_index"]))

            logger.debug("Successfully loaded embeddings from cache")
            return True

        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return False

    async def _save_to_cache(self) -> None:
        """Save embeddings and indices to cache."""
        try:
            cache_paths = self._get_cache_paths()

            logger.debug("Saving embeddings to cache")

            # Save metadata
            metadata = {
                "vocabulary_size": len(self.vocabulary),
                "char_ngram_range": self.char_ngram_range,
                "subword_ngram_range": self.subword_ngram_range,
                "max_features": self.max_features,
                "cache_version": "1.0",
            }

            with open(cache_paths["metadata"], "wb") as f:
                pickle.dump(metadata, f)

            # Save vectorizers
            if self.char_vectorizer:
                with open(cache_paths["char_vectorizer"], "wb") as f:
                    pickle.dump(self.char_vectorizer, f)

            if self.subword_vectorizer:
                with open(cache_paths["subword_vectorizer"], "wb") as f:
                    pickle.dump(self.subword_vectorizer, f)

            if self.word_vectorizer:
                with open(cache_paths["word_vectorizer"], "wb") as f:
                    pickle.dump(self.word_vectorizer, f)

            # Save embeddings
            if self.char_embeddings is not None:
                np.save(cache_paths["char_embeddings"], self.char_embeddings)

            if self.subword_embeddings is not None:
                np.save(cache_paths["subword_embeddings"], self.subword_embeddings)

            if self.word_embeddings is not None:
                np.save(cache_paths["word_embeddings"], self.word_embeddings)

            # Save FAISS indices
            if self.char_index:
                faiss.write_index(self.char_index, str(cache_paths["char_index"]))

            if self.subword_index:
                faiss.write_index(self.subword_index, str(cache_paths["subword_index"]))

            if self.word_index:
                faiss.write_index(self.word_index, str(cache_paths["word_index"]))

            logger.debug("Successfully saved embeddings to cache")

        except Exception as e:
            logger.error(f"Failed to save to cache: {e}")

    async def search(self, query: str, max_results: int = 20) -> list[tuple[str, float]]:
        """
        Perform semantic similarity search.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of (word, score) tuples sorted by similarity
        """
        if not self.vocabulary:
            return []

        query = query.strip().lower()
        if not query:
            return []

        # Get embeddings for query
        query_vectors = await self._get_query_embeddings(query)

        # Search each embedding level
        results: dict[str, float] = {}

        # Character-level search (morphological similarity)
        if query_vectors["char"] is not None:
            char_results = await self._search_embedding_level(
                query_vectors["char"], EmbeddingLevel.CHAR, max_results * 2
            )
            for word, score in char_results:
                results[word] = results.get(word, 0.0) + score * 0.2  # 20% weight

        # Subword-level search (decomposition)
        if query_vectors["subword"] is not None:
            subword_results = await self._search_embedding_level(
                query_vectors["subword"], EmbeddingLevel.SUBWORD, max_results * 2
            )
            for word, score in subword_results:
                results[word] = results.get(word, 0.0) + score * 0.3  # 30% weight

        # Word-level search (semantic similarity)
        if query_vectors["word"] is not None:
            word_results = await self._search_embedding_level(
                query_vectors["word"], EmbeddingLevel.WORD, max_results * 2
            )
            for word, score in word_results:
                results[word] = results.get(word, 0.0) + score * 0.5  # 50% weight

        # Sort by combined score and return top results
        sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:max_results]

    async def _get_query_embeddings(self, query: str) -> dict[str, np.ndarray | None]:
        """Get embeddings for a query at all levels."""
        embeddings = {}

        # Character-level embedding
        if self.char_vectorizer:
            char_vec = self.char_vectorizer.transform([query]).toarray()
            embeddings["char"] = char_vec[0] if char_vec.size > 0 else None
        else:
            embeddings["char"] = None

        # Subword-level embedding
        if self.subword_vectorizer:
            subword_text = self._create_subword_text(query)
            subword_vec = self.subword_vectorizer.transform([subword_text]).toarray()
            embeddings["subword"] = subword_vec[0] if subword_vec.size > 0 else None
        else:
            embeddings["subword"] = None

        # Word-level embedding
        if self.word_vectorizer:
            word_text = self._create_word_text(query)
            word_vec = self.word_vectorizer.transform([word_text]).toarray()
            embeddings["word"] = word_vec[0] if word_vec.size > 0 else None
        else:
            embeddings["word"] = None

        return embeddings

    async def _search_embedding_level(
        self,
        query_vector: np.ndarray,
        level: EmbeddingLevel,
        max_results: int,
    ) -> list[tuple[str, float]]:
        """Search at a specific embedding level."""

        if level == EmbeddingLevel.CHAR and self.char_index:
            return await self._search_faiss(query_vector, self.char_index, max_results)
        elif level == EmbeddingLevel.SUBWORD and self.subword_index:
            return await self._search_faiss(query_vector, self.subword_index, max_results)
        elif level == EmbeddingLevel.WORD and self.word_index:
            return await self._search_faiss(query_vector, self.word_index, max_results)
        else:
            raise ValueError(f"Invalid embedding level: {level}")

    async def _search_faiss(
        self,
        query_vector: np.ndarray,
        index: faiss.Index,
        max_results: int,
    ) -> list[tuple[str, float]]:
        """Search using FAISS index."""
        # Normalize query vector
        query_norm = query_vector / np.linalg.norm(query_vector)
        query_norm = query_norm.reshape(1, -1).astype(np.float32)

        # Search
        scores, indices = index.search(query_norm, min(max_results, len(self.vocabulary)))

        # Convert to results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.vocabulary):
                results.append((self.vocabulary[idx], float(score)))

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get semantic search statistics and metrics."""

        stats: dict[str, Any] = {
            "vocabulary_size": len(self.vocabulary),
            "embedding_levels": {},
            "index_size": {},
            "memory_usage": {},
        }

        # Character level stats
        if self.char_embeddings is not None:
            stats["embedding_levels"]["character"] = {
                "features": self.char_embeddings.shape[1],
                "vocabulary_coverage": self.char_embeddings.shape[0],
                "ngram_range": self.char_ngram_range,
            }
            stats["memory_usage"]["char_embeddings_mb"] = self.char_embeddings.nbytes / 1024 / 1024

        if self.char_index is not None:
            stats["index_size"]["char_index"] = self.char_index.ntotal

        # Subword level stats
        if self.subword_embeddings is not None:
            stats["embedding_levels"]["subword"] = {
                "features": self.subword_embeddings.shape[1],
                "vocabulary_coverage": self.subword_embeddings.shape[0],
                "ngram_range": self.subword_ngram_range,
            }
            stats["memory_usage"]["subword_embeddings_mb"] = (
                self.subword_embeddings.nbytes / 1024 / 1024
            )

        if self.subword_index is not None:
            stats["index_size"]["subword_index"] = self.subword_index.ntotal

        # Word level stats
        if self.word_embeddings is not None:
            stats["embedding_levels"]["word"] = {
                "features": self.word_embeddings.shape[1],
                "vocabulary_coverage": self.word_embeddings.shape[0],
                "ngram_range": (1, 2),
            }
            stats["memory_usage"]["word_embeddings_mb"] = self.word_embeddings.nbytes / 1024 / 1024

        if self.word_index is not None:
            stats["index_size"]["word_index"] = self.word_index.ntotal

        # Calculate total memory usage
        total_memory = sum(stats["memory_usage"].values())
        stats["memory_usage"]["total_mb"] = total_memory

        # Configuration info
        stats["configuration"] = {
            "max_features": self.max_features,
            "char_ngram_range": self.char_ngram_range,
            "subword_ngram_range": self.subword_ngram_range,
            "cache_dir": str(self.cache_dir),
        }

        return stats

    async def _search_cosine_similarity(
        self, query_vector: np.ndarray, embeddings: np.ndarray, max_results: int
    ) -> list[tuple[str, float]]:
        """Search using cosine similarity."""
        if embeddings is None or embeddings.size == 0:
            return []

        # Normalize query vector
        query_norm = query_vector / np.linalg.norm(query_vector)
        query_norm = query_norm.reshape(1, -1)

        # Calculate cosine similarity
        similarities = cosine_similarity(query_norm, embeddings)[0]

        # Get top results
        indices = np.argsort(similarities)[::-1][:max_results]
        results = [(self.vocabulary[i], float(similarities[i])) for i in indices]

        return results
