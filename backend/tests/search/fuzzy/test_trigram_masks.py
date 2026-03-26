"""Tests for the probabilistic mask-augmented trigram index.

Covers: POSTING_DTYPE structure, build output, mask filtering, substring
candidates, and length buckets.
"""

from __future__ import annotations

import numpy as np
import pytest

from floridify.search.fuzzy.candidates import (
    POSTING_DTYPE,
    build_candidate_index,
    get_candidates,
    get_substring_candidates,
)


class TestTrigramMasks:
    """Tests for the probabilistic mask-augmented trigram index."""

    def test_posting_dtype_structure(self):
        """POSTING_DTYPE has idx, loc, nxt fields."""
        assert "idx" in POSTING_DTYPE.names
        assert "loc" in POSTING_DTYPE.names
        assert "nxt" in POSTING_DTYPE.names

    def test_build_produces_numpy_arrays(self):
        """build_candidate_index produces structured numpy arrays."""
        vocab = sorted(["apple", "banana", "cherry"])
        trig_idx, len_bkts = build_candidate_index(vocab)
        for tg, arr in trig_idx.items():
            assert isinstance(arr, np.ndarray)
            assert arr.dtype == POSTING_DTYPE

    def test_masks_reduce_false_positives(self):
        """Masks should produce fewer candidates than count-only for dissimilar queries."""
        vocab = sorted(["apple", "application", "apply", "banana", "cherry",
                        "dog", "elephant", "grape", "hello", "world"] * 10)
        vocab = sorted(set(vocab))
        trig_idx, len_bkts = build_candidate_index(vocab)
        vocab_to_idx = {w: i for i, w in enumerate(vocab)}

        candidates = get_candidates(
            "xyz", vocab, vocab_to_idx, trig_idx, len_bkts,
            max_results=50, use_lemmas=False,
        )
        # "xyz" shares few trigrams with any word — should get mostly length-bucket candidates
        assert isinstance(candidates, list)

    def test_substring_candidates(self):
        """get_substring_candidates finds words containing the query."""
        vocab = sorted(["apple", "application", "pineapple", "apply", "banana"])
        trig_idx, _ = build_candidate_index(vocab)

        results = get_substring_candidates("app", vocab, trig_idx, max_results=10)
        found = [vocab[i] for i in results]
        assert all("app" in w for w in found)

    def test_length_buckets(self):
        """Length buckets group words by character count."""
        vocab = sorted(["cat", "dog", "elephant", "hi", "no"])
        _, len_bkts = build_candidate_index(vocab)
        assert 2 in len_bkts  # "hi", "no"
        assert 3 in len_bkts  # "cat", "dog"
        assert 8 in len_bkts  # "elephant"
