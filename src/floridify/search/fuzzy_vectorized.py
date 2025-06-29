"""Vectorized fuzzy search using embeddings and approximate nearest neighbors.

Implements state-of-the-art vector similarity search based on:
1. Character-level embeddings for morphological similarity
2. Subword embeddings (FastText-style) for handling OOV words
3. FAISS for efficient approximate nearest neighbor search
4. Multi-level embedding fusion for comprehensive similarity
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .enums import VectorSearchMethod


class CharacterEmbedder:
    """Character-level embedding for morphological similarity."""

    def __init__(self, embed_dim: int = 64, max_word_length: int = 20) -> None:
        self.embed_dim = embed_dim
        self.max_word_length = max_word_length

        # Character vocabulary (English + French + common symbols)
        self.char_vocab = self._build_char_vocab()
        self.char_to_idx = {char: idx for idx, char in enumerate(self.char_vocab)}
        self.vocab_size = len(self.char_vocab)

        # Initialize character embeddings (random, could be pre-trained)
        np.random.seed(42)  # Reproducible embeddings
        self.char_embeddings = np.random.randn(self.vocab_size, embed_dim).astype(np.float32)

    def _build_char_vocab(self) -> list[str]:
        """Build character vocabulary for multiple languages."""
        chars = []

        # Basic ASCII letters
        chars.extend([chr(i) for i in range(ord("a"), ord("z") + 1)])
        chars.extend([chr(i) for i in range(ord("A"), ord("Z") + 1)])

        # French accented characters
        french_chars = [
            "à",
            "á",
            "â",
            "ä",
            "ç",
            "è",
            "é",
            "ê",
            "ë",
            "ì",
            "í",
            "î",
            "ï",
            "ñ",
            "ò",
            "ó",
            "ô",
            "ö",
            "ù",
            "ú",
            "û",
            "ü",
            "ý",
            "ÿ",
            "À",
            "Á",
            "Â",
            "Ä",
            "Ç",
            "È",
            "É",
            "Ê",
            "Ë",
            "Ì",
            "Í",
            "Î",
            "Ï",
            "Ñ",
            "Ò",
            "Ó",
            "Ô",
            "Ö",
            "Ù",
            "Ú",
            "Û",
            "Ü",
            "Ý",
            "Ÿ",
        ]
        chars.extend(french_chars)

        # Special tokens
        chars.extend(["<PAD>", "<UNK>", "<START>", "<END>"])

        return chars

    def encode_word(self, word: str) -> Any:
        """Encode word as sequence of character embeddings."""
        # Pad or truncate word to max length
        word_chars = list(word.lower())[: self.max_word_length]
        word_chars += ["<PAD>"] * (self.max_word_length - len(word_chars))

        # Convert characters to indices
        char_indices = []
        for char in word_chars:
            if char in self.char_to_idx:
                char_indices.append(self.char_to_idx[char])
            else:
                char_indices.append(self.char_to_idx["<UNK>"])

        # Get embeddings and pool (mean pooling)
        char_embeds = self.char_embeddings[char_indices]

        # Mean pooling over character sequence
        word_embedding = np.mean(char_embeds, axis=0)

        return word_embedding.astype(np.float32)


class SubwordEmbedder:
    """FastText-style subword embeddings for handling unknown words."""

    def __init__(self, embed_dim: int = 100, min_n: int = 2, max_n: int = 5) -> None:
        self.embed_dim = embed_dim
        self.min_n = min_n
        self.max_n = max_n

        # Subword vocabulary will be built from training words
        self.subword_vocab: dict[str, int] = {}
        self.subword_embeddings: np.ndarray | None = None
        self._is_trained = False

    def _get_subwords(self, word: str) -> list[str]:
        """Extract character n-grams from word."""
        word_bounded = f"<{word.lower()}>"
        subwords = []

        for n in range(self.min_n, self.max_n + 1):
            for i in range(len(word_bounded) - n + 1):
                subwords.append(word_bounded[i : i + n])

        return subwords

    def build_vocab(self, words: list[str]) -> None:
        """Build subword vocabulary from word list."""
        subword_counts: dict[str, int] = {}

        # Count subword occurrences
        for word in words:
            subwords = self._get_subwords(word)
            for subword in subwords:
                subword_counts[subword] = subword_counts.get(subword, 0) + 1

        # Keep only frequent subwords (threshold can be tuned)
        min_freq = max(2, len(words) // 10000)  # Adaptive threshold
        self.subword_vocab = {
            subword: idx
            for idx, (subword, count) in enumerate(subword_counts.items())
            if count >= min_freq
        }

        # Initialize random embeddings
        vocab_size = len(self.subword_vocab)
        np.random.seed(42)
        self.subword_embeddings = np.random.randn(vocab_size, self.embed_dim).astype(np.float32)
        self._is_trained = True

    def encode_word(self, word: str) -> Any:
        """Encode word as average of subword embeddings."""
        if not self._is_trained:
            # Return zero vector if not trained
            return np.zeros(self.embed_dim, dtype=np.float32)

        subwords = self._get_subwords(word)
        valid_embeddings = []

        for subword in subwords:
            if subword in self.subword_vocab:
                idx = self.subword_vocab[subword]
                if self.subword_embeddings is not None and idx < len(self.subword_embeddings):
                    valid_embeddings.append(self.subword_embeddings[idx])

        if valid_embeddings:
            valid_array = np.array(valid_embeddings)
            return np.mean(valid_array, axis=0).astype(np.float32)
        else:
            # Fallback to zero vector for completely unknown words
            return np.zeros(self.embed_dim, dtype=np.float32)


class TFIDFEmbedder:
    """TF-IDF character n-gram embeddings for traditional similarity."""

    def __init__(self, ngram_range: tuple[int, int] = (2, 4), max_features: int = 10000) -> None:
        self.ngram_range = ngram_range
        self.max_features = max_features
        self.vectorizer: TfidfVectorizer | None = None
        self._is_trained = False

    def fit(self, words: list[str]) -> None:
        """Fit TF-IDF vectorizer on word list."""
        # Convert words to character n-grams
        char_docs = []
        for word in words:
            # Add spaces between characters for n-gram extraction
            char_doc = " ".join(word.lower())
            char_docs.append(char_doc)

        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=self.ngram_range,
            max_features=self.max_features,
            lowercase=True,
        )

        self.vectorizer.fit(char_docs)
        self._is_trained = True

    def encode_word(self, word: str) -> Any:
        """Encode word using TF-IDF character n-grams."""
        if not self._is_trained or self.vectorizer is None:
            return np.zeros(self.max_features, dtype=np.float32)

        char_doc = " ".join(word.lower())
        vector = self.vectorizer.transform([char_doc])
        return vector.toarray()[0].astype(np.float32)


class VectorizedFuzzySearch:
    """High-performance vectorized fuzzy search using multiple embedding strategies."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path("data/vector_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize embedders
        self.char_embedder = CharacterEmbedder(embed_dim=64)
        self.subword_embedder = SubwordEmbedder(embed_dim=100)
        self.tfidf_embedder = TFIDFEmbedder()

        # FAISS indices for different embedding types
        self.char_index: faiss.Index | None = None
        self.subword_index: faiss.Index | None = None
        self.tfidf_index: faiss.Index | None = None

        # Word mappings
        self.idx_to_word: dict[int, str] = {}
        self.word_to_idx: dict[str, int] = {}

        # Combined embeddings for fusion
        self.combined_embeddings: np.ndarray | None = None
        self.combined_index: faiss.Index | None = None

        self._is_built = False

    def build_index(self, words: list[str]) -> None:
        """Build vectorized search index from word list."""
        print(f"Building vectorized search index for {len(words)} words...")

        # Filter and clean words (allow spaces for phrases)
        clean_words = []
        for word in words:
            word_clean = word.strip().lower()
            # Allow letters, spaces, hyphens, and apostrophes for phrases
            if (
                word_clean
                and len(word_clean) > 1
                and word_clean.replace(" ", "").replace("-", "").replace("'", "").isalpha()
            ):
                clean_words.append(word_clean)

        # Remove duplicates while preserving order
        unique_words = list(dict.fromkeys(clean_words))
        print(f"Processing {len(unique_words)} unique words...")

        # Build word mappings
        self.idx_to_word = {idx: word for idx, word in enumerate(unique_words)}
        self.word_to_idx = {word: idx for idx, word in enumerate(unique_words)}

        # Train embedders
        print("Training subword embedder...")
        self.subword_embedder.build_vocab(unique_words)

        print("Training TF-IDF embedder...")
        self.tfidf_embedder.fit(unique_words)

        # Generate embeddings
        print("Generating character embeddings...")
        char_embeddings = np.array(
            [self.char_embedder.encode_word(word) for word in unique_words], dtype=np.float32
        )

        print("Generating subword embeddings...")
        subword_embeddings = np.array(
            [self.subword_embedder.encode_word(word) for word in unique_words], dtype=np.float32
        )

        print("Generating TF-IDF embeddings...")
        tfidf_embeddings = np.array(
            [self.tfidf_embedder.encode_word(word) for word in unique_words], dtype=np.float32
        )

        # Normalize embeddings
        char_embeddings = self._normalize_embeddings(char_embeddings)
        subword_embeddings = self._normalize_embeddings(subword_embeddings)
        tfidf_embeddings = self._normalize_embeddings(tfidf_embeddings)

        # Create FAISS indices
        print("Building FAISS indices...")

        # Character-level index
        char_dim = char_embeddings.shape[1]
        self.char_index = faiss.IndexFlatIP(char_dim)  # Inner product for normalized vectors
        self.char_index.add(char_embeddings)

        # Subword index
        subword_dim = subword_embeddings.shape[1]
        self.subword_index = faiss.IndexFlatIP(subword_dim)
        self.subword_index.add(subword_embeddings)

        # TF-IDF index
        tfidf_dim = tfidf_embeddings.shape[1]
        self.tfidf_index = faiss.IndexFlatIP(tfidf_dim)
        self.tfidf_index.add(tfidf_embeddings)

        # Combined fusion index
        print("Creating fusion embeddings...")
        self.combined_embeddings = np.concatenate(
            [
                char_embeddings * 0.3,  # Character similarity weight
                subword_embeddings * 0.5,  # Subword similarity weight
                tfidf_embeddings * 0.2,  # N-gram similarity weight
            ],
            axis=1,
        )

        combined_dim = self.combined_embeddings.shape[1]
        self.combined_index = faiss.IndexFlatIP(combined_dim)
        self.combined_index.add(self.combined_embeddings)

        self._is_built = True
        print("Vectorized search index built successfully!")

    def search(
        self, query: str, k: int = 20, method: VectorSearchMethod = VectorSearchMethod.FUSION
    ) -> list[tuple[str, float]]:
        """Search for similar words using vectorized approach."""
        if not self._is_built:
            return []

        query_clean = query.strip().lower()

        if method == VectorSearchMethod.CHARACTER:
            return self._search_character(query_clean, k)
        elif method == VectorSearchMethod.SUBWORD:
            return self._search_subword(query_clean, k)
        elif method == VectorSearchMethod.TFIDF:
            return self._search_tfidf(query_clean, k)
        elif method == VectorSearchMethod.FUSION:
            return self._search_fusion(query_clean, k)
        else:
            raise ValueError(f"Unknown search method: {method.value}")

    def _search_character(self, query: str, k: int) -> list[tuple[str, float]]:
        """Search using character-level embeddings."""
        if self.char_index is None:
            return []

        query_embed = self.char_embedder.encode_word(query)
        query_embed = query_embed / np.linalg.norm(query_embed)  # Normalize
        query_embed = query_embed.reshape(1, -1)

        scores, indices = self.char_index.search(query_embed, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:  # Valid result
                word = self.idx_to_word[idx]
                results.append((word, float(score)))

        return results

    def _search_subword(self, query: str, k: int) -> list[tuple[str, float]]:
        """Search using subword embeddings."""
        if self.subword_index is None:
            return []

        query_embed = self.subword_embedder.encode_word(query)
        query_embed = query_embed / (np.linalg.norm(query_embed) + 1e-8)  # Normalize
        query_embed = query_embed.reshape(1, -1)

        scores, indices = self.subword_index.search(query_embed, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                word = self.idx_to_word[idx]
                results.append((word, float(score)))

        return results

    def _search_tfidf(self, query: str, k: int) -> list[tuple[str, float]]:
        """Search using TF-IDF character n-grams."""
        if self.tfidf_index is None:
            return []

        query_embed = self.tfidf_embedder.encode_word(query)
        query_embed = query_embed / (np.linalg.norm(query_embed) + 1e-8)  # Normalize
        query_embed = query_embed.reshape(1, -1)

        scores, indices = self.tfidf_index.search(query_embed, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                word = self.idx_to_word[idx]
                results.append((word, float(score)))

        return results

    def _search_fusion(self, query: str, k: int) -> list[tuple[str, float]]:
        """Search using fused embeddings from all methods."""
        if self.combined_index is None:
            return []

        # Generate query embedding using all methods
        char_embed = self.char_embedder.encode_word(query)
        char_embed = char_embed / (np.linalg.norm(char_embed) + 1e-8)

        subword_embed = self.subword_embedder.encode_word(query)
        subword_embed = subword_embed / (np.linalg.norm(subword_embed) + 1e-8)

        tfidf_embed = self.tfidf_embedder.encode_word(query)
        tfidf_embed = tfidf_embed / (np.linalg.norm(tfidf_embed) + 1e-8)

        # Combine with same weights as during indexing
        query_combined = np.concatenate([char_embed * 0.3, subword_embed * 0.5, tfidf_embed * 0.2])

        query_combined = query_combined.reshape(1, -1)

        scores, indices = self.combined_index.search(query_combined, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                word = self.idx_to_word[idx]
                results.append((word, float(score)))

        return results

    def _normalize_embeddings(self, embeddings: np.ndarray) -> Any:
        """L2 normalize embeddings for cosine similarity."""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        return embeddings / norms

    def save_index(self) -> None:
        """Save vectorized search index to cache."""
        if not self._is_built:
            return

        # Save FAISS indices
        faiss.write_index(self.char_index, str(self.cache_dir / "char_index.faiss"))
        faiss.write_index(self.subword_index, str(self.cache_dir / "subword_index.faiss"))
        faiss.write_index(self.tfidf_index, str(self.cache_dir / "tfidf_index.faiss"))
        faiss.write_index(self.combined_index, str(self.cache_dir / "combined_index.faiss"))

        # Save embedders and mappings
        cache_data = {
            "char_embedder": self.char_embedder,
            "subword_embedder": self.subword_embedder,
            "tfidf_embedder": self.tfidf_embedder,
            "idx_to_word": self.idx_to_word,
            "word_to_idx": self.word_to_idx,
            "combined_embeddings": self.combined_embeddings,
            "is_built": self._is_built,
        }

        with open(self.cache_dir / "vector_cache.pkl", "wb") as f:
            pickle.dump(cache_data, f)

    def load_index(self) -> bool:
        """Load vectorized search index from cache."""
        try:
            # Load FAISS indices
            self.char_index = faiss.read_index(str(self.cache_dir / "char_index.faiss"))
            self.subword_index = faiss.read_index(str(self.cache_dir / "subword_index.faiss"))
            self.tfidf_index = faiss.read_index(str(self.cache_dir / "tfidf_index.faiss"))
            self.combined_index = faiss.read_index(str(self.cache_dir / "combined_index.faiss"))

            # Load other data
            with open(self.cache_dir / "vector_cache.pkl", "rb") as f:
                cache_data = pickle.load(f)

            self.char_embedder = cache_data["char_embedder"]
            self.subword_embedder = cache_data["subword_embedder"]
            self.tfidf_embedder = cache_data["tfidf_embedder"]
            self.idx_to_word = cache_data["idx_to_word"]
            self.word_to_idx = cache_data["word_to_idx"]
            self.combined_embeddings = cache_data["combined_embeddings"]
            self._is_built = cache_data["is_built"]

            return True

        except Exception as e:
            print(f"Failed to load vector cache: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get vectorized search statistics."""
        stats = {
            "is_built": self._is_built,
            "total_words": len(self.idx_to_word) if self._is_built else 0,
            "char_vocab_size": self.char_embedder.vocab_size,
            "subword_vocab_size": len(self.subword_embedder.subword_vocab),
        }

        if self._is_built and self.combined_embeddings is not None:
            stats.update(
                {
                    "embedding_dim": self.combined_embeddings.shape[1],
                    "char_dim": self.char_embedder.embed_dim,
                    "subword_dim": self.subword_embedder.embed_dim,
                    "tfidf_features": self.tfidf_embedder.max_features,
                }
            )

        return stats
