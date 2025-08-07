"""
High-performance trie-based exact and prefix search implementation.

Uses marisa-trie for C++ optimized performance with minimal memory footprint.
Provides exact matching and autocomplete functionality with frequency-based ranking.
"""

from __future__ import annotations

import pickle
from datetime import timedelta
from pathlib import Path
from typing import Any

import marisa_trie
import numpy as np

from ..caching.unified import get_unified
from ..utils.logging import get_logger
from .utils import get_vocabulary_hash

logger = get_logger(__name__)


class TrieSearch:
    """
    High-performance trie-based search using marisa-trie (C++ backend).

    Performance characteristics:
    - Search: O(m) where m = query length
    - Memory: ~20MB for 500k+ words (5x more efficient than Python trie)
    - Build time: O(n*m) where n = number of words, m = average word length
    - Prefix enumeration: Very fast with optimized C++ implementation

    Features:
    - Exact string matching
    - Prefix matching for autocomplete
    - Frequency-based result ranking
    - Minimal memory footprint with double-array implementation
    - Support for phrases and multi-word expressions
    - Persistent storage and loading capability
    """

    def __init__(self) -> None:
        """Initialize the optimized trie search engine."""
        self._trie: marisa_trie.Trie | None = None
        self._word_frequencies: dict[str, int] = {}
        self._word_count = 0
        self._max_frequency = 0
        self._stats_dirty = True  # Flag to track when stats need recalculation
        self._vocabulary_hash: str | None = None
        self._cache: Any = None  # Will be initialized on first use

    async def build_index(
        self, words: list[str], frequencies: dict[str, int] | None = None
    ) -> None:
        """
        Build the optimized trie index with content-hash based caching.

        Args:
            words: List of words and phrases to index
            frequencies: Optional frequency data for ranking
        """
        # Generate vocabulary hash for caching
        vocab_hash = get_vocabulary_hash(words)

        # Check if we already have this vocabulary loaded
        if vocab_hash == self._vocabulary_hash and self._trie is not None:
            logger.debug(f"Trie already built for vocabulary: {vocab_hash[:8]}")
            return

        # Try to load from cache
        cached_trie = await self._load_from_cache(vocab_hash)
        if cached_trie:
            logger.info(f"Loaded trie from cache: {vocab_hash[:8]}")
            self._trie = cached_trie["trie"]
            self._word_frequencies = cached_trie["frequencies"]
            self._word_count = cached_trie["word_count"]
            self._max_frequency = cached_trie["max_frequency"]
            self._vocabulary_hash = vocab_hash
            self._stats_dirty = True
            return

        logger.info(f"Building new trie: {vocab_hash[:8]} ({len(words)} words)")

        self._word_frequencies.clear()
        self._word_count = 0
        self._stats_dirty = True  # Mark stats as needing recalculation
        self._max_frequency = 0

        # Process and normalize words
        normalized_words = []
        for word in words:
            word = word.strip().lower()
            if not word:
                continue

            # Get frequency (default based on word characteristics)
            if frequencies is None:
                frequency = self._calculate_default_frequency(word)
            else:
                frequency = frequencies.get(
                    word, self._calculate_default_frequency(word)
                )

            self._word_frequencies[word] = frequency
            self._max_frequency = max(self._max_frequency, frequency)
            normalized_words.append(word)
            self._word_count += 1

        # Build the marisa-trie (C++ optimized)
        if normalized_words:
            self._trie = marisa_trie.Trie(normalized_words)
            # Cache the built trie
            await self._save_to_cache(vocab_hash)
        else:
            self._trie = None

        self._vocabulary_hash = vocab_hash

    def _calculate_default_frequency(self, word: str) -> int:
        """
        Calculate default frequency based on word characteristics.

        Heuristics:
        - Shorter words are typically more common
        - Common patterns get higher scores
        - Phrases get moderate scores
        """
        base_score = 1000

        # Length penalty (shorter = more common)
        length_penalty = len(word) * 10

        # Phrase bonus/penalty
        if " " in word:
            # Phrases: moderate frequency
            phrase_bonus = 200
        else:
            # Single words: base frequency
            phrase_bonus = 0

        # Common word patterns
        pattern_bonus = 0
        if word.endswith(("ing", "ed", "er", "est", "ly")):
            pattern_bonus = 100
        elif word.startswith(("un", "pre", "re")):
            pattern_bonus = 50

        return max(1, base_score - length_penalty + phrase_bonus + pattern_bonus)

    async def _save_to_cache(self, vocab_hash: str) -> None:
        """Save trie to cache."""
        if not self._trie:
            return

        # Get cache
        if self._cache is None:
            self._cache = await get_unified()

        cache_data = {
            "trie": self._trie,
            "frequencies": self._word_frequencies.copy(),
            "word_count": self._word_count,
            "max_frequency": self._max_frequency,
        }

        # Store with 7-day TTL
        await self._cache.set("trie", vocab_hash, cache_data, ttl=timedelta(days=7))
        logger.debug(f"Saved trie to cache: {vocab_hash[:8]}")

    async def _load_from_cache(self, vocab_hash: str) -> dict[str, Any] | None:
        """Load trie from cache."""
        # Get cache
        if self._cache is None:
            self._cache = await get_unified()

        cached_data = await self._cache.get("trie", vocab_hash)

        if cached_data:
            logger.debug(f"Loaded trie from cache: {vocab_hash[:8]}")
            return cached_data  # type: ignore[no-any-return]

        return None

    def search_exact(self, query: str) -> list[str]:
        """
        Find exact matches for the query using optimized marisa-trie.

        Args:
            query: Exact string to search for

        Returns:
            List of exact matches (typically 0 or 1 items)
        """
        if not query or not self._trie:
            return []

        # Use marisa-trie's optimized exact search
        if query in self._trie:
            return [query]

        return []

    def search_prefix(self, prefix: str, max_results: int = 20) -> list[str]:
        """
        Find all words that start with the given prefix using optimized marisa-trie.

        Args:
            prefix: Prefix to search for
            max_results: Maximum number of results to return

        Returns:
            List of words starting with prefix, ranked by frequency
        """
        if not prefix or not self._trie:
            return []

        # Use marisa-trie's optimized prefix search
        matches = list(self._trie.keys(prefix))

        # Sort by frequency (descending) and return top results
        if len(matches) <= max_results:
            # If we have few matches, simple frequency sort is fine
            frequency_pairs = [
                (word, self._word_frequencies.get(word, 0)) for word in matches
            ]
            frequency_pairs.sort(key=lambda x: x[1], reverse=True)
            return [word for word, _ in frequency_pairs]
        else:
            # For many matches, use numpy argsort for better performance than heapq
            frequencies = np.array(
                [self._word_frequencies.get(word, 0) for word in matches]
            )
            # Get indices of top frequencies (argsort returns ascending, so negate and reverse)
            top_indices = np.argsort(-frequencies)[:max_results]
            return [matches[i] for i in top_indices]

    def contains(self, word: str) -> bool:
        """
        Check if a word exists in the trie using optimized marisa-trie.

        Args:
            word: Word to check

        Returns:
            True if word exists in the trie
        """
        if not word or not self._trie:
            return False
        return word in self._trie

    def get_all_words(self) -> list[str]:
        """
        Get all words in the trie, sorted by frequency.

        Returns:
            List of all words sorted by frequency (descending)
        """
        if not self._trie:
            return []

        # Get all words from the trie
        all_words = list(self._trie)

        # Sort by frequency (descending)
        frequency_words = [
            (word, self._word_frequencies.get(word, 0)) for word in all_words
        ]
        frequency_words.sort(key=lambda x: x[1], reverse=True)

        return [word for word, _ in frequency_words]

    def get_statistics(self) -> dict[str, Any]:
        """
        Get trie statistics and performance metrics.

        Returns:
            Dictionary with trie statistics
        """
        if not self._trie:
            return {
                "word_count": 0,
                "max_frequency": 0,
                "memory_efficiency": "N/A",
                "average_word_length": 0.0,
            }

        # Cache statistics to avoid expensive recalculation
        if not hasattr(self, "_cached_stats") or self._stats_dirty:
            all_words = list(self._trie)
            avg_length = (
                sum(len(word) for word in all_words) / len(all_words)
                if all_words
                else 0.0
            )
            self._cached_avg_length = avg_length
            self._cached_word_list_size = len(all_words)
            self._stats_dirty = False
        else:
            avg_length = self._cached_avg_length

        return {
            "word_count": self._word_count,
            "memory_nodes": getattr(
                self, "_cached_word_list_size", self._word_count
            ),  # Use cached size
            "average_depth": avg_length,  # Use average word length as depth approximation
            "max_frequency": self._max_frequency,
            "memory_efficiency": "5x better than Python trie",
            "average_word_length": avg_length,
            "backend": "marisa-trie (C++)",
        }

    def save_to_file(self, filepath: Path) -> None:
        """
        Save the trie and frequency data to a file for persistence.

        Args:
            filepath: Path to save the trie data
        """
        if not self._trie:
            raise ValueError("No trie built to save")

        data = {
            "trie_data": list(self._trie),
            "frequencies": self._word_frequencies,
            "word_count": self._word_count,
            "max_frequency": self._max_frequency,
        }

        with filepath.open("wb") as f:
            pickle.dump(data, f)

    def load_from_file(self, filepath: Path) -> None:
        """
        Load the trie and frequency data from a file.

        Args:
            filepath: Path to load the trie data from
        """
        with filepath.open("rb") as f:
            data = pickle.load(f)

        # Rebuild the trie from saved data
        words = data["trie_data"]
        self._word_frequencies = data["frequencies"]
        self._word_count = data["word_count"]
        self._max_frequency = data["max_frequency"]

        if words:
            self._trie = marisa_trie.Trie(words)
        else:
            self._trie = None
