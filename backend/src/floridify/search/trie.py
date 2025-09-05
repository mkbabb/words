"""High-performance trie-based exact and prefix search implementation.

Uses marisa-trie for C++ optimized performance with minimal memory footprint.
Provides exact matching and autocomplete functionality with frequency-based ranking.
"""

from __future__ import annotations

import marisa_trie
import numpy as np

from ..corpus.core import Corpus
from ..models.versioned import VersionConfig
from ..text import normalize
from ..utils.logging import get_logger
from .models import TrieIndex

logger = get_logger(__name__)


class TrieSearch:
    """High-performance trie-based search using marisa-trie (C++ backend).

    Performance characteristics:
    - Search: O(m) where m = query length
    - Memory: ~20MB for 500k+ words (5x more efficient than Python trie)
    - Build time: O(n*m) where n = number of words, m = average word length
    - Prefix enumeration: Very fast with optimized C++ implementation
    """

    def __init__(self, index: TrieIndex | None = None) -> None:
        """Initialize the trie search with an optional index.

        Args:
            index: Pre-loaded TrieIndex to use
        """
        # Index data model
        self.index = index

        # Runtime trie (built from index)
        self._trie: marisa_trie.Trie | None = None

        # Load trie from index if provided
        if index:
            self._load_from_index()

    async def initialize(self) -> None:
        """Initialize the trie search (no-op for compatibility)."""
        pass

    async def build_from_corpus(self, corpus: Corpus) -> None:
        """Build the trie index from a corpus.

        Args:
            corpus: Corpus object containing vocabulary
        """
        # Get or create trie index
        self.index = await TrieIndex.get_or_create(
            corpus=corpus,
            config=VersionConfig(),
        )

        # Load the trie from the index
        self._load_from_index()

    def _load_from_index(self) -> None:
        """Load trie from the index model."""
        if not self.index or not self.index.trie_data:
            return

        # Build marisa trie from word list
        self._trie = marisa_trie.Trie(self.index.trie_data)
        logger.debug(f"Loaded trie with {self.index.word_count} words")

    def search_exact(self, query: str) -> str | None:
        """Find exact matches for the query using optimized marisa-trie.

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
            # Return original word with diacritics if available
            if self.index and normalized_query in self.index.normalized_to_original:
                return self.index.normalized_to_original[normalized_query]
            return normalized_query

        return None

    def search_prefix(self, prefix: str, max_results: int = 20) -> list[str]:
        """Find all words that start with the given prefix using optimized marisa-trie.

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

        # Sort by frequency if we have frequency data
        if self.index and self.index.word_frequencies:
            if len(matches) <= max_results:
                # Simple sort for small results
                frequency_pairs = [
                    (word, self.index.word_frequencies.get(word, 0)) for word in matches
                ]
                frequency_pairs.sort(key=lambda x: x[1], reverse=True)
                matches = [word for word, _ in frequency_pairs]
            else:
                # Use numpy for large results
                frequencies = np.array(
                    [self.index.word_frequencies.get(word, 0) for word in matches]
                )
                top_indices = np.argsort(-frequencies)[:max_results]
                matches = [matches[i] for i in top_indices]

        # Return original words with diacritics if available
        if self.index and self.index.normalized_to_original:
            return [
                self.index.normalized_to_original.get(word, word) for word in matches[:max_results]
            ]

        return matches[:max_results]

    @classmethod
    async def from_corpus(
        cls,
        corpus: Corpus,
        config: VersionConfig | None = None,
    ) -> TrieSearch:
        """Create TrieSearch from a corpus.

        Args:
            corpus: Corpus to build trie from
            config: Version configuration

        Returns:
            TrieSearch instance with loaded index
        """
        # Get or create index
        index = await TrieIndex.get_or_create(
            corpus=corpus,
            config=config or VersionConfig(),
        )

        # Create search with index
        return cls(index=index)
