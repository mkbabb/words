"""Correctness + performance validation for search pipeline optimizations.

Tests every search method (exact, fuzzy, smart cascade) at four corpus scales:
  - Tiny:   35 words   (minimal / edge cases)
  - Small:  10,000     (fast feedback)
  - Medium: 140,000    (half English)
  - Large:  278,000    (full English)

Tests the following optimizations:
  1. get_candidates() accumulates ALL four stages (no early return)
  2. Fuzzy candidate reduction + length-neighborhood fallback
  3. Semantic vocab embedding O(1) lookup
  4. TrieIndex.create() skips redundant sort
  5. lemma_text_to_index O(1) lemma lookup
  6. _rebuild_indices() clears lemma_text_to_index on rebuild

Run:
    cd backend
    PYTHONPATH=src:$PYTHONPATH pytest tests/search/test_search_optimization.py -v -s
"""

from __future__ import annotations

import random
import statistics
import time

import numpy as np
import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.search.constants import SearchMode
from floridify.search.core import Search
from floridify.search.models import TrieIndex

# ═══════════════════════════════════════════════════════════════════
#  Vocabulary generation (deterministic, shared across all tests)
# ═══════════════════════════════════════════════════════════════════

_SEED_WORDS = [
    "apple", "banana", "cherry", "mountain", "river", "ocean", "forest",
    "happy", "angry", "calm", "excited", "beautiful", "dangerous", "important",
    "run", "walk", "jump", "think", "speak", "write", "understand",
    "elephant", "tiger", "dolphin", "eagle", "butterfly", "penguin",
    "computer", "algorithm", "database", "network", "software", "hardware",
    "democracy", "philosophy", "mathematics", "literature", "psychology",
    "restaurant", "hospital", "university", "government", "environment",
    "perspective", "communication", "responsibility", "extraordinary",
    "acknowledgment", "circumstantial", "discrimination", "comprehensive",
    "perpendicular", "rehabilitation", "superintendent", "transformation",
]

_PREFIXES = ["un", "re", "pre", "mis", "over", "under", "out", "dis", "non", "anti"]
_SUFFIXES = [
    "ing", "tion", "ness", "ment", "able", "ible", "ous", "ive", "ful", "less",
    "ly", "er", "est", "ize", "ify", "al", "ial", "ed", "en", "ity",
]


def _generate_vocabulary(target_size: int) -> list[str]:
    """Deterministic vocabulary at *target_size*."""
    vocab: set[str] = set(_SEED_WORDS)

    for word in list(_SEED_WORDS):
        for pfx in _PREFIXES:
            vocab.add(f"{pfx}{word}")
        for sfx in _SUFFIXES:
            vocab.add(f"{word}{sfx}")
        for pfx in _PREFIXES:
            for sfx in _SUFFIXES:
                vocab.add(f"{pfx}{word}{sfx}")

    rng = random.Random(42)
    families = [
        "lex", "morph", "syn", "sem", "phon", "graph", "prag", "cog",
        "neur", "psych", "soci", "anthro", "bio", "geo", "astro",
    ]
    i = 0
    while len(vocab) < target_size:
        fam = families[i % len(families)]
        length = rng.randint(4, 14)
        consonants, vowels = "bcdfghjklmnpqrstvwxyz", "aeiou"
        w = fam
        for j in range(length - len(fam)):
            w += rng.choice(consonants) if j % 2 == 0 else rng.choice(vowels)
        vocab.add(w)
        i += 1

    return sorted(vocab)[:target_size]


# Pre-generate once at module load (deterministic)
VOCAB_TINY = [
    "apple", "application", "apply", "applied", "applying",
    "banana", "bandana", "balance",
    "definitely", "define", "defined", "definition",
    "cat", "car", "card", "cart", "care",
    "example", "examine", "excellent", "exercise",
    "happy", "happen", "happening", "happiness",
    "orange", "organize", "organic", "origin", "original",
    "test", "testing", "tested", "tester", "testimony",
    "elephant", "elegant", "element", "elevator", "elaborate",
]
VOCAB_SMALL = _generate_vocabulary(10_000)
VOCAB_MEDIUM = _generate_vocabulary(140_000)
VOCAB_LARGE = _generate_vocabulary(278_000)

