"""Fuzzy search -- correctness, quality, and performance at multiple corpus scales."""

from __future__ import annotations

import pytest

from tests.search.conftest import (
    EXACT_QUERIES,
    EXACT_QUERIES_LARGE,
    FUZZY_QUERIES,
    FUZZY_QUERIES_LARGE,
    _fmt,
    _label,
    _run_timed,
)


@pytest.mark.asyncio
class TestFuzzySearch:
    # --- Correctness: known typos resolve to expected words ---

    @pytest.mark.parametrize("typo,expected", FUZZY_QUERIES)
    async def test_typo_resolved_small(self, small_engine, typo, expected):
        results = small_engine.search_fuzzy(typo, max_results=10)
        result_words = [r.word.lower() for r in results]
        assert expected in result_words, (
            f"'{expected}' not found for typo '{typo}' at 10K; got {result_words[:5]}"
        )

    @pytest.mark.parametrize("typo,expected", FUZZY_QUERIES + FUZZY_QUERIES_LARGE)
    async def test_typo_resolved_large(self, large_engine, typo, expected):
        results = large_engine.search_fuzzy(typo, max_results=10)
        result_words = [r.word.lower() for r in results]
        assert expected in result_words, (
            f"'{expected}' not found for typo '{typo}' at 278K; got {result_words[:5]}"
        )

    # --- Quality: exact word is always rank-1 for itself ---

    @pytest.mark.parametrize("word", EXACT_QUERIES[:5])
    async def test_exact_word_is_rank1_small(self, small_engine, word):
        results = small_engine.search_fuzzy(word, max_results=5)
        assert len(results) > 0
        assert results[0].word.lower() == word
        assert results[0].score >= 0.95

    @pytest.mark.parametrize("word", EXACT_QUERIES[:5] + EXACT_QUERIES_LARGE[:3])
    async def test_exact_word_is_rank1_large(self, large_engine, word):
        results = large_engine.search_fuzzy(word, max_results=5)
        assert len(results) > 0, f"No fuzzy results for exact word '{word}'"
        assert results[0].word.lower() == word, (
            f"Expected '{word}' as rank-1, got '{results[0].word.lower()}' "
            f"(score={results[0].score:.3f})"
        )
        assert results[0].score >= 0.95

    # --- Invariant: results sorted descending ---

    async def test_sorted_by_score(self, small_engine):
        results = small_engine.search_fuzzy("apple", max_results=20)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    async def test_sorted_by_score_large(self, large_engine):
        results = large_engine.search_fuzzy("apple", max_results=20)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    # --- Invariant: max_results respected ---

    @pytest.mark.parametrize("cap", [1, 3, 5, 20])
    async def test_max_results_fuzzy(self, small_engine, cap):
        results = small_engine.search_fuzzy("test", max_results=cap)
        assert len(results) <= cap

    # --- Edge: gibberish should not crash ---

    async def test_gibberish_no_crash(self, large_engine):
        results = large_engine.search_fuzzy("zzxqkw", max_results=5)
        assert isinstance(results, list)

    async def test_single_char(self, small_engine):
        results = small_engine.search_fuzzy("a", max_results=5)
        assert isinstance(results, list)

    async def test_very_long_query(self, small_engine):
        results = small_engine.search_fuzzy("a" * 100, max_results=5)
        assert isinstance(results, list)

    # --- Quality: no regressions across scales (score should not collapse) ---

    async def test_quality_stable_across_scales(self, small_engine, large_engine):
        """The top match score for a clear typo shouldn't drop much at larger scale."""
        for typo, expected in FUZZY_QUERIES:
            small_results = small_engine.search_fuzzy(typo, max_results=10)
            large_results = large_engine.search_fuzzy(typo, max_results=10)

            small_top = next((r.score for r in small_results if r.word.lower() == expected), 0)
            large_top = next((r.score for r in large_results if r.word.lower() == expected), 0)

            # Both scales should find the target; allow 20% score drop
            assert large_top >= small_top * 0.80, (
                f"Score collapsed for '{typo}->{expected}': "
                f"{small_top:.3f}@10K vs {large_top:.3f}@278K"
            )

    # --- Performance ---

    async def test_fuzzy_perf_small(self, small_engine, small_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        stats, _ = _run_timed(
            lambda: [small_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=100,
            warmup=10,
        )
        print(f"\n  FUZZY  {_label(small_corpus):>5} ({len(queries)}q): {_fmt(stats)}")

    async def test_fuzzy_perf_medium(self, medium_engine, medium_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        stats, _ = _run_timed(
            lambda: [medium_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=30,
            warmup=3,
        )
        print(f"\n  FUZZY {_label(medium_corpus):>5} ({len(queries)}q): {_fmt(stats)}")

    async def test_fuzzy_perf_large(self, large_engine, large_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        stats, _ = _run_timed(
            lambda: [large_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=20,
            warmup=2,
        )
        print(f"\n  FUZZY {_label(large_corpus):>5} ({len(queries)}q): {_fmt(stats)}")
        # Target: <10ms for 10 queries at 278K (1ms/query)
        assert stats["p95_ms"] < 50.0, f"Fuzzy too slow at 278K: p95={stats['p95_ms']:.1f}ms"

    async def test_fuzzy_perf_large_cached(self, large_engine, large_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        # Warm LRU caches
        for q in queries:
            large_engine.search_fuzzy(q, max_results=20)
        stats, _ = _run_timed(
            lambda: [large_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=20,
            warmup=0,
        )
        print(f"\n  FUZZY {_label(large_corpus):>5} cached ({len(queries)}q): {_fmt(stats)}")
