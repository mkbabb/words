"""Smart cascade search -- correctness + performance at multiple corpus scales.

Tests the _smart_search_cascade including:
- Exact match early exit (skips fuzzy/semantic when word IS in dictionary)
- Typo correction via fuzzy (misspellings found at all corpus scales)
- Pathological query performance (short nonsense, very long words, common prefixes)
- Cascade time budget enforcement
- BK-tree node visit cap effectiveness
"""

from __future__ import annotations

import time

import pytest

from floridify.search.constants import SearchMethod, SearchMode

from tests.search.conftest import (
    SMART_QUERIES,
    _fmt,
    _label,
    _run_timed_async,
)


@pytest.mark.asyncio
class TestSmartSearch:
    # ── Correctness: exact words found, typos resolved ────────────

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

    # ── Exact-match early exit ────────────────────────────────────

    async def test_exact_match_skips_fuzzy(self, large_engine):
        """When query IS a known word, cascade should return fast without fuzzy."""
        # Warm up
        await large_engine.search_with_mode("apple", mode=SearchMode.SMART, max_results=10)

        t0 = time.perf_counter()
        results = await large_engine.search_with_mode(
            "apple", mode=SearchMode.SMART, max_results=10
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        words = [r.word.lower() for r in results]
        assert "apple" in words
        # Exact + prefix only = should be sub-5ms (trie is O(m))
        assert elapsed_ms < 20, f"Exact match took {elapsed_ms:.1f}ms — fuzzy likely leaked through"

    async def test_exact_match_methods_are_exact_or_prefix(self, large_engine):
        """Exact match results should only contain exact/prefix methods, not fuzzy."""
        results = await large_engine.search_with_mode(
            "elephant", mode=SearchMode.SMART, max_results=20
        )
        methods = {r.method for r in results}
        assert SearchMethod.FUZZY not in methods, (
            f"Fuzzy results leaked through exact-match gate: {methods}"
        )
        assert SearchMethod.SEMANTIC not in methods, (
            f"Semantic results leaked through exact-match gate: {methods}"
        )

    # ── Typo correction robustness (fuzzy must fire) ──────────────

    async def test_typo_correction_with_prefix_distractors(self, large_engine):
        """Misspellings that happen to have prefix matches must still find the
        correct word via fuzzy — prefix results alone are insufficient."""
        # "definately" has prefix matches like "definatelyized" (synthetic),
        # but the user meant "definitely"
        for typo, expected in [
            ("computr", "computer"),
            ("algorythm", "algorithm"),
            ("filosofy", "philosophy"),
            ("beautful", "beautiful"),
            ("databse", "database"),
        ]:
            results = await large_engine.search_with_mode(
                typo, mode=SearchMode.SMART, max_results=20
            )
            words = [r.word.lower() for r in results]
            assert expected in words, (
                f"Typo '{typo}' did not find '{expected}'; got {words[:5]}"
            )

    async def test_typo_correction_still_fast(self, large_engine):
        """Fuzzy search for typos at 278K scale must complete within 100ms."""
        typos = ["elefant", "aple", "hapy", "computr", "algorythm"]
        # Warm up
        for t in typos:
            await large_engine.search_with_mode(t, mode=SearchMode.SMART, max_results=10)

        for typo in typos:
            t0 = time.perf_counter()
            await large_engine.search_with_mode(typo, mode=SearchMode.SMART, max_results=10)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert elapsed_ms < 100, (
                f"Typo '{typo}' took {elapsed_ms:.1f}ms — BK-tree may be exploding"
            )

    # ── Pathological queries ──────────────────────────────────────

    async def test_short_nonsense_query_bounded(self, large_engine):
        """Short nonsense queries (no exact/prefix matches) must not explode.
        The BK-tree node visit cap should prevent pathological traversal."""
        # Warm up
        await large_engine.search_with_mode("zyx", mode=SearchMode.SMART, max_results=10)

        for q in ["zyx", "qzw", "jxk"]:
            t0 = time.perf_counter()
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=10)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert elapsed_ms < 100, (
                f"Short nonsense '{q}' took {elapsed_ms:.1f}ms at 278K — "
                f"node visit cap may be too high"
            )

    async def test_long_query_routes_around_bktree(self, large_engine):
        """Queries > BKTREE_MAX_QUERY_LENGTH skip the BK-tree but still run
        trigram + phonetic via FuzzySearch. The cascade doesn't skip fuzzy
        entirely — BK-tree routing is FuzzySearch's internal concern."""
        long_queries = ["perspicaciousness", "antidisestablishment", "supercalifragilistic"]
        # Warm up
        for q in long_queries:
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=10)

        for q in long_queries:
            t0 = time.perf_counter()
            await large_engine.search_with_mode(
                q, mode=SearchMode.SMART, max_results=10
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            # Without BK-tree, trigram+phonetic are fast
            assert elapsed_ms < 50, (
                f"Long query '{q}' ({len(q)} chars) took {elapsed_ms:.1f}ms — "
                f"BK-tree should be routed around for len > 20"
            )

    async def test_common_prefix_performance(self, large_engine):
        """Common prefixes like 'the', 'a', 'san' must stay fast. These have
        enormous prefix result sets but should early-exit via the max_results
        gate before reaching fuzzy."""
        # Use exact-match words — these skip fuzzy via has_exact gate
        exact_words = ["the", "a", "an", "and", "or", "test"]
        # Filter to words actually in the corpus
        for q in exact_words:
            exact_results = large_engine.search_exact(q)
            if not exact_results:
                continue  # skip if not in corpus

            t0 = time.perf_counter()
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert elapsed_ms < 20, (
                f"Common word '{q}' took {elapsed_ms:.1f}ms — "
                f"exact match gate should keep this sub-5ms"
            )

    async def test_common_prefix_no_exact_match(self, large_engine):
        """Short prefixes with many results but no exact match (e.g., 'san',
        'per') must complete within budget even when fuzzy runs."""
        # Pick prefixes that are NOT exact matches but have many prefix results
        prefixes = ["san", "per", "com", "pre", "int"]
        # Warm up
        for q in prefixes:
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)

        for q in prefixes:
            exact = large_engine.search_exact(q)
            if exact:
                continue  # skip — this prefix is also an exact word

            t0 = time.perf_counter()
            results = await large_engine.search_with_mode(
                q, mode=SearchMode.SMART, max_results=20
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            # These have many prefix results → early exit before fuzzy
            assert elapsed_ms < 50, (
                f"Prefix '{q}' took {elapsed_ms:.1f}ms — "
                f"should early-exit when prefix fills max_results"
            )

    # ── Cascade invariants ────────────────────────────────────────

    async def test_exact_match_always_ranked_first(self, large_engine):
        """When the query is an exact match, it must be the top result."""
        for word in ["apple", "elephant", "happy", "computer", "mountain"]:
            exact = large_engine.search_exact(word)
            if not exact:
                continue
            results = await large_engine.search_with_mode(
                word, mode=SearchMode.SMART, max_results=10
            )
            assert results[0].word.lower() == word, (
                f"Exact match '{word}' not ranked first; got '{results[0].word}'"
            )

    async def test_bktree_k1_finds_common_typos_at_278k(self, large_engine):
        """BK-tree with node visit cap must still find single-character typos
        at full 278K scale. This validates the 50K visit cap doesn't prune
        k=1 matches for typical English words."""
        typo_pairs = [
            ("aple", "apple"),
            ("hapy", "happy"),
            ("elefant", "elephant"),
            ("computr", "computer"),
        ]
        for typo, expected in typo_pairs:
            results = await large_engine.search_with_mode(
                typo, mode=SearchMode.SMART, max_results=20
            )
            words = [r.word.lower() for r in results]
            assert expected in words, (
                f"BK-tree missed k=1 correction: '{typo}' → '{expected}' "
                f"not in results {words[:5]}. Node visit cap may be too low."
            )

    # ── Cascade budget enforcement ────────────────────────────────

    async def test_cascade_budget_bounds_total_time(self, large_engine):
        """The 50ms cascade budget must bound total cascade time for any
        query at 278K. This is an end-to-end check, not per-stage."""
        # Mix of query types that stress different stages
        queries = [
            "apple",       # exact match
            "aple",        # typo (fuzzy)
            "persp",       # prefix-heavy
            "zyx",         # nonsense (fuzzy + semantic)
            "the",         # common exact match
            "algorithm",   # exact, long
        ]
        # Warm all queries
        for q in queries:
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)

        for q in queries:
            t0 = time.perf_counter()
            await large_engine.search_with_mode(q, mode=SearchMode.SMART, max_results=20)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            # 100ms ceiling gives 2x headroom over the 50ms budget target
            assert elapsed_ms < 100, (
                f"Cascade for '{q}' took {elapsed_ms:.1f}ms — exceeds 100ms ceiling"
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