# Words guaranteed in ALL vocabs (10K through 278K).
# Verified: _generate_vocabulary(10_000) sorts alphabetically and takes first 10K,
# so only words early in the alphabet survive.  These are the safe intersection.
_SAFE_WORDS = sorted(set(_SEED_WORDS) & set(VOCAB_SMALL))

# Queries for every scale — ONLY words guaranteed present at 10K+
EXACT_QUERIES = _SAFE_WORDS[:10]

# Typo→target pairs — target must be in 10K+
FUZZY_QUERIES = [
    ("aple", "apple"),
    ("banna", "banana"),
    ("elefant", "elephant"),
    ("mountan", "mountain"),
    ("hapy", "happy"),
    ("computr", "computer"),
    ("algorythm", "algorithm"),
    ("filosofy", "philosophy"),
    ("beautful", "beautiful"),
    ("databse", "database"),
]
# Filter to only targets in 10K vocab
FUZZY_QUERIES = [(t, e) for t, e in FUZZY_QUERIES if e in set(VOCAB_SMALL)]

# Large-scale only queries (words only in 278K)
EXACT_QUERIES_LARGE = [
    "understand", "river", "run", "walk", "tiger",
    "software", "university", "transformation",
]
FUZZY_QUERIES_LARGE = [
    ("undrstnd", "understand"),
    ("rivr", "river"),
    ("tigr", "tiger"),
    ("softwre", "software"),
]

SMART_QUERIES = [w for w in ["apple", "happy", "banana", "elephant", "mountain",
                              "algorithm", "beautiful", "database", "computer", "philosophy"]
                 if w in set(VOCAB_SMALL)][:10]


# ═══════════════════════════════════════════════════════════════════
#  Corpus + engine fixtures  (function-scoped → clean per test)
# ═══════════════════════════════════════════════════════════════════

async def _make_corpus(test_db, name: str, vocab: list[str]) -> Corpus:
    corpus = await Corpus.create(
        corpus_name=name,
        vocabulary=vocab,
        language=Language.ENGLISH,
    )
    corpus.corpus_type = CorpusType.LANGUAGE
    manager = TreeCorpusManager()
    return await manager.save_corpus(corpus)


async def _make_engine(corpus: Corpus) -> Search:
    engine = Search()
    engine.corpus = corpus
    await engine.build_indices()
    return engine


@pytest_asyncio.fixture
async def tiny_corpus(test_db) -> Corpus:
    return await _make_corpus(test_db, "opt_tiny", VOCAB_TINY)


@pytest_asyncio.fixture
async def small_corpus(test_db) -> Corpus:
    return await _make_corpus(test_db, "opt_10k", VOCAB_SMALL)


@pytest_asyncio.fixture
async def medium_corpus(test_db) -> Corpus:
    return await _make_corpus(test_db, "opt_140k", VOCAB_MEDIUM)


@pytest_asyncio.fixture
async def large_corpus(test_db) -> Corpus:
    return await _make_corpus(test_db, "opt_278k", VOCAB_LARGE)


@pytest_asyncio.fixture
async def tiny_engine(tiny_corpus) -> Search:
    return await _make_engine(tiny_corpus)


@pytest_asyncio.fixture
async def small_engine(small_corpus) -> Search:
    return await _make_engine(small_corpus)


@pytest_asyncio.fixture
async def medium_engine(medium_corpus) -> Search:
    return await _make_engine(medium_corpus)


@pytest_asyncio.fixture
async def large_engine(large_corpus) -> Search:
    return await _make_engine(large_corpus)


# ═══════════════════════════════════════════════════════════════════
#  Timing helpers
# ═══════════════════════════════════════════════════════════════════

def _run_timed(fn, iterations=50, warmup=5):
    for _ in range(warmup):
        fn()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }, result


