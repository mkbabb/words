"""Exact search -- correctness + performance at multiple corpus scales."""

from __future__ import annotations

import pytest

from tests.search.conftest import (
    EXACT_QUERIES,
    EXACT_QUERIES_LARGE,
    _fmt,
    _label,
    _run_timed,
)


@pytest.mark.asyncio
class TestExactSearch:
    # --- Correctness: every seed word is found at every scale ---

    @pytest.mark.parametrize("word", EXACT_QUERIES)
    async def test_exact_correctness_small(self, small_engine, word):
        results = small_engine.search_exact(word)
        assert len(results) == 1, f"Expected 1 result for '{word}', got {len(results)}"
        assert results[0].word.lower() == word
        assert results[0].score == 1.0

    @pytest.mark.parametrize("word", EXACT_QUERIES + EXACT_QUERIES_LARGE)
    async def test_exact_correctness_large(self, large_engine, word):
        results = large_engine.search_exact(word)
        assert len(results) == 1, f"Expected 1 result for '{word}', got {len(results)}"
        assert results[0].word.lower() == word

    async def test_exact_miss(self, large_engine):
        results = large_engine.search_exact("xyznonexistent")
        assert results == []

    # --- Performance ---

    async def test_exact_perf_small(self, small_engine, small_corpus):
        stats, _ = _run_timed(
            lambda: [small_engine.search_exact(q) for q in EXACT_QUERIES],
            iterations=500,
            warmup=50,
        )
        print(f"\n  EXACT  {_label(small_corpus):>5} ({len(EXACT_QUERIES)}q): {_fmt(stats)}")
        assert stats["p95_ms"] < 5.0

    async def test_exact_perf_medium(self, medium_engine, medium_corpus):
        stats, _ = _run_timed(
            lambda: [medium_engine.search_exact(q) for q in EXACT_QUERIES],
            iterations=500,
            warmup=50,
        )
        print(f"\n  EXACT {_label(medium_corpus):>5} ({len(EXACT_QUERIES)}q): {_fmt(stats)}")
        assert stats["p95_ms"] < 5.0

    async def test_exact_perf_large(self, large_engine, large_corpus):
        stats, _ = _run_timed(
            lambda: [large_engine.search_exact(q) for q in EXACT_QUERIES],
            iterations=500,
            warmup=50,
        )
        print(f"\n  EXACT {_label(large_corpus):>5} ({len(EXACT_QUERIES)}q): {_fmt(stats)}")
        assert stats["p95_ms"] < 5.0
