"""Suffix array for O(m log n) substring search over vocabulary.

Builds a sorted suffix array over the concatenated vocabulary with null-byte
sentinels. Binary search finds all words containing a given substring.

Uses pydivsufsort for O(n) construction.
"""

from __future__ import annotations

import bisect

import numpy as np
from pydivsufsort import divsufsort

from ...utils.logging import get_logger

logger = get_logger(__name__)


class SuffixArray:
    """Suffix array for exact substring search over a vocabulary.

    Concatenates all vocabulary words with null-byte sentinels, builds a suffix
    array over the result, and provides O(m log n) substring queries where
    m = query length, n = total text length.
    """

    def __init__(
        self,
        vocabulary: list[str],
    ) -> None:
        """Build suffix array from vocabulary.

        Args:
            vocabulary: List of normalized vocabulary words.

        """
        self._vocabulary = vocabulary
        self._word_count = len(vocabulary)

        if not vocabulary:
            self._text = b""
            self._sa = np.array([], dtype=np.int64)
            self._suffix_to_word: np.ndarray = np.array([], dtype=np.int32)
            return

        # Concatenate words with null-byte sentinels: "word1\0word2\0..."
        self._text = "\0".join(vocabulary).encode("utf-8") + b"\0"

        # Build suffix array in O(n) via libdivsufsort
        # np.frombuffer returns a readonly array; divsufsort needs writable.
        text_arr = np.array(list(self._text), dtype=np.uint8)
        self._sa = divsufsort(text_arr)

        # Build reverse mapping: text position → word index
        # Precompute for O(1) lookups during query
        self._word_starts = self._build_word_starts(vocabulary)
        self._suffix_to_word = self._build_suffix_to_word_map()

        text_kb = len(self._text) / 1024
        sa_kb = self._sa.nbytes / 1024
        map_kb = self._suffix_to_word.nbytes / 1024
        logger.info(
            f"Built suffix array: {self._word_count} words, "
            f"text={text_kb:.0f}KB, SA={sa_kb:.0f}KB, map={map_kb:.0f}KB"
        )

    def _build_word_starts(self, vocabulary: list[str]) -> np.ndarray:
        """Build array of byte offsets where each word starts in the text."""
        starts = np.empty(len(vocabulary), dtype=np.int64)
        offset = 0
        for i, word in enumerate(vocabulary):
            starts[i] = offset
            offset += len(word.encode("utf-8")) + 1  # +1 for null byte
        return starts

    def _build_suffix_to_word_map(self) -> np.ndarray:
        """Map each text position to its vocabulary word index.

        Uses the sorted word_starts for binary search.
        """
        text_len = len(self._text)
        # For each position, find which word it belongs to via bisect
        result = np.empty(text_len, dtype=np.int32)
        starts = self._word_starts

        for pos in range(text_len):
            # bisect_right gives the index of the first start > pos
            word_idx = bisect.bisect_right(starts, pos) - 1
            result[pos] = max(0, word_idx)

        return result

    def search(
        self,
        query: str,
        max_results: int = 50,
    ) -> list[tuple[int, float]]:
        """Find all vocabulary words containing the query as a substring.

        Args:
            query: Substring to search for (must be non-empty).
            max_results: Maximum results to return.

        Returns:
            List of (word_index, coverage_score) tuples, sorted by coverage
            (query_len / word_len) descending.

        """
        if not query or not self._text or len(self._sa) == 0:
            return []

        query_bytes = query.encode("utf-8")
        query_len = len(query_bytes)
        text = self._text
        sa = self._sa
        n = len(sa)

        # Binary search for the leftmost suffix >= query_bytes
        lo, hi = 0, n
        while lo < hi:
            mid = (lo + hi) // 2
            pos = int(sa[mid])
            suffix = text[pos : pos + query_len]
            if suffix < query_bytes:
                lo = mid + 1
            else:
                hi = mid
        left = lo

        # Binary search for the rightmost suffix with prefix == query_bytes
        lo, hi = left, n
        while lo < hi:
            mid = (lo + hi) // 2
            pos = int(sa[mid])
            suffix = text[pos : pos + query_len]
            if suffix <= query_bytes:
                lo = mid + 1
            else:
                hi = mid
        right = lo

        if left >= right:
            return []

        # Collect unique word indices from the matching suffix range
        seen_words: set[int] = set()
        results: list[tuple[int, float]] = []

        for i in range(left, min(right, left + max_results * 10)):
            pos = int(sa[i])
            # Skip if this position is inside a null byte
            if text[pos : pos + 1] == b"\0":
                continue

            word_idx = int(self._suffix_to_word[pos])
            if word_idx in seen_words:
                continue

            # Skip if the match spans a word boundary (contains null byte)
            if b"\0" in text[pos : pos + query_len]:
                continue

            word = self._vocabulary[word_idx]
            # Don't return exact matches (those are handled by exact search)
            if word == query:
                continue

            seen_words.add(word_idx)
            coverage = len(query) / len(word)
            results.append((word_idx, coverage))

            if len(results) >= max_results:
                break

        # Sort by coverage descending (most specific matches first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results


__all__ = ["SuffixArray"]
