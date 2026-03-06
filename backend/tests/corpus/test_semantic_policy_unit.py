"""Unit tests for corpus semantic policy helpers."""

from __future__ import annotations

from floridify.corpus.semantic_policy import compute_effective_semantic_state


def test_effective_semantic_state_child_to_parent_or() -> None:
    assert compute_effective_semantic_state(None, [False, False]) is False
    assert compute_effective_semantic_state(False, [False, False]) is False
    assert compute_effective_semantic_state(True, [False, False]) is True
    assert compute_effective_semantic_state(False, [True, False]) is True
