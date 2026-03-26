"""Tests for BK-tree edit-distance search.

Covers: exact match, distance-1/2 typos, adaptive max distance, cascading search,
time budget enforcement, max results cap, and edge cases.
"""

from __future__ import annotations

import math
import time

import pytest

from floridify.search.config import (
    BKTREE_CASCADE_MIN_CANDIDATES,
    EDIT_DISTANCE_LENGTH_MULTIPLIER,
    EDIT_DISTANCE_MAX,
    EDIT_DISTANCE_MIN,
)
from floridify.search.fuzzy.bk_tree import BKTree, adaptive_max_distance, cascading_search


class TestBKTree:
    """Tests for BK-tree edit-distance search."""

    def test_exact_match(self, bk_tree: BKTree, multilingual_vocab: list[str]):
        """Distance 0 finds exact matches."""
        results = bk_tree.find("apple", max_distance=0)
        found = [multilingual_vocab[i] for i, _ in results]
        assert "apple" in found

    def test_distance_1(self, bk_tree: BKTree, multilingual_vocab: list[str]):
        """Distance 1 finds single-edit typos."""
        results = bk_tree.find("aple", max_distance=1)
        found = [multilingual_vocab[i] for i, d in results if d <= 1]
        assert "apple" in found

    def test_distance_2(self, bk_tree: BKTree, multilingual_vocab: list[str]):
        """Distance 2 finds double-edit typos."""
        results = bk_tree.find("nessesary", max_distance=2)
        found = [multilingual_vocab[i] for i, d in results if d <= 2]
        assert "necessary" in found

    def test_adaptive_max_distance(self):
        """Adaptive k scales with query length."""
        assert adaptive_max_distance(4) == EDIT_DISTANCE_MIN  # Short → min
        assert adaptive_max_distance(8) == max(EDIT_DISTANCE_MIN, math.ceil(8 * EDIT_DISTANCE_LENGTH_MULTIPLIER))
        assert adaptive_max_distance(15) <= EDIT_DISTANCE_MAX  # Long → capped

    def test_cascading_search_expands(self, bk_tree: BKTree, multilingual_vocab: list[str]):
        """Cascading search expands k until min_candidates met."""
        results = cascading_search(
            bk_tree, "perspicasious",
            min_candidates=BKTREE_CASCADE_MIN_CANDIDATES,
        )
        assert len(results) > 0
        found = [multilingual_vocab[i] for i, _ in results]
        assert "perspicacious" in found

    def test_time_budget_enforcement(self):
        """Time budget prevents runaway on large trees."""
        # Build a large-ish tree
        vocab = [f"word{i:05d}" for i in range(10000)]
        tree = BKTree.build(vocab)
        start = time.perf_counter()
        cascading_search(tree, "xxxxx", min_candidates=10, time_budget_ms=5.0)
        elapsed = (time.perf_counter() - start) * 1000
        # Should respect budget (with some overhead)
        assert elapsed < 50.0  # 10x budget = generous margin

    def test_max_results_cap(self, bk_tree: BKTree):
        """Results capped at max_results."""
        results = bk_tree.find("a", max_distance=5, max_results=3)
        assert len(results) <= 3

    def test_empty_tree(self):
        """Empty vocabulary produces None tree."""
        tree = BKTree.build([])
        assert tree is None

    def test_single_word_tree(self):
        """Single-word tree works correctly."""
        tree = BKTree.build(["hello"])
        results = tree.find("hello", max_distance=0)
        assert len(results) == 1
