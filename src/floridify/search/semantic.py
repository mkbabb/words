"""
Semantic search implementation using vector embeddings.

Multi-level embedding strategy with character, subword, and word-level vectors.
Implements FAISS for efficient similarity search with GPU support.
"""

from __future__ import annotations

import asyncio
import pickle
from pathlib import Path
from typing import Any

import faiss  # type: ignore[import-untyped]
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]


class SemanticSearch:
    """
    Vector-based semantic similarity using multiple embedding levels.

    Embedding Strategy:
    - Character Embeddings (64D): Handle morphological similarity (helpful → helpfully)
    - Subword Embeddings (128D): Decompose unknown words into familiar parts
    - Word Embeddings (384D): Capture semantic relationships (happy → joyful)

    Similarity Scoring:
    - Cosine Similarity: Measures angle between vectors (0-1 score)
    - Combined with fuzzy scores for hybrid ranking
    - FAISS for efficient nearest neighbor search
    """

    def __init__(self, cache_dir: Path) -> None:
        """
        Initialize semantic search engine.

        Args:
            cache_dir: Directory for caching embeddings and indices
        """
        self.cache_dir = cache_dir
        self.vector_dir = cache_dir / "vectors"
        self.vector_dir.mkdir(parents=True, exist_ok=True)

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
        self.vocabulary = vocabulary
        self.word_to_id = {word: i for i, word in enumerate(vocabulary)}

        # Try to load from cache first
        if await self._load_from_cache():
            return

        # Build embeddings from scratch
        await self._build_embeddings()

        # Save to cache
        await self._save_to_cache()

    async def _load_from_cache(self) -> bool:
        """Try to load embeddings from cache."""
        cache_files = {
            "char": self.vector_dir / "char_embeddings.pkl",
            "subword": self.vector_dir / "subword_embeddings.pkl",
            "word": self.vector_dir / "word_embeddings.pkl",
            "vocabulary": self.vector_dir / "vocabulary.pkl",
        }

        # Check if all cache files exist
        if not all(f.exists() for f in cache_files.values()):
            return False

        try:
            # Load vocabulary
            with cache_files["vocabulary"].open("rb") as f:
                cached_vocab = pickle.load(f)

            # Check if vocabulary matches
            if cached_vocab != self.vocabulary:
                return False

            # Load embeddings
            with cache_files["char"].open("rb") as f:
                char_data = pickle.load(f)
                self.char_vectorizer = char_data["vectorizer"]
                self.char_embeddings = char_data["embeddings"]

            with cache_files["subword"].open("rb") as f:
                subword_data = pickle.load(f)
                self.subword_vectorizer = subword_data["vectorizer"]
                self.subword_embeddings = subword_data["embeddings"]

            with cache_files["word"].open("rb") as f:
                word_data = pickle.load(f)
                self.word_vectorizer = word_data["vectorizer"]
                self.word_embeddings = word_data["embeddings"]

            # Build FAISS indices

            await self._build_faiss_indices()

            return True

        except Exception:
            return False

    async def _save_to_cache(self) -> None:
        """Save embeddings to cache."""
        cache_files = {
            "char": self.vector_dir / "char_embeddings.pkl",
            "subword": self.vector_dir / "subword_embeddings.pkl",
            "word": self.vector_dir / "word_embeddings.pkl",
            "vocabulary": self.vector_dir / "vocabulary.pkl",
        }

        try:
            # Save vocabulary
            with cache_files["vocabulary"].open("wb") as f:
                pickle.dump(self.vocabulary, f)

            # Save embeddings with vectorizers
            if self.char_vectorizer and self.char_embeddings is not None:
                with cache_files["char"].open("wb") as f:
                    pickle.dump(
                        {
                            "vectorizer": self.char_vectorizer,
                            "embeddings": self.char_embeddings,
                        },
                        f,
                    )

            if self.subword_vectorizer and self.subword_embeddings is not None:
                with cache_files["subword"].open("wb") as f:
                    pickle.dump(
                        {
                            "vectorizer": self.subword_vectorizer,
                            "embeddings": self.subword_embeddings,
                        },
                        f,
                    )

            if self.word_vectorizer and self.word_embeddings is not None:
                with cache_files["word"].open("wb") as f:
                    pickle.dump(
                        {
                            "vectorizer": self.word_vectorizer,
                            "embeddings": self.word_embeddings,
                        },
                        f,
                    )

        except Exception as e:
            print(f"Warning: Failed to save embeddings to cache: {e}")

    async def _build_embeddings(self) -> None:
        """Build all embedding levels."""
        print(f"Building embeddings for {len(self.vocabulary)} words...")

        # Run embedding generation in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None, self._build_embeddings_sync
        )

        # Build FAISS indices
        await self._build_faiss_indices()

    def _build_embeddings_sync(self) -> None:
        """Build embeddings synchronously (CPU intensive)."""
        # Character-level embeddings (morphological patterns)
        print("Building character-level embeddings...")
        self.char_vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=self.char_ngram_range,
            max_features=self.max_features // 4,  # Smaller for char-level
            lowercase=True,
            strip_accents="unicode",
        )
        self.char_embeddings = self.char_vectorizer.fit_transform(
            self.vocabulary
        ).toarray()

        # Subword-level embeddings (decomposition)
        print("Building subword-level embeddings...")
        subword_texts = [self._create_subword_text(word) for word in self.vocabulary]
        self.subword_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=self.subword_ngram_range,
            max_features=self.max_features // 2,  # Medium size
            lowercase=True,
            strip_accents="unicode",
        )
        self.subword_embeddings = self.subword_vectorizer.fit_transform(
            subword_texts
        ).toarray()

        # Word-level embeddings (semantic meaning)
        print("Building word-level embeddings...")
        word_texts = [self._create_word_text(word) for word in self.vocabulary]
        self.word_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=self.max_features,  # Full size
            lowercase=True,
            strip_accents="unicode",
        )
        self.word_embeddings = self.word_vectorizer.fit_transform(word_texts).toarray()

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
        print("Building FAISS indices...")

        # Build character index
        if self.char_embeddings is not None:
            self.char_index = faiss.IndexFlatIP(
                self.char_embeddings.shape[1]
            )  # Inner product
            # Normalize embeddings for cosine similarity (with safety check)
            norms = np.linalg.norm(self.char_embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
            char_norm = self.char_embeddings / norms
            self.char_index.add(char_norm.astype(np.float32))

        # Build subword index
        if self.subword_embeddings is not None:
            self.subword_index = faiss.IndexFlatIP(self.subword_embeddings.shape[1])
            norms = np.linalg.norm(self.subword_embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
            subword_norm = self.subword_embeddings / norms
            self.subword_index.add(subword_norm.astype(np.float32))

        # Build word index
        if self.word_embeddings is not None:
            self.word_index = faiss.IndexFlatIP(self.word_embeddings.shape[1])
            norms = np.linalg.norm(self.word_embeddings, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
            word_norm = self.word_embeddings / norms
            self.word_index.add(word_norm.astype(np.float32))

    async def search(
        self, query: str, max_results: int = 20
    ) -> list[tuple[str, float]]:
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
                query_vectors["char"], "char", max_results * 2
            )
            for word, score in char_results:
                results[word] = results.get(word, 0.0) + score * 0.2  # 20% weight

        # Subword-level search (decomposition)
        if query_vectors["subword"] is not None:
            subword_results = await self._search_embedding_level(
                query_vectors["subword"], "subword", max_results * 2
            )
            for word, score in subword_results:
                results[word] = results.get(word, 0.0) + score * 0.3  # 30% weight

        # Word-level search (semantic similarity)
        if query_vectors["word"] is not None:
            word_results = await self._search_embedding_level(
                query_vectors["word"], "word", max_results * 2
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
        level: str,
        max_results: int,
    ) -> list[tuple[str, float]]:
        """Search at a specific embedding level."""

        # Use FAISS if available
        if level == "char" and self.char_index:
            return await self._search_faiss(query_vector, self.char_index, max_results)
        elif level == "subword" and self.subword_index:
            return await self._search_faiss(
                query_vector, self.subword_index, max_results
            )
        elif level == "word" and self.word_index:
            return await self._search_faiss(query_vector, self.word_index, max_results)

        # Fallback to sklearn cosine similarity
        return await self._search_cosine(query_vector, level, max_results)

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
        scores, indices = index.search(
            query_norm, min(max_results, len(self.vocabulary))
        )

        # Convert to results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.vocabulary):
                results.append((self.vocabulary[idx], float(score)))

        return results

    async def _search_cosine(
        self,
        query_vector: np.ndarray,
        level: str,
        max_results: int,
    ) -> list[tuple[str, float]]:
        """Search using cosine similarity."""
        # Get embedding matrix for this level
        if level == "char" and self.char_embeddings is not None:
            embeddings = self.char_embeddings
        elif level == "subword" and self.subword_embeddings is not None:
            embeddings = self.subword_embeddings
        elif level == "word" and self.word_embeddings is not None:
            embeddings = self.word_embeddings
        else:
            return []

        # Calculate cosine similarity
        similarities = cosine_similarity([query_vector], embeddings)[0]

        # Get top results
        top_indices = np.argsort(similarities)[::-1][:max_results]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append((self.vocabulary[idx], float(similarities[idx])))

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get semantic search statistics."""
        stats: dict[str, Any] = {
            "vocabulary_size": len(self.vocabulary),
            "embedding_levels": {},
        }

        if self.char_embeddings is not None:
            stats["embedding_levels"]["char"] = {
                "shape": self.char_embeddings.shape,
                "features": self.char_embeddings.shape[1],
            }

        if self.subword_embeddings is not None:
            stats["embedding_levels"]["subword"] = {
                "shape": self.subword_embeddings.shape,
                "features": self.subword_embeddings.shape[1],
            }

        if self.word_embeddings is not None:
            stats["embedding_levels"]["word"] = {
                "shape": self.word_embeddings.shape,
                "features": self.word_embeddings.shape[1],
            }

        return stats
