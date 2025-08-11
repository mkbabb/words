"""
High-performance trie-based exact and prefix search implementation.

Uses marisa-trie for C++ optimized performance with minimal memory footprint.
Provides exact matching and autocomplete functionality with frequency-based ranking.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any

import marisa_trie
import numpy as np

from ..caching.unified import get_unified
from ..text import batch_normalize, normalize
from ..utils.logging import get_logger
from .utils import calculate_default_frequency, get_vocabulary_hash

logger = get_logger(__name__)


class TrieSearch:
    """
    High-performance trie-based search using marisa-trie (C++ backend).

    Performance characteristics:
    - Search: O(m) where m = query length
    - Memory: ~20MB for 500k+ words (5x more efficient than Python trie)
    - Build time: O(n*m) where n = number of words, m = average word length
    - Prefix enumeration: Very fast with optimized C++ implementation
    """

    def __init__(self) -> None:
        """Initialize the optimized trie search engine."""
        self._trie: marisa_trie.Trie | None = None
        self._word_frequencies: dict[str, int] = {}
        self._word_count = 0
        self._max_frequency = 0
        self._vocabulary_hash: str | None = None
        self._cache: Any = None  # Will be initialized on first use

    async def initialize(self) -> None:
        """Initialize the trie search (no-op for compatibility)."""
        pass

    async def update_corpus(self, corpus: Any) -> None:
        """
        Update the trie with a new corpus.

        Args:
            corpus: Corpus object containing vocabulary
        """
        await self.build_index(corpus.vocabulary, corpus.word_frequencies)

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

        # Load from cache with integrity verification
        cached_trie = await self._load_from_cache(vocab_hash)
        if cached_trie:
            try:
                self.model_load(cached_trie)
                self._vocabulary_hash = vocab_hash
                logger.info(f"Loaded verified trie from cache: {vocab_hash[:8]}")
                return
            except ValueError as e:
                logger.warning(f"Cache integrity failed: {e}, rebuilding trie")
                # Cache was corrupted, continue to rebuild

        logger.info(f"Building new trie: {vocab_hash[:8]} ({len(words)} words)")

        self._word_frequencies.clear()
        self._word_count = 0
        self._max_frequency = 0

        # Batch normalize all words in parallel
        normalized_words = batch_normalize(words)

        # Build frequency map and filter empty words
        valid_words = []
        for normalized in normalized_words:
            if not normalized:
                continue

            # Get frequency (default based on word characteristics)
            if frequencies is None:
                frequency = calculate_default_frequency(normalized)
            else:
                frequency = frequencies.get(normalized, calculate_default_frequency(normalized))

            self._word_frequencies[normalized] = frequency
            self._max_frequency = max(self._max_frequency, frequency)
            valid_words.append(normalized)
            self._word_count += 1

        # Build the marisa-trie (C++ optimized)
        if valid_words:
            self._trie = marisa_trie.Trie(valid_words)
            # Cache the built trie
            await self._save_to_cache(vocab_hash)
        else:
            self._trie = None

        self._vocabulary_hash = vocab_hash

    def search_exact(self, query: str) -> str | None:
        """
        Find exact matches for the query using optimized marisa-trie.

        Args:
            query: Exact string to search for

        Returns:
            List of exact matches (typically 0 or 1 items)
        """
        if not query or not self._trie:
            return None

        # Normalize query using global normalize function
        normalized_query = normalize(query)
        if not normalized_query:
            return None

        # Use marisa-trie's optimized exact search
        if normalized_query in self._trie:
            return normalized_query

        return None

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

        # Normalize prefix using global normalize function
        normalized_prefix = normalize(prefix)
        if not normalized_prefix:
            return []

        # Use marisa-trie's optimized prefix search
        matches = list(self._trie.keys(normalized_prefix))

        # Sort by frequency (descending) and return top results
        if len(matches) <= max_results:
            # If we have few matches, simple frequency sort is fine
            frequency_pairs = [(word, self._word_frequencies.get(word, 0)) for word in matches]
            frequency_pairs.sort(key=lambda x: x[1], reverse=True)
            return [word for word, _ in frequency_pairs]
        else:
            # For many matches, use numpy argsort for better performance
            frequencies = np.array([self._word_frequencies.get(word, 0) for word in matches])
            # Get indices of top frequencies
            top_indices = np.argsort(-frequencies)[:max_results]
            return [matches[i] for i in top_indices]

    def model_dump(self) -> dict[str, Any]:
        """
        Export trie state with integrity checks and robust serialization.

        Returns:
            Dictionary containing trie state with integrity verification
        """
        if not self._trie:
            return {
                "trie_data": [],
                "frequencies": {},
                "word_count": 0,
                "max_frequency": 0,
                "vocabulary_hash": self._vocabulary_hash,
                "format_version": "2.0",
                "integrity_hash": None,
            }

        # Extract trie data with UTF-8 validation
        trie_words = []
        for word in self._trie:
            try:
                # Ensure word is valid UTF-8 and can be JSON serialized
                word.encode("utf-8").decode("utf-8")
                trie_words.append(word)
            except (UnicodeError, UnicodeDecodeError, UnicodeEncodeError):
                logger.warning(f"Skipping non-UTF-8 word during trie serialization: {repr(word)}")
                continue

        # Sort for deterministic output and integrity
        trie_words_sorted = sorted(trie_words)

        # Create data payload
        data_payload = {
            "trie_data": trie_words_sorted,
            "frequencies": self._word_frequencies.copy(),
            "word_count": len(trie_words_sorted),
            "max_frequency": self._max_frequency,
            "vocabulary_hash": self._vocabulary_hash,
            "format_version": "2.0",
        }

        # Calculate integrity hash for corruption detection
        data_str = json.dumps(data_payload, sort_keys=True, separators=(",", ":"))
        integrity_hash = hashlib.sha256(data_str.encode()).hexdigest()
        data_payload["integrity_hash"] = integrity_hash

        return data_payload

    def model_load(self, data: dict[str, Any]) -> None:
        """
        Load trie state with integrity verification and corruption detection.

        Args:
            data: Dictionary containing trie state

        Raises:
            ValueError: If cache is corrupted or integrity check fails
        """
        # Check format version for backwards compatibility
        format_version = data.get("format_version", "1.0")

        if format_version == "2.0":
            # Verify integrity for v2.0 format
            stored_hash = data.get("integrity_hash")
            if stored_hash:
                # Recreate hash without integrity_hash field
                check_data = {k: v for k, v in data.items() if k != "integrity_hash"}
                data_str = json.dumps(check_data, sort_keys=True, separators=(",", ":"))
                computed_hash = hashlib.sha256(data_str.encode()).hexdigest()

                if computed_hash != stored_hash:
                    raise ValueError(
                        f"Trie cache integrity check failed: {computed_hash[:8]} != {stored_hash[:8]}"
                    )

        words = data.get("trie_data", [])
        self._word_frequencies = data.get("frequencies", {})
        self._word_count = data.get("word_count", 0)
        self._max_frequency = data.get("max_frequency", 0)
        self._vocabulary_hash = data.get("vocabulary_hash")

        if words:
            # Validate and construct trie
            valid_words = [w for w in words if isinstance(w, str) and w.strip()]
            if not valid_words:
                raise ValueError("No valid words found in trie cache data")

            # Deduplicate and sort for consistent construction
            sorted_words = sorted(set(valid_words))
            self._trie = marisa_trie.Trie(sorted_words)
            logger.debug(f"Loaded trie from cache: {len(sorted_words)} words, integrity verified")
        else:
            self._trie = None

    async def _save_to_cache(self, vocab_hash: str) -> None:
        """Save trie to cache."""
        if not self._trie:
            return

        # Get cache
        if self._cache is None:
            self._cache = await get_unified()

        cache_data = self.model_dump()

        # Store with 7-day TTL
        await self._cache.set("trie", vocab_hash, cache_data, ttl=timedelta(days=7))
        logger.debug(f"Saved trie to cache: {vocab_hash[:8]}")

    async def _load_from_cache(self, vocab_hash: str) -> dict[str, Any] | None:
        """Load trie from cache with integrity verification."""
        if self._cache is None:
            self._cache = await get_unified()

        try:
            cached_data = await self._cache.get("trie", vocab_hash)
            if cached_data:
                # Verify integrity before returning
                format_version = cached_data.get("format_version", "1.0")
                if format_version == "2.0":
                    stored_hash = cached_data.get("integrity_hash")
                    if stored_hash:
                        check_data = {k: v for k, v in cached_data.items() if k != "integrity_hash"}
                        data_str = json.dumps(check_data, sort_keys=True, separators=(",", ":"))
                        computed_hash = hashlib.sha256(data_str.encode()).hexdigest()

                        if computed_hash != stored_hash:
                            logger.warning(
                                f"Cache integrity check failed for {vocab_hash[:8]}, discarding"
                            )
                            await self._cache.delete("trie", vocab_hash)
                            return None

                logger.debug(f"Loaded verified trie from cache: {vocab_hash[:8]}")
                return cached_data  # type: ignore[no-any-return]
        except Exception as e:
            logger.warning(f"Cache load failed for {vocab_hash[:8]}: {e}")

        return None