async def _run_timed_async(fn, iterations=30, warmup=3):
    for _ in range(warmup):
        await fn()
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = await fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "p95_ms": sorted(times)[int(len(times) * 0.95)],
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
    }, result


def _fmt(stats: dict) -> str:
    return (
        f"mean={stats['mean_ms']:8.3f}ms  median={stats['median_ms']:8.3f}ms  "
        f"min={stats['min_ms']:8.3f}ms  p95={stats['p95_ms']:8.3f}ms"
    )


def _label(corpus: Corpus) -> str:
    return f"{len(corpus.vocabulary) // 1000}K" if len(corpus.vocabulary) >= 1000 else str(len(corpus.vocabulary))


# ═══════════════════════════════════════════════════════════════════
#  1. get_candidates() correctness — every scale
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestGetCandidates:
    """Verify get_candidates() collects from ALL four stages at every corpus size."""

    # --- Invariant: length buckets always contribute ---

    async def test_length_buckets_always_present_tiny(self, tiny_corpus):
        cands = tiny_corpus.get_candidates("aple", max_results=100)
        words = set(tiny_corpus.get_words_by_indices(cands))
        assert len(cands) > 0
        assert any(3 <= len(w) <= 6 for w in words), f"No similar-length words: {words}"

    async def test_length_buckets_always_present_large(self, large_corpus):
        cands = large_corpus.get_candidates("aple", max_results=300)
        words = set(large_corpus.get_words_by_indices(cands))
        assert len(cands) > 0
        assert any(3 <= len(w) <= 6 for w in words)

    # --- Invariant: direct matches always included ---

    @pytest.mark.parametrize("word", EXACT_QUERIES[:5])
    async def test_direct_match_in_candidates_small(self, small_corpus, word):
        cands = small_corpus.get_candidates(word, max_results=50)
        words = set(small_corpus.get_words_by_indices(cands))
        assert word in words, f"Direct match '{word}' missing from candidates"

    @pytest.mark.parametrize("word", EXACT_QUERIES[:5] + EXACT_QUERIES_LARGE[:3])
    async def test_direct_match_in_candidates_large(self, large_corpus, word):
        cands = large_corpus.get_candidates(word, max_results=50)
        words = set(large_corpus.get_words_by_indices(cands))
        assert word in words, (
            f"Direct match '{word}' evicted from candidates at 278K "
            f"(got {len(cands)} candidates, sample: {list(words)[:5]})"
        )

    # --- Invariant: max_results cap is respected ---

    @pytest.mark.parametrize("cap", [1, 5, 20, 50])
    async def test_max_results_cap_small(self, small_corpus, cap):
        cands = small_corpus.get_candidates("test", max_results=cap)
        assert len(cands) <= cap

    @pytest.mark.parametrize("cap", [1, 5, 20, 50])
    async def test_max_results_cap_large(self, large_corpus, cap):
        cands = large_corpus.get_candidates("test", max_results=cap)
        assert len(cands) <= cap

    # --- Invariant: empty / whitespace queries return empty ---

    async def test_empty_query(self, tiny_corpus):
        assert tiny_corpus.get_candidates("") == []
        assert tiny_corpus.get_candidates("   ") == []

    # --- Invariant: no empty candidates for ANY seed word at any scale ---

    @pytest.mark.parametrize("word", _SEED_WORDS[:20])
    async def test_never_empty_for_seed_words_small(self, small_corpus, word):
        cands = small_corpus.get_candidates(word, max_results=50)
        assert len(cands) > 0, f"Empty candidates for seed word '{word}' at 10K"

    @pytest.mark.parametrize("word", _SEED_WORDS[:10])
    async def test_never_empty_for_seed_words_large(self, large_corpus, word):
        cands = large_corpus.get_candidates(word, max_results=50)
        assert len(cands) > 0, f"Empty candidates for seed word '{word}' at 278K"

    # --- Regression: typo queries should also get candidates ---

    async def test_typo_candidates_at_every_scale(self, small_corpus, large_corpus):
        for typo, _ in FUZZY_QUERIES[:5]:
            for corpus in [small_corpus, large_corpus]:
                cands = corpus.get_candidates(typo, max_results=50)
                assert len(cands) > 0, (
                    f"Empty candidates for typo '{typo}' at {_label(corpus)}"
                )


