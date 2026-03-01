#!/usr/bin/env python3
"""Validate fuzzy search quality and correctness.

Tests typo correction, prefix matching, false positive rejection, and ranking quality
using a realistic English vocabulary corpus. Runs standalone without MongoDB.

Usage:
    cd backend
    .venv/bin/python scripts/validate_search_quality.py
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# The FuzzySearch pipeline depends on Corpus.get_candidates() for candidate
# pre-selection and then runs RapidFuzz scorers on the candidate vocabulary.
# We build a real Corpus in-memory (no MongoDB) and invoke FuzzySearch.search()
# directly so we exercise the *exact* production code path:
#   Corpus.get_candidates → RapidFuzz WRatio + token_set_ratio → apply_length_correction
# ---------------------------------------------------------------------------

from floridify.corpus.core import Corpus, CorpusType
from floridify.models.base import Language
from floridify.search.constants import DEFAULT_MIN_SCORE, SearchMethod
from floridify.search.fuzzy import FuzzySearch
from floridify.search.utils import apply_length_correction


# ── Realistic English vocabulary ──────────────────────────────────────────
# ~200 common English words spanning multiple domains, lengths, and patterns.
# This is large enough to stress candidate selection and false-positive filtering.

VOCABULARY = sorted(
    set(
        [
            # Fruits
            "apple",
            "apples",
            "banana",
            "bananas",
            "orange",
            "oranges",
            "grape",
            "grapes",
            "cherry",
            "cherries",
            "peach",
            "peaches",
            "plum",
            "plums",
            "strawberry",
            "watermelon",
            "blueberry",
            "raspberry",
            "pineapple",
            "mango",
            "kiwi",
            "lemon",
            "lime",
            # Animals
            "dog",
            "cat",
            "elephant",
            "tiger",
            "lion",
            "horse",
            "rabbit",
            "mouse",
            "fish",
            "bird",
            "bear",
            "deer",
            "wolf",
            "fox",
            "snake",
            "whale",
            "dolphin",
            "penguin",
            "eagle",
            "hawk",
            # Common English words
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "may",
            "new",
            "now",
            "old",
            "see",
            "way",
            "who",
            "did",
            "let",
            "say",
            "she",
            "too",
            "use",
            # Longer common words
            "about",
            "after",
            "again",
            "house",
            "place",
            "world",
            "think",
            "where",
            "which",
            "their",
            "there",
            "these",
            "other",
            "would",
            "could",
            "right",
            "under",
            "still",
            "never",
            "every",
            "music",
            "water",
            "money",
            # Words specifically needed for test cases
            "ample",
            "maple",
            "computer",
            "comprehensive",
            "complete",
            "company",
            "compare",
            "compact",
            "compose",
            "concept",
            "philosophy",
            "photograph",
            "telephone",
            "definitely",
            "beautiful",
            "beginning",
            "experience",
            "government",
            "important",
            "information",
            "different",
            "education",
            "knowledge",
            "something",
            "understand",
            "necessary",
            "particular",
            "restaurant",
            "technology",
            "environment",
            "development",
            # Words with common misspelling targets
            "accommodate",
            "occurrence",
            "recommend",
            "separate",
            "surprise",
            "tomorrow",
            "Wednesday",
            "February",
            "calendar",
            "library",
            # Additional padding for realism
            "running",
            "walking",
            "jumping",
            "swimming",
            "reading",
            "writing",
            "playing",
            "working",
            "helping",
            "making",
            "taking",
            "coming",
            "going",
            "looking",
            "finding",
            "system",
            "program",
            "process",
            "number",
            "people",
            "family",
            "school",
            "friend",
            "health",
            "garden",
            "market",
            "travel",
            "energy",
            "design",
            "change",
            "simple",
            "single",
            "double",
            "triple",
        ]
    )
)


# ── Test infrastructure ───────────────────────────────────────────────────


@dataclass
class TestResult:
    name: str
    query: str
    passed: bool
    top_results: list[tuple[str, float]]  # (word, score)
    reason: str = ""


@dataclass
class TestSuite:
    name: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)


def format_results(results: list[tuple[str, float]], max_show: int = 5) -> str:
    """Format search results for display."""
    if not results:
        return "  (no results)"
    lines = []
    for i, (word, score) in enumerate(results[:max_show]):
        lines.append(f"  {i + 1}. {word:25s} score={score:.4f}")
    if len(results) > max_show:
        lines.append(f"  ... and {len(results) - max_show} more")
    return "\n".join(lines)


def print_test_result(result: TestResult) -> None:
    """Print a single test result."""
    status = "PASS" if result.passed else "FAIL"
    icon = "[+]" if result.passed else "[-]"
    print(f"\n{icon} {status}: {result.name}")
    print(f"    Query: '{result.query}'")
    if result.reason:
        print(f"    Reason: {result.reason}")
    print(format_results(result.top_results))


# ── Build corpus and search engine ────────────────────────────────────────


def build_corpus_sync(vocabulary: list[str]) -> Corpus:
    """Build a Corpus in-memory without any async / MongoDB calls.

    We manually replicate the essential steps of Corpus.create() that the
    FuzzySearch pipeline needs:
      - vocabulary, vocabulary_to_index
      - signature_buckets, length_buckets  (for get_candidates)
      - original_vocabulary, normalized_to_original_indices
    """
    from floridify.text.normalize import batch_normalize, get_word_signature

    # Normalize
    normalized = batch_normalize(vocabulary)
    unique_normalized = sorted(set(normalized))

    vocabulary_to_index = {w: i for i, w in enumerate(unique_normalized)}

    # Build normalized_to_original_indices
    normalized_to_original_indices: dict[int, list[int]] = {}
    for orig_idx, norm_word in enumerate(normalized):
        if norm_word in vocabulary_to_index:
            sorted_idx = vocabulary_to_index[norm_word]
            normalized_to_original_indices.setdefault(sorted_idx, []).append(orig_idx)

    corpus = Corpus(
        corpus_name="validation_corpus",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=unique_normalized,
        original_vocabulary=vocabulary,
        normalized_to_original_indices=normalized_to_original_indices,
        vocabulary_to_index=vocabulary_to_index,
    )

    # Build signature + length buckets (needed by get_candidates)
    corpus.signature_buckets = {}
    corpus.length_buckets = {}
    for idx, word in enumerate(unique_normalized):
        sig = get_word_signature(word)
        corpus.signature_buckets.setdefault(sig, []).append(idx)
        length = len(word)
        corpus.length_buckets.setdefault(length, []).append(idx)

    # Sort buckets
    for bucket in corpus.signature_buckets.values():
        bucket.sort()
    for bucket in corpus.length_buckets.values():
        bucket.sort()

    return corpus


def run_fuzzy_search(
    fuzzy: FuzzySearch,
    corpus: Corpus,
    query: str,
    max_results: int = 10,
    min_score: float | None = None,
) -> list[tuple[str, float]]:
    """Run fuzzy search and return (word, score) pairs."""
    results = fuzzy.search(query, corpus, max_results=max_results, min_score=min_score)
    return [(r.word, r.score) for r in results]


# ── Test categories ───────────────────────────────────────────────────────


def test_typo_correction(fuzzy: FuzzySearch, corpus: Corpus) -> TestSuite:
    """Test that common typos are corrected to the right word."""
    suite = TestSuite(name="Typo Correction")

    cases = [
        # (test_name, query, expected_word, description)
        ("deletion", "aple", "apple", "missing letter 'p'"),
        ("insertion", "appple", "apple", "extra letter 'p'"),
        ("transposition", "aplpe", "apple", "swapped 'l' and 'p'"),
        ("truncation", "banan", "banana", "missing final 'a'"),
        ("phonetic", "elefant", "elephant", "phonetic misspelling"),
        ("common_misspelling", "definately", "definitely", "common misspelling"),
        ("double_letter_error", "occurence", "occurrence", "missing 'r'"),
        ("vowel_swap", "seperate", "separate", "common a/e confusion"),
    ]

    for test_name, query, expected_word, description in cases:
        results = run_fuzzy_search(fuzzy, corpus, query, max_results=5)
        top_words = [w for w, _ in results]

        if not results:
            suite.results.append(
                TestResult(
                    name=f"Typo/{test_name}: '{query}' -> '{expected_word}' ({description})",
                    query=query,
                    passed=False,
                    top_results=[],
                    reason="No results returned",
                )
            )
            continue

        # The expected word should appear in the top 3 results
        found_in_top3 = expected_word in top_words[:3]

        suite.results.append(
            TestResult(
                name=f"Typo/{test_name}: '{query}' -> '{expected_word}' ({description})",
                query=query,
                passed=found_in_top3,
                top_results=results[:5],
                reason="" if found_in_top3 else f"'{expected_word}' not in top 3: {top_words[:3]}",
            )
        )

    return suite


def test_prefix_matching(fuzzy: FuzzySearch, corpus: Corpus) -> TestSuite:
    """Test prefix-like queries through fuzzy search.

    ARCHITECTURE NOTE: True prefix matching is handled by TrieSearch.search_prefix()
    in production. The smart search cascade is: exact (trie) -> fuzzy -> semantic.
    Fuzzy search uses RapidFuzz WRatio which is not designed for prefix matching --
    short prefixes against much longer words produce low WRatio scores because
    the length ratio dominates. Additionally, the candidate selection (signature
    + length buckets) often excludes words whose length differs by more than 2.

    This suite validates:
    1. Fuzzy CAN handle prefix-like queries when query/target lengths are close
    2. Fuzzy correctly CANNOT handle short-prefix-to-long-word (documented gap)
    """
    suite = TestSuite(name="Prefix Matching (fuzzy)")

    # -- Test 1: Close-length prefix (should work) --
    results = run_fuzzy_search(fuzzy, corpus, "comput", max_results=10)
    top_words = [w for w, _ in results]
    found_computer = "computer" in top_words[:3]

    suite.results.append(
        TestResult(
            name="Prefix/close_length: 'comput' -> 'computer' (6 vs 8 chars)",
            query="comput",
            passed=found_computer,
            top_results=results[:5],
            reason="" if found_computer else f"'computer' not in top 3: {top_words[:3]}",
        )
    )

    # -- Test 2: Truncation that is NOT a prefix problem --
    # "banan" -> "banana" is truncation (5 vs 6 chars), should work via fuzzy
    results_banan = run_fuzzy_search(fuzzy, corpus, "banan", max_results=5)
    found_banana = len(results_banan) > 0 and results_banan[0][0] == "banana"

    suite.results.append(
        TestResult(
            name="Prefix/near_length: 'banan' -> 'banana' (5 vs 6 chars)",
            query="banan",
            passed=found_banana,
            top_results=results_banan[:5],
            reason="" if found_banana else f"Top result is not 'banana'",
        )
    )

    # -- Test 3: Known limitation -- short prefix vs long word --
    # "straw" (5 chars) -> "strawberry" (10 chars) -- 2x length ratio
    # The candidate selection's length_tolerance=2 means length buckets
    # only cover 3-7 chars, so "strawberry" is never even a candidate.
    # This is by design: fuzzy search is for typo correction, not prefix.
    results_straw = run_fuzzy_search(fuzzy, corpus, "straw", max_results=10)
    top_straw = [w for w, _ in results_straw]
    straw_finds_strawberry = "strawberry" in top_straw

    suite.results.append(
        TestResult(
            name="Prefix/known_gap: 'straw' does NOT find 'strawberry' (5 vs 10 chars -- trie's job)",
            query="straw",
            # This PASSES if strawberry is NOT found -- it's a known architectural gap
            passed=not straw_finds_strawberry,
            top_results=results_straw[:5],
            reason=(
                ""
                if not straw_finds_strawberry
                else "Unexpectedly found 'strawberry' -- candidate selection has changed"
            ),
        )
    )

    return suite


def test_false_positives(fuzzy: FuzzySearch, corpus: Corpus) -> TestSuite:
    """Test that garbage input returns no or very low-scoring results."""
    suite = TestSuite(name="False Positive Rejection")

    cases = [
        # (test_name, query, max_allowed_score, max_allowed_count, description)
        ("garbage_xyz", "xyz", 0.5, 3, "random 3-char should have few/low results"),
        ("garbage_qqqq", "qqqq", 0.5, 3, "repeated chars should have few/low results"),
        (
            "single_char_a",
            "a",
            0.6,
            5,
            "single char should not fuzzy-match many words highly",
        ),
        ("nonsense_long", "zxcvbnm", 0.4, 3, "keyboard mash should have very few results"),
    ]

    for test_name, query, max_score, max_count, description in cases:
        results = run_fuzzy_search(fuzzy, corpus, query, max_results=10)

        # Filter to only results above the threshold
        high_scoring = [(w, s) for w, s in results if s > max_score]

        passed = len(high_scoring) <= max_count

        suite.results.append(
            TestResult(
                name=f"FalsePos/{test_name}: '{query}' ({description})",
                query=query,
                passed=passed,
                top_results=results[:5],
                reason=(
                    ""
                    if passed
                    else f"{len(high_scoring)} results above {max_score} (max allowed: {max_count})"
                ),
            )
        )

    return suite


def test_ranking_quality(fuzzy: FuzzySearch, corpus: Corpus) -> TestSuite:
    """Test that results are ranked in a sensible order."""
    suite = TestSuite(name="Ranking Quality")

    # ── Test 1: "aple" should rank "apple" above "ample" above "maple" ──
    results = run_fuzzy_search(fuzzy, corpus, "aple", max_results=10)
    result_dict = {w: s for w, s in results}

    apple_score = result_dict.get("apple", 0.0)
    ample_score = result_dict.get("ample", 0.0)
    maple_score = result_dict.get("maple", 0.0)

    # apple should be the best match (edit distance 1)
    apple_above_ample = apple_score >= ample_score
    apple_above_maple = apple_score >= maple_score

    suite.results.append(
        TestResult(
            name="Ranking/aple: 'apple' should outscore 'ample'",
            query="aple",
            passed=apple_above_ample,
            top_results=results[:5],
            reason=(
                ""
                if apple_above_ample
                else f"apple={apple_score:.4f} < ample={ample_score:.4f}"
            ),
        )
    )

    suite.results.append(
        TestResult(
            name="Ranking/aple: 'apple' should outscore 'maple'",
            query="aple",
            passed=apple_above_maple,
            top_results=results[:5],
            reason=(
                ""
                if apple_above_maple
                else f"apple={apple_score:.4f} < maple={maple_score:.4f}"
            ),
        )
    )

    # ── Test 2: "banan" should rank "banana" #1 ──
    results_banana = run_fuzzy_search(fuzzy, corpus, "banan", max_results=5)
    banana_is_first = len(results_banana) > 0 and results_banana[0][0] == "banana"

    suite.results.append(
        TestResult(
            name="Ranking/banan: 'banana' should be top result",
            query="banan",
            passed=banana_is_first,
            top_results=results_banana[:5],
            reason=(
                ""
                if banana_is_first
                else f"Top result is '{results_banana[0][0]}' not 'banana'"
                if results_banana
                else "No results returned"
            ),
        )
    )

    # ── Test 3: Exact substring should score higher than distant match ──
    # "comput" should rank "computer" very high
    results_comput = run_fuzzy_search(fuzzy, corpus, "comput", max_results=5)
    comput_dict = {w: s for w, s in results_comput}
    computer_score = comput_dict.get("computer", 0.0)
    computer_in_top2 = "computer" in [w for w, _ in results_comput[:2]]

    suite.results.append(
        TestResult(
            name="Ranking/comput: 'computer' should be in top 2",
            query="comput",
            passed=computer_in_top2,
            top_results=results_comput[:5],
            reason=(
                ""
                if computer_in_top2
                else f"'computer' (score={computer_score:.4f}) not in top 2"
            ),
        )
    )

    # ── Test 4: Edit distance 1 should outscore edit distance 2+ ──
    # "orang" is edit-distance 1 from "orange" but further from "arrange"
    results_orang = run_fuzzy_search(fuzzy, corpus, "orang", max_results=5)
    orang_dict = {w: s for w, s in results_orang}
    orange_score = orang_dict.get("orange", 0.0)

    # orange should be the top result
    orange_is_top = len(results_orang) > 0 and results_orang[0][0] == "orange"

    suite.results.append(
        TestResult(
            name="Ranking/orang: 'orange' should be top result (edit dist 1)",
            query="orang",
            passed=orange_is_top,
            top_results=results_orang[:5],
            reason=(
                ""
                if orange_is_top
                else f"Top result is '{results_orang[0][0]}' not 'orange'"
                if results_orang
                else "No results returned"
            ),
        )
    )

    return suite


def test_length_correction(fuzzy: FuzzySearch, corpus: Corpus) -> TestSuite:
    """Test the length correction scoring adjustments."""
    suite = TestSuite(name="Length Correction")

    # Short query against long word should get penalized
    score_short_vs_long = apply_length_correction(
        "a", "elephant", 0.8, is_query_phrase=False, is_candidate_phrase=False
    )
    score_matched_length = apply_length_correction(
        "apple", "ample", 0.8, is_query_phrase=False, is_candidate_phrase=False
    )

    # Short query "a" against "elephant" should be penalized more than "apple" vs "ample"
    penalized_correctly = score_short_vs_long < score_matched_length

    suite.results.append(
        TestResult(
            name="LengthCorrection: short-vs-long gets heavier penalty",
            query="a",
            passed=penalized_correctly,
            top_results=[("'a' vs 'elephant'", score_short_vs_long), ("'apple' vs 'ample'", score_matched_length)],
            reason=(
                ""
                if penalized_correctly
                else f"short-vs-long={score_short_vs_long:.4f} >= matched={score_matched_length:.4f}"
            ),
        )
    )

    # Perfect match should not be corrected
    perfect_score = apply_length_correction(
        "apple", "apple", 1.0, is_query_phrase=False, is_candidate_phrase=False
    )

    suite.results.append(
        TestResult(
            name="LengthCorrection: perfect match score >= 0.99",
            query="apple",
            passed=perfect_score >= 0.99,
            top_results=[("apple", perfect_score)],
            reason="" if perfect_score >= 0.99 else f"Perfect score={perfect_score:.4f}",
        )
    )

    return suite


def test_edge_cases(fuzzy: FuzzySearch, corpus: Corpus) -> TestSuite:
    """Test edge cases and boundary conditions."""
    suite = TestSuite(name="Edge Cases")

    # Empty query
    results_empty = run_fuzzy_search(fuzzy, corpus, "", max_results=5)
    suite.results.append(
        TestResult(
            name="Edge/empty: empty query returns no results",
            query="",
            passed=len(results_empty) == 0,
            top_results=results_empty[:5],
            reason="" if len(results_empty) == 0 else f"Got {len(results_empty)} results for empty query",
        )
    )

    # Very long query
    long_query = "supercalifragilisticexpialidocious"
    results_long = run_fuzzy_search(fuzzy, corpus, long_query, max_results=5)
    # Should either return nothing or low-scoring results
    high_scoring_long = [(w, s) for w, s in results_long if s > 0.7]
    suite.results.append(
        TestResult(
            name="Edge/long: very long nonsense word has few high matches",
            query=long_query,
            passed=len(high_scoring_long) <= 2,
            top_results=results_long[:5],
            reason=(
                ""
                if len(high_scoring_long) <= 2
                else f"{len(high_scoring_long)} results above 0.7"
            ),
        )
    )

    # Query that IS in the vocabulary should get score ~1.0
    results_exact = run_fuzzy_search(fuzzy, corpus, "apple", max_results=5)
    apple_exact = next((s for w, s in results_exact if w == "apple"), 0.0)
    suite.results.append(
        TestResult(
            name="Edge/exact_in_vocab: 'apple' in corpus scores >= 0.85",
            query="apple",
            passed=apple_exact >= 0.85,
            top_results=results_exact[:5],
            reason="" if apple_exact >= 0.85 else f"apple score={apple_exact:.4f}",
        )
    )

    # Case insensitivity
    results_upper = run_fuzzy_search(fuzzy, corpus, "APPLE", max_results=5)
    found_apple_upper = any(w == "apple" for w, _ in results_upper)
    suite.results.append(
        TestResult(
            name="Edge/case: 'APPLE' finds 'apple' (case insensitive)",
            query="APPLE",
            passed=found_apple_upper,
            top_results=results_upper[:5],
            reason="" if found_apple_upper else "'apple' not found in results",
        )
    )

    return suite


def run_candidate_diagnostics(corpus: Corpus) -> None:
    """Print diagnostic info about candidate selection for key queries.

    This is informational only -- helps understand WHY certain queries fail.
    """
    from floridify.text.normalize import get_word_signature

    print(f"\n{'=' * 72}")
    print("  CANDIDATE SELECTION DIAGNOSTICS")
    print(f"{'=' * 72}")

    diagnostic_queries = ["aple", "comp", "comput", "elefant", "straw", "banan", "definately"]

    for query in diagnostic_queries:
        candidates = corpus.get_candidates(query.lower(), max_results=800)
        candidate_words = corpus.get_words_by_indices(candidates) if candidates else []

        query_sig = get_word_signature(query.lower())
        query_len = len(query)

        # Check what buckets matched
        sig_match = query_sig in corpus.signature_buckets
        len_matches = []
        for diff in range(3):
            for length in [query_len - diff, query_len + diff]:
                if length > 0 and length in corpus.length_buckets:
                    len_matches.append(length)

        print(f"\n  Query: '{query}'")
        print(f"    Signature: '{query_sig}' (bucket exists: {sig_match})")
        print(f"    Length: {query_len}, matching length buckets: {sorted(set(len_matches))}")
        print(f"    Candidates returned: {len(candidates)}")
        if candidate_words:
            print(f"    Sample candidates: {candidate_words[:15]}")
        else:
            print(f"    (no candidates -- fuzzy search falls back to full vocab or sample)")


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> int:
    print("=" * 72)
    print("  Fuzzy Search Quality Validation")
    print("=" * 72)

    # Build corpus
    print(f"\nBuilding corpus with {len(VOCABULARY)} words ...")
    t0 = time.perf_counter()
    corpus = build_corpus_sync(VOCABULARY)
    build_time = (time.perf_counter() - t0) * 1000
    print(f"  Corpus built: {len(corpus.vocabulary)} unique normalized words ({build_time:.1f}ms)")
    print(f"  Signature buckets: {len(corpus.signature_buckets)}")
    print(f"  Length buckets: {len(corpus.length_buckets)}")

    # Create fuzzy search engine
    fuzzy = FuzzySearch(min_score=DEFAULT_MIN_SCORE)

    # Run all test suites
    suites: list[TestSuite] = []

    test_functions = [
        test_typo_correction,
        test_prefix_matching,
        test_false_positives,
        test_ranking_quality,
        test_length_correction,
        test_edge_cases,
    ]

    total_passed = 0
    total_failed = 0

    for test_fn in test_functions:
        print(f"\n{'─' * 72}")
        suite = test_fn(fuzzy, corpus)
        suites.append(suite)
        print(f"\n  Suite: {suite.name}")

        for result in suite.results:
            print_test_result(result)

        total_passed += suite.passed
        total_failed += suite.failed

        suite_status = "ALL PASS" if suite.failed == 0 else f"{suite.failed} FAILED"
        print(f"\n  >> {suite.name}: {suite.passed}/{suite.total} passed ({suite_status})")

    # ── Candidate selection diagnostics ──
    run_candidate_diagnostics(corpus)

    # ── Summary ──
    print(f"\n{'=' * 72}")
    print("  SUMMARY")
    print(f"{'=' * 72}")

    for suite in suites:
        status = "PASS" if suite.failed == 0 else "FAIL"
        icon = "[+]" if suite.failed == 0 else "[-]"
        print(f"  {icon} {status}  {suite.name:40s}  {suite.passed}/{suite.total}")

    total = total_passed + total_failed
    print(f"\n  Total: {total_passed}/{total} passed, {total_failed} failed")

    if total_failed > 0:
        print(f"\n  RESULT: FAIL ({total_failed} test(s) failed)")
        return 1
    else:
        print(f"\n  RESULT: ALL TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
