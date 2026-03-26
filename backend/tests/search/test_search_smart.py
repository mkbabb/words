"""Smart cascade search -- correctness + performance at multiple corpus scales."""

from __future__ import annotations

import pytest

from floridify.search.constants import SearchMode

from tests.search.conftest import (
    SMART_QUERIES,
    _fmt,
    _label,
    _run_timed_async,
)


@pytest.mark.asyncio
class TestSmartSearch:
    # --- Correctness: exact words found, typos resolved ---

    async def test_smart_finds_exact(self, small_engine):
        results = await small_engine.search_with_mode(
            "apple", mode=SearchMode.SMART, max_results=10
        )
        words = [r.word.lower() for r in results]
        assert "apple" in words

    async def test_smart_finds_typo(self, small_engine):
        results = await small_engine.search_with_mode(
            "elefant", mode=SearchMode.SMART, max_results=10
        )
        words = [r.word.lower() for r in results]
        assert "elephant" in words

    async def test_smart_finds_typo_large(self, large_engine):
        # Use a typo for a word guaranteed in 278K
        for typo, expected in [("elefant", "elephant"), ("aple", "apple"), ("hapy", "happy")]:
            results = await large_engine.search_with_mode(
                typo, mode=SearchMode.SMART, max_results=10
            )
            words = [r.word.lower() for r in results]
            assert expected in words, (
                f"Smart search at 278K: '{expected}' not found for '{typo}'; got {words[:5]}"
            )

    # --- Performance ---

    async def test_smart_perf_small(self, small_engine, small_corpus):
        async def run():
            return [
                await small_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)
                for q in SMART_QUERIES
            ]

        stats, _ = await _run_timed_async(run, iterations=50, warmup=5)
        print(f"\n  SMART  {_label(small_corpus):>5} ({len(SMART_QUERIES)}q): {_fmt(stats)}")

    async def test_smart_perf_medium(self, medium_engine, medium_corpus):
        async def run():
            return [
                await medium_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)
                for q in SMART_QUERIES
            ]

        stats, _ = await _run_timed_async(run, iterations=20, warmup=2)
        print(f"\n  SMART {_label(medium_corpus):>5} ({len(SMART_QUERIES)}q): {_fmt(stats)}")

    async def test_smart_perf_large(self, large_engine, large_corpus):
        async def run():
            return [
                await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)
                for q in SMART_QUERIES
            ]

        stats, _ = await _run_timed_async(run, iterations=15, warmup=2)
        print(f"\n  SMART {_label(large_corpus):>5} ({len(SMART_QUERIES)}q): {_fmt(stats)}")

    async def test_smart_perf_large_cached(self, large_engine, large_corpus):
        for q in SMART_QUERIES:
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)

        async def run():
            return [
                await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)
                for q in SMART_QUERIES
            ]

        stats, _ = await _run_timed_async(run, iterations=15, warmup=0)
        print(f"\n  SMART {_label(large_corpus):>5} cached ({len(SMART_QUERIES)}q): {_fmt(stats)}")
