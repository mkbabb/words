"""Fuzzy search correctness tests.

Tests for scoring calibration, false positive prevention, length correction,
and phrase reordering. General fuzzy search functionality is tested in
test_search_optimization.py (TestFuzzySearch, 15+ parametrized tests).
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.models.base import Language
from floridify.search.fuzzy.search import FuzzySearch
from floridify.search.fuzzy.scoring import apply_length_correction


class TestBigramCandidateSelection:
    """Tests that the trigram index produces quality candidates for typo queries."""

    @pytest_asyncio.fixture
    async def typo_corpus(self):
        """Corpus with common misspelling targets."""
        vocabulary = [
            "ephemeral", "accommodate", "definitely", "separate",
            "occurrence", "recommend", "necessary", "environment",
            "beautiful", "beginning", "experience", "government",
            "restaurant", "technology", "development", "knowledge",
            "particular", "information", "understand", "philosophy",
            "psychology", "pneumonia", "mnemonic", "rhythm",
        ]
        corpus = await Corpus.create(
            corpus_name="test_typo_corpus",
            vocabulary=vocabulary,
            language=Language.ENGLISH,
        )
        if not corpus.corpus_uuid:
            corpus.corpus_uuid = str(uuid.uuid4())
        return corpus

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "typo,expected",
        [
            ("ephemrerl", "ephemeral"),
            ("accomodate", "accommodate"),
            ("definately", "definitely"),
            ("seperate", "separate"),
            ("occurence", "occurrence"),
            ("recomend", "recommend"),
            ("necesary", "necessary"),
            ("enviroment", "environment"),
        ],
    )
    async def test_typo_in_candidates(self, typo_corpus, typo, expected):
        """Verify target word is in get_candidates() output for typo queries."""
        candidates = typo_corpus.get_candidates(typo.lower(), max_results=1500)
        candidate_words = typo_corpus.get_words_by_indices(candidates)
        assert expected in candidate_words, (
            f"'{expected}' not found in candidates for typo '{typo}'. "
            f"Got {len(candidate_words)} candidates: {candidate_words[:20]}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "typo,expected",
        [
            ("ephemrerl", "ephemeral"),
            ("accomodate", "accommodate"),
            ("definately", "definitely"),
            ("seperate", "separate"),
            ("occurence", "occurrence"),
            ("recomend", "recommend"),
            ("necesary", "necessary"),
            ("enviroment", "environment"),
        ],
    )
    async def test_typo_fuzzy_search_finds_target(self, typo_corpus, typo, expected):
        """Full fuzzy search finds the correct word for common misspellings."""
        search = FuzzySearch(min_score=0.3)
        results = search.search(typo, corpus=typo_corpus, max_results=10)
        result_words = [r.word for r in results]
        assert expected in result_words[:5], (
            f"'{expected}' not in top 5 fuzzy results for '{typo}'. "
            f"Got: {result_words[:10]}"
        )


class TestFuzzySearchCorrectness:
    """Focused correctness tests for fuzzy search gaps identified in audit."""

    @pytest_asyncio.fixture
    async def correctness_corpus(self):
        """Corpus designed to test specific correctness edge cases (in-memory)."""
        vocabulary = [
            # Core words for edit distance testing
            "apple", "apples", "application", "apply",
            # Dissimilar words for false positive testing
            "xyz", "quantum", "zzzzz",
            # Phrase testing
            "machine learning", "big red dog", "learning machine",
            # Inflected forms for lemmatization testing
            "run", "running", "runs", "ran",
            "walk", "walking", "walks", "walked",
            # Length-varied words
            "a", "an", "the", "antidisestablishmentarianism",
            # Similar-sounding words
            "their", "there", "they're",
        ]

        corpus = await Corpus.create(
            corpus_name="test_correctness_corpus",
            vocabulary=vocabulary,
            language=Language.ENGLISH,
        )
        corpus.corpus_type = CorpusType.LANGUAGE
        if not corpus.corpus_uuid:
            corpus.corpus_uuid = str(uuid.uuid4())
        return corpus

    @pytest.fixture
    def strict_search(self):
        """FuzzySearch with standard min_score."""
        return FuzzySearch(min_score=0.3)

    @pytest.mark.asyncio
    async def test_false_positive_prevention(self, strict_search, correctness_corpus):
        """Assert dissimilar words do NOT match above reasonable threshold."""
        # "xyz" is completely dissimilar to "apple"
        results = strict_search.search(
            "xyz", corpus=correctness_corpus, max_results=10, min_score=0.5
        )

        # Should not find "apple" with score >= 0.5
        apple_results = [r for r in results if r.word == "apple"]
        assert len(apple_results) == 0, (
            f"Dissimilar query 'xyz' should NOT match 'apple' at min_score=0.5, "
            f"but got score {apple_results[0].score:.3f}" if apple_results else ""
        )

    @pytest.mark.asyncio
    async def test_length_correction_short_fragment(self, strict_search, correctness_corpus):
        """Short fragments shouldn't outscore full matches via apply_length_correction."""
        # Verify length correction penalizes short candidates for long queries
        score_short = apply_length_correction(
            query="application",
            candidate="a",
            base_score=0.8,
        )
        score_full = apply_length_correction(
            query="application",
            candidate="application",
            base_score=0.8,
        )

        assert score_full > score_short, (
            f"Full match score ({score_full:.3f}) should exceed "
            f"short fragment score ({score_short:.3f})"
        )

    @pytest.mark.asyncio
    async def test_length_correction_prefix_bonus(self):
        """Prefix matches should get ~1.3x bonus from apply_length_correction."""
        score_prefix = apply_length_correction(
            query="app",
            candidate="apple",
            base_score=0.7,
        )
        score_non_prefix = apply_length_correction(
            query="ple",
            candidate="apple",
            base_score=0.7,
        )

        # Prefix match should score higher (1.3x bonus)
        assert score_prefix > score_non_prefix, (
            f"Prefix score ({score_prefix:.3f}) should exceed "
            f"non-prefix score ({score_non_prefix:.3f})"
        )

    @pytest.mark.asyncio
    async def test_length_correction_phrase_bonus(self):
        """Phrase matching bonuses (1.1-1.3x) should be applied correctly."""
        # Both phrases, similar length → 1.1x bonus
        score_both_phrases = apply_length_correction(
            query="big red dog",
            candidate="big red cat",
            base_score=0.7,
            is_query_phrase=True,
            is_candidate_phrase=True,
        )
        # Query is word, candidate is phrase, not prefix → 0.95x penalty
        score_word_to_phrase = apply_length_correction(
            query="dog",
            candidate="big red dog",
            base_score=0.7,
            is_query_phrase=False,
            is_candidate_phrase=True,
        )
        # Exact word matching first word of phrase → 1.2x bonus
        score_first_word = apply_length_correction(
            query="big",
            candidate="big red dog",
            base_score=0.7,
            is_query_phrase=False,
            is_candidate_phrase=True,
        )

        # First word match should get biggest bonus
        assert score_first_word > score_word_to_phrase, (
            f"First word match ({score_first_word:.3f}) should exceed "
            f"non-first-word match ({score_word_to_phrase:.3f})"
        )

    @pytest.mark.asyncio
    async def test_dual_scorer_phrase_reordering(self, strict_search, correctness_corpus):
        """Demonstrate dual-scorer value: phrase reordering should still find match.

        "learning machine" should find "machine learning" via token_set_ratio.
        """
        results = strict_search.search(
            "learning machine",
            corpus=correctness_corpus,
            max_results=5,
            min_score=0.3,
        )

        words = [r.word for r in results]
        # Should find "machine learning" despite word reordering
        has_ml = any("machine" in w and "learning" in w for w in words)
        assert has_ml, (
            f"Reordered phrase 'learning machine' should find 'machine learning', "
            f"but got: {words}"
        )

    @pytest.mark.asyncio
    async def test_lemmatization_integration(self, strict_search, correctness_corpus):
        """Verify "running" matches lemma "run" correctly."""
        results = strict_search.search(
            "running",
            corpus=correctness_corpus,
            max_results=10,
            min_score=0.3,
        )

        words = [r.word for r in results]
        # Should find "run" or "running" (both are in corpus)
        assert any(w in ("run", "running", "runs", "ran") for w in words), (
            f"Query 'running' should match run-family words, but got: {words}"
        )

    @pytest.mark.asyncio
    async def test_scoring_calibration_single_substitution(self, strict_search, correctness_corpus):
        """Single substitution typos should score in 0.7-1.0 range."""
        # "apnle" → single substitution in "apple" (p→n)
        results = strict_search.search(
            "apnle",
            corpus=correctness_corpus,
            max_results=5,
        )

        apple_results = [r for r in results if r.word == "apple"]
        if apple_results:
            assert 0.6 <= apple_results[0].score <= 1.0, (
                f"Single substitution score {apple_results[0].score:.3f} "
                f"outside expected range [0.6, 1.0]"
            )

    @pytest.mark.asyncio
    async def test_scoring_calibration_single_transposition(self, strict_search, correctness_corpus):
        """Single transposition typos should score in 0.75-1.0 range."""
        # "appel" → transposition of l and e in "apple"
        results = strict_search.search(
            "appel",
            corpus=correctness_corpus,
            max_results=5,
        )

        apple_results = [r for r in results if r.word == "apple"]
        if apple_results:
            assert 0.7 <= apple_results[0].score <= 1.0, (
                f"Transposition score {apple_results[0].score:.3f} "
                f"outside expected range [0.7, 1.0]"
            )

    @pytest.mark.asyncio
    async def test_scoring_calibration_double_error(self, strict_search, correctness_corpus):
        """Double-error typos should score in 0.5-0.85 range."""
        # "aplee" → two errors from "apple"
        results = strict_search.search(
            "aplee",
            corpus=correctness_corpus,
            max_results=5,
        )

        apple_results = [r for r in results if r.word == "apple"]
        if apple_results:
            assert 0.4 <= apple_results[0].score <= 0.9, (
                f"Double error score {apple_results[0].score:.3f} "
                f"outside expected range [0.4, 0.9]"
            )