# ═══════════════════════════════════════════════════════════════════
#  2. lemma_text_to_index integrity
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestLemmaIndex:
    """Verify lemma_text_to_index is populated, consistent, and survives rebuilds."""

    async def test_populated_after_create(self, tiny_corpus):
        assert len(tiny_corpus.lemma_text_to_index) > 0
        assert len(tiny_corpus.lemma_text_to_index) == len(tiny_corpus.lemmatized_vocabulary)

    async def test_consistent_with_lemmatized_vocabulary(self, small_corpus):
        for lemma, idx in small_corpus.lemma_text_to_index.items():
            assert small_corpus.lemmatized_vocabulary[idx] == lemma

    async def test_survives_add_words(self, test_db):
        corpus = await _make_corpus(test_db, "lemma_add", VOCAB_TINY[:20])
        old_size = len(corpus.lemma_text_to_index)
        await corpus.add_words(["xylophone", "zebra", "quixotic"])
        # lemma_text_to_index should be rebuilt (not stale)
        assert len(corpus.lemma_text_to_index) >= old_size
        for lemma, idx in corpus.lemma_text_to_index.items():
            assert corpus.lemmatized_vocabulary[idx] == lemma

    async def test_survives_rebuild_indices(self, test_db):
        corpus = await _make_corpus(test_db, "lemma_rebuild", VOCAB_TINY[:20])
        await corpus._rebuild_indices()
        assert len(corpus.lemma_text_to_index) > 0
        for lemma, idx in corpus.lemma_text_to_index.items():
            assert corpus.lemmatized_vocabulary[idx] == lemma

    async def test_bidirectional_consistency(self, small_corpus):
        """lemma_text_to_index[text] == idx  ↔  lemmatized_vocabulary[idx] == text"""
        for idx, lemma in enumerate(small_corpus.lemmatized_vocabulary):
            assert small_corpus.lemma_text_to_index[lemma] == idx


# ═══════════════════════════════════════════════════════════════════
#  3. Exact search — correctness + performance
# ═══════════════════════════════════════════════════════════════════

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
            iterations=500, warmup=50,
        )
        print(f"\n  EXACT  {_label(small_corpus):>5} ({len(EXACT_QUERIES)}q): {_fmt(stats)}")
        assert stats["p95_ms"] < 5.0

    async def test_exact_perf_medium(self, medium_engine, medium_corpus):
        stats, _ = _run_timed(
            lambda: [medium_engine.search_exact(q) for q in EXACT_QUERIES],
            iterations=500, warmup=50,
        )
        print(f"\n  EXACT {_label(medium_corpus):>5} ({len(EXACT_QUERIES)}q): {_fmt(stats)}")
        assert stats["p95_ms"] < 5.0

    async def test_exact_perf_large(self, large_engine, large_corpus):
        stats, _ = _run_timed(
            lambda: [large_engine.search_exact(q) for q in EXACT_QUERIES],
            iterations=500, warmup=50,
        )
        print(f"\n  EXACT {_label(large_corpus):>5} ({len(EXACT_QUERIES)}q): {_fmt(stats)}")
        assert stats["p95_ms"] < 5.0


