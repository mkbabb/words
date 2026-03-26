"""BK-tree for adaptive edit-distance fuzzy matching.

A BK-tree (Burkhard-Keller tree) exploits the triangle inequality of edit
distance to prune the search space. For a query word and max edit distance k,
it visits O(n^(k/log(n))) nodes instead of all n.

Uses Damerau-Levenshtein distance (handles transpositions as single edits)
via rapidfuzz's C++ backend for speed.
"""

from __future__ import annotations

import math

from rapidfuzz.distance import DamerauLevenshtein

from ...utils.logging import get_logger
from ..config import (
    BKTREE_CASCADE_MIN_CANDIDATES,
    BKTREE_MAX_RESULTS_CAP,
    BKTREE_TIME_BUDGET_LARGE,
    EDIT_DISTANCE_LENGTH_MULTIPLIER,
    EDIT_DISTANCE_MAX,
    EDIT_DISTANCE_MIN,
)

logger = get_logger(__name__)


class BKTree:
    """BK-tree for adaptive-k edit-distance search.

    Each node stores a word (by vocabulary index) and a dict mapping
    edit-distance values to child subtrees.
    """

    __slots__ = ("word_idx", "word", "children")

    def __init__(self, word_idx: int, word: str) -> None:
        self.word_idx = word_idx
        self.word = word
        self.children: dict[int, BKTree] = {}

    def insert(self, word_idx: int, word: str) -> None:
        """Insert a word into the tree."""
        d = DamerauLevenshtein.distance(self.word, word)
        if d == 0:
            return  # Duplicate word
        if d in self.children:
            self.children[d].insert(word_idx, word)
        else:
            self.children[d] = BKTree(word_idx, word)

    def find(
        self, query: str, max_distance: int, max_results: int = BKTREE_MAX_RESULTS_CAP
    ) -> list[tuple[int, int]]:
        """Find all words within max_distance of query.

        Args:
            query: Query string.
            max_distance: Maximum Damerau-Levenshtein distance.
            max_results: Safety cap on results to prevent runaway at high k.

        Returns:
            List of (word_index, distance) tuples.

        """
        results: list[tuple[int, int]] = []
        self._search(query, max_distance, results, max_results)
        return results

    def _search(
        self,
        query: str,
        max_distance: int,
        results: list[tuple[int, int]],
        max_results: int = BKTREE_MAX_RESULTS_CAP,
    ) -> None:
        """Recursive BK-tree search exploiting triangle inequality."""
        if len(results) >= max_results:
            return

        d = DamerauLevenshtein.distance(self.word, query)
        if d <= max_distance:
            results.append((self.word_idx, d))

        # Triangle inequality: only visit children with distance in [d-k, d+k]
        lo = max(1, d - max_distance)
        hi = d + max_distance
        for child_dist, child_node in self.children.items():
            if lo <= child_dist <= hi:
                if len(results) >= max_results:
                    return
                child_node._search(query, max_distance, results, max_results)

    @classmethod
    def build(cls, vocabulary: list[str]) -> BKTree | None:
        """Build a BK-tree from a vocabulary list.

        Args:
            vocabulary: Sorted, normalized vocabulary list.

        Returns:
            Root BKTree node, or None if vocabulary is empty.

        """
        if not vocabulary:
            return None

        root = cls(0, vocabulary[0])
        for idx in range(1, len(vocabulary)):
            root.insert(idx, vocabulary[idx])

        logger.info(f"Built BK-tree with {len(vocabulary)} words")
        return root


def adaptive_max_distance(query_length: int) -> int:
    """Compute adaptive maximum edit distance based on query length.

    Longer words tolerate more typos:
    - 1-4 chars: k=1-2
    - 5-8 chars: k=2-3
    - 9-14 chars: k=3-4
    - 15+ chars: k=4-5

    Formula: max_k = min(5, max(2, ceil(query_length * 0.35)))
    """
    return min(EDIT_DISTANCE_MAX, max(EDIT_DISTANCE_MIN, math.ceil(query_length * EDIT_DISTANCE_LENGTH_MULTIPLIER)))


def cascading_search(
    tree: BKTree,
    query: str,
    min_candidates: int = BKTREE_CASCADE_MIN_CANDIDATES,
    max_distance: int | None = None,
    max_results: int = BKTREE_MAX_RESULTS_CAP,
    time_budget_ms: float = BKTREE_TIME_BUDGET_LARGE,
) -> list[tuple[int, int]]:
    """Search BK-tree with cascading edit distance and time budget.

    Starts at k=1 and expands to k+1 if fewer than min_candidates found,
    up to the adaptive max_distance for the query length. Stops early if
    the time budget is exceeded (prevents runaway on large, degenerate corpora).

    Args:
        tree: BK-tree root.
        query: Query string.
        min_candidates: Minimum candidates before stopping expansion.
        max_distance: Override for maximum edit distance. If None, uses
            adaptive_max_distance based on query length.
        max_results: Safety cap on results per k level.
        time_budget_ms: Maximum time in milliseconds before aborting expansion.

    Returns:
        List of (word_index, distance) tuples.

    """
    import time

    if max_distance is None:
        max_distance = adaptive_max_distance(len(query))

    start = time.perf_counter()
    best_results: list[tuple[int, int]] = []

    for k in range(1, max_distance + 1):
        results = tree.find(query, k, max_results=max_results)
        if len(results) >= min_candidates:
            return results
        if len(results) > len(best_results):
            best_results = results

        # Time budget check: don't expand k if we've already taken too long
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > time_budget_ms:
            logger.debug(
                f"BK-tree time budget exceeded at k={k}: {elapsed_ms:.1f}ms > {time_budget_ms}ms"
            )
            return best_results

    return best_results


__all__ = ["BKTree", "adaptive_max_distance", "cascading_search"]