# ═══════════════════════════════════════════════════════════════════
#  4. Fuzzy search — correctness + quality + performance
# ═══════════════════════════════════════════════════════════════════

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
                f"Score collapsed for '{typo}→{expected}': "
                f"{small_top:.3f}@10K vs {large_top:.3f}@278K"
            )

    # --- Performance ---

    async def test_fuzzy_perf_small(self, small_engine, small_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        stats, _ = _run_timed(
            lambda: [small_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=100, warmup=10,
        )
        print(f"\n  FUZZY  {_label(small_corpus):>5} ({len(queries)}q): {_fmt(stats)}")

    async def test_fuzzy_perf_medium(self, medium_engine, medium_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        stats, _ = _run_timed(
            lambda: [medium_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=30, warmup=3,
        )
        print(f"\n  FUZZY {_label(medium_corpus):>5} ({len(queries)}q): {_fmt(stats)}")

    async def test_fuzzy_perf_large(self, large_engine, large_corpus):
        queries = [t for t, _ in FUZZY_QUERIES]
        stats, _ = _run_timed(
            lambda: [large_engine.search_fuzzy(q, max_results=20) for q in queries],
            iterations=20, warmup=2,
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
            iterations=20, warmup=0,
        )
        print(f"\n  FUZZY {_label(large_corpus):>5} cached ({len(queries)}q): {_fmt(stats)}")


# ═══════════════════════════════════════════════════════════════════
#  5. Smart cascade — correctness + performance
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestSmartSearch:

    # --- Correctness: exact words found, typos resolved ---

    async def test_smart_finds_exact(self, small_engine):
        results = await small_engine.search_with_mode("apple", mode=SearchMode.SMART, max_results=10)
        words = [r.word.lower() for r in results]
        assert "apple" in words

    async def test_smart_finds_typo(self, small_engine):
        results = await small_engine.search_with_mode("elefant", mode=SearchMode.SMART, max_results=10)
        words = [r.word.lower() for r in results]
        assert "elephant" in words

    async def test_smart_finds_typo_large(self, large_engine):
        # Use a typo for a word guaranteed in 278K
        for typo, expected in [("elefant", "elephant"), ("aple", "apple"), ("hapy", "happy")]:
            results = await large_engine.search_with_mode(typo, mode=SearchMode.SMART, max_results=10)
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


# ═══════════════════════════════════════════════════════════════════
#  6. Semantic vocab embedding lookup
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestSemanticVocabLookup:
    """Verify the vocabulary embedding lookup optimization."""

    async def test_in_vocab_returns_embedding(self, test_db):
        from floridify.search.semantic.core import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat", "apple", "banana"]
        corpus = await _make_corpus(test_db, "sem_invocab", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb = search._lookup_vocab_embedding("happy")
        assert emb is not None, "In-vocab 'happy' should return embedding"
        assert isinstance(emb, np.ndarray)
        assert emb.shape[0] > 0

    async def test_case_insensitive_lookup(self, test_db):
        from floridify.search.semantic.core import SemanticSearch

        vocab = ["happy", "sad", "dog"]
        corpus = await _make_corpus(test_db, "sem_case", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        # "Happy" (capitalized) should still hit the fast path
        emb = search._lookup_vocab_embedding("Happy")
        assert emb is not None, "Case-insensitive lookup failed for 'Happy'"

    async def test_oov_returns_none(self, test_db):
        from floridify.search.semantic.core import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat"]
        corpus = await _make_corpus(test_db, "sem_oov", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        assert search._lookup_vocab_embedding("xylophone") is None

    async def test_correct_shape(self, test_db):
        from floridify.search.semantic.core import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat"]
        corpus = await _make_corpus(test_db, "sem_shape", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb = search._lookup_vocab_embedding("dog")
        if emb is not None and search.sentence_embeddings is not None:
            assert emb.shape == (search.sentence_embeddings.shape[1],)

    async def test_no_corpus_returns_none(self):
        from floridify.search.semantic.core import SemanticSearch

        search = SemanticSearch()
        assert search._lookup_vocab_embedding("anything") is None

    async def test_embeddings_differ_for_different_words(self, test_db):
        """Distinct words should have distinct pre-computed embeddings."""
        from floridify.search.semantic.core import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat", "mountain", "river"]
        corpus = await _make_corpus(test_db, "sem_distinct", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb_happy = search._lookup_vocab_embedding("happy")
        emb_dog = search._lookup_vocab_embedding("dog")
        assert emb_happy is not None and emb_dog is not None
        # Cosine distance should be non-trivial
        cos_sim = float(np.dot(emb_happy, emb_dog) / (np.linalg.norm(emb_happy) * np.linalg.norm(emb_dog)))
        assert cos_sim < 0.99, f"'happy' and 'dog' embeddings too similar: {cos_sim:.4f}"


# ═══════════════════════════════════════════════════════════════════
#  7. TrieIndex sort optimization
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestTrieIndexSort:

    async def test_trie_data_matches_vocabulary(self, tiny_corpus):
        trie_index = await TrieIndex.create(tiny_corpus)
        assert trie_index.trie_data == list(tiny_corpus.vocabulary)

    async def test_trie_data_is_sorted(self, small_corpus):
        trie_index = await TrieIndex.create(small_corpus)
        assert trie_index.trie_data == sorted(trie_index.trie_data)


# ═══════════════════════════════════════════════════════════════════
#  8. Index build performance
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestIndexBuild:

    async def test_build_small(self, small_corpus, test_db):
        async def build():
            engine = Search()
            engine.corpus = small_corpus
            await engine.build_indices()
            return engine
        stats, _ = await _run_timed_async(build, iterations=10, warmup=1)
        print(f"\n  BUILD  {_label(small_corpus):>5}: {_fmt(stats)}")

    async def test_build_medium(self, medium_corpus, test_db):
        async def build():
            engine = Search()
            engine.corpus = medium_corpus
            await engine.build_indices()
            return engine
        stats, _ = await _run_timed_async(build, iterations=5, warmup=1)
        print(f"\n  BUILD {_label(medium_corpus):>5}: {_fmt(stats)}")

    async def test_build_large(self, large_corpus, test_db):
        async def build():
            engine = Search()
            engine.corpus = large_corpus
            await engine.build_indices()
            return engine
        stats, _ = await _run_timed_async(build, iterations=3, warmup=1)
        print(f"\n  BUILD {_label(large_corpus):>5}: {_fmt(stats)}")


# ═══════════════════════════════════════════════════════════════════
#  9. Semantic search — cached performance (small corpus only)
# ═══════════════════════════════════════════════════════════════════

SEMANTIC_QUERIES = ["fruit", "animal", "emotion", "technology", "nature"]


@pytest.mark.asyncio
class TestSemanticSearchPerf:

    async def test_semantic_uncached_small(self, small_corpus, test_db):
        from floridify.search.semantic.core import SemanticSearch

        engine = Search()
        engine.corpus = small_corpus
        await engine.build_indices()

        semantic = await SemanticSearch.from_corpus(corpus=small_corpus)
        await semantic.initialize()
        engine.semantic_search = semantic
        engine._semantic_ready = True

        # Warm model, clear cache
        await engine.search_semantic("warmup", max_results=10)
        semantic.result_cache.clear()
        semantic.result_cache_order.clear()

        async def run():
            results = []
            for q in SEMANTIC_QUERIES:
                unique_q = f"{q}_{time.perf_counter_ns()}"
                r = await engine.search_semantic(unique_q, max_results=10)
                results.extend(r)
            return results

        stats, _ = await _run_timed_async(run, iterations=10, warmup=2)
        print(f"\n  SEMANTIC uncached {_label(small_corpus):>5} ({len(SEMANTIC_QUERIES)}q): {_fmt(stats)}")

    async def test_semantic_cached_small(self, small_corpus, test_db):
        from floridify.search.semantic.core import SemanticSearch

        engine = Search()
        engine.corpus = small_corpus
        await engine.build_indices()

        semantic = await SemanticSearch.from_corpus(corpus=small_corpus)
        await semantic.initialize()
        engine.semantic_search = semantic
        engine._semantic_ready = True

        # Populate cache
        for q in SEMANTIC_QUERIES:
            await engine.search_semantic(q, max_results=10)

        async def run():
            return [await engine.search_semantic(q, max_results=10) for q in SEMANTIC_QUERIES]

        stats, _ = await _run_timed_async(run, iterations=50, warmup=5)
        print(f"\n  SEMANTIC cached   {_label(small_corpus):>5} ({len(SEMANTIC_QUERIES)}q): {_fmt(stats)}")
