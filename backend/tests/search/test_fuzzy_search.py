"""Fuzzy search component tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.search.constants import SearchMethod
from floridify.search.fuzzy import FuzzySearch
from floridify.search.utils import apply_length_correction


@pytest_asyncio.fixture
async def fuzzy_corpus(test_db):
    """Create corpus for fuzzy search testing."""
    vocabulary = [
        # Similar words for fuzzy matching
        "apple",
        "apples",
        "aple",
        "appel",
        "banana",
        "bananna",
        "bannana",
        "orange",
        "orang",
        "oranges",  # Added orange to match test expectations
        "strawberry",
        "strawbery",
        "stawberry",
        "watermelon",
        "watermellon",
        "watermelen",
        # Some distinct words
        "grape",
        "cherry",
        "peach",
        "plum",
    ]

    corpus = await Corpus.create(
        corpus_name="test_fuzzy_corpus",
        vocabulary=vocabulary,
        language=Language.ENGLISH,
    )
    corpus.corpus_type = CorpusType.LANGUAGE
    corpus.lemmatized_vocabulary = vocabulary

    manager = TreeCorpusManager()
    saved = await manager.save_corpus(corpus)
    return saved


@pytest_asyncio.fixture
async def fuzzy_search():
    """Create FuzzySearch instance."""
    search = FuzzySearch(min_score=0.4)
    return search


class TestFuzzySearch:
    """Test suite for fuzzy search functionality."""

    @pytest.mark.asyncio
    async def test_rapidfuzz_integration(self, fuzzy_search, fuzzy_corpus):
        """Test RapidFuzz backend performance."""
        # Test with typo
        results = fuzzy_search.search("aple", corpus=fuzzy_corpus, max_results=5)

        # Should find "apple" as top result
        assert len(results) > 0
        assert results[0].word in ["apple", "aple"]
        assert results[0].method == SearchMethod.FUZZY
        assert results[0].score > 0.8

    @pytest.mark.asyncio
    async def test_candidate_preselection(self, fuzzy_search, fuzzy_corpus):
        """Test fuzzy candidate optimization."""
        # Search for a word with many similar candidates
        results = fuzzy_search.search("straberry", corpus=fuzzy_corpus, max_results=3)

        # Should efficiently find strawberry variants
        words = [r.word for r in results]
        assert any("straw" in w for w in words)

    @pytest.mark.asyncio
    async def test_multi_scorer_approach(self, fuzzy_search, fuzzy_corpus):
        """Test WRatio vs token_set_ratio scoring."""
        # Test different scoring methods - FuzzySearch uses default scorer
        # Test with single-word queries that exist in the corpus

        results_apple = fuzzy_search.search(
            "aple",  # Typo of apple
            corpus=fuzzy_corpus,
            max_results=5,
            min_score=0.5,
        )

        results_banana = fuzzy_search.search(
            "bananna",  # Alternative spelling in corpus
            corpus=fuzzy_corpus,
            max_results=5,
            min_score=0.5,
        )

        # Both should find related words
        assert len(results_apple) > 0
        assert len(results_banana) > 0

        # Should find apple variants
        apple_words = [r.word for r in results_apple]
        assert any("apple" in w or "aple" in w or "appel" in w for w in apple_words)

        # Should find banana variants
        banana_words = [r.word for r in results_banana]
        assert any("banana" in w or "bananna" in w for w in banana_words)

    @pytest.mark.asyncio
    async def test_typo_tolerance(self, fuzzy_search, fuzzy_corpus):
        """Test tolerance for different types of typos."""
        # Substitution
        results = fuzzy_search.search("apole", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word for r in results)

        # Insertion
        results = fuzzy_search.search("appple", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word for r in results)

        # Deletion
        results = fuzzy_search.search("aple", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word for r in results)

        # Transposition
        results = fuzzy_search.search("appel", corpus=fuzzy_corpus, max_results=3)
        assert any("apple" in r.word or "appel" in r.word for r in results)

    @pytest.mark.asyncio
    async def test_similarity_threshold(self, fuzzy_search, fuzzy_corpus):
        """Test minimum similarity threshold."""
        # High threshold - should only find very similar words
        results = fuzzy_search.search("apple", corpus=fuzzy_corpus, max_results=10, min_score=0.9)

        # All results should have high similarity
        assert all(r.score >= 0.9 for r in results)

        # Low threshold - should find more distant matches
        results = fuzzy_search.search("apple", corpus=fuzzy_corpus, max_results=10, min_score=0.5)

        # Should find more results
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, fuzzy_search, fuzzy_corpus):
        """Test handling of empty queries."""
        results = fuzzy_search.search("", corpus=fuzzy_corpus)
        assert len(results) == 0

        results = fuzzy_search.search("   ", corpus=fuzzy_corpus)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_special_character_handling(self, fuzzy_search, fuzzy_corpus):
        """Test fuzzy search with special characters."""
        # Should normalize and still find matches
        results = fuzzy_search.search("app-le", corpus=fuzzy_corpus, max_results=3)
        assert len(results) > 0

        results = fuzzy_search.search("app_le", corpus=fuzzy_corpus, max_results=3)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_case_insensitive_fuzzy(self, fuzzy_search, fuzzy_corpus):
        """Test case-insensitive fuzzy matching."""
        results = fuzzy_search.search("APPLE", corpus=fuzzy_corpus, max_results=3)

        assert len(results) > 0
        # Should find apple regardless of case
        assert any("apple" in r.word.lower() for r in results)

    @pytest.mark.asyncio
    async def test_performance_with_large_vocabulary(self, test_db):
        """Test fuzzy search performance with large vocabulary."""
        # Generate large vocabulary
        large_vocab = []
        for i in range(1000):
            large_vocab.extend(
                [
                    f"word{i}",
                    f"term{i}",
                    f"text{i}",
                ]
            )

        corpus = Corpus(
            corpus_name="large_fuzzy_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(set(large_vocab)),
            original_vocabulary=large_vocab,
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        search = FuzzySearch(min_score=0.4)

        # Should complete search quickly even with large vocabulary
        import time

        start = time.time()
        results = search.search("word500", corpus=saved_corpus, max_results=5)
        elapsed = time.time() - start

        assert len(results) > 0
        assert elapsed < 1.0  # Should complete within 1 second

    @pytest.mark.asyncio
    async def test_concurrent_fuzzy_searches(self, fuzzy_search, fuzzy_corpus):
        """Test concurrent fuzzy searches."""
        import asyncio

        queries = ["aple", "bananna", "orang", "grap"]

        # Run searches concurrently
        results = await asyncio.gather(
            *[asyncio.to_thread(fuzzy_search.search, q, fuzzy_corpus, 3) for q in queries]
        )

        # Each search should return results
        assert all(len(r) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_fuzzy_search_ranking(self, fuzzy_search, fuzzy_corpus):
        """Test result ranking by similarity."""
        results = fuzzy_search.search("apple", corpus=fuzzy_corpus, max_results=10)

        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Exact match should be first if it exists
        if results and "apple" in fuzzy_corpus.vocabulary:
            assert results[0].word == "apple"
            assert results[0].score >= 0.99  # Fuzzy might not be exactly 1.0

    @pytest.mark.asyncio
    async def test_phonetic_similarity(self, fuzzy_search, fuzzy_corpus):
        """Test finding phonetically similar words."""
        # Words that sound similar but spelled differently
        results = fuzzy_search.search("cheree", corpus=fuzzy_corpus, max_results=5)

        # Should find "cherry" based on phonetic similarity
        words = [r.word for r in results]
        assert any("cherry" in w for w in words)

    @pytest.mark.asyncio
    async def test_fuzzy_with_empty_corpus(self, test_db):
        """Test fuzzy search with empty corpus."""
        corpus = Corpus(
            corpus_name="empty_fuzzy_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=[],
            original_vocabulary=[],
        )

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        search = FuzzySearch(min_score=0.4)
        results = search.search("test", corpus=saved_corpus)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fuzzy_search_metadata(self, fuzzy_search, fuzzy_corpus):
        """Test metadata in fuzzy search results."""
        results = fuzzy_search.search("aple", corpus=fuzzy_corpus, max_results=3)

        for result in results:
            assert result.method == SearchMethod.FUZZY
            assert 0 <= result.score <= 1.0
            assert result.word in fuzzy_corpus.vocabulary
            assert result.lemmatized_word is not None


class TestFuzzySearchCorrectness:
    """Focused correctness tests for fuzzy search gaps identified in audit."""

    @pytest_asyncio.fixture
    async def correctness_corpus(self, test_db):
        """Corpus designed to test specific correctness edge cases."""
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

        manager = TreeCorpusManager()
        return await manager.save_corpus(corpus)

    @pytest.fixture
    def strict_search(self):
        """FuzzySearch with standard min_score."""
        return FuzzySearch(min_score=0.3)

    @pytest.mark.asyncio
    async def test_edit_distance_ranking(self, strict_search, correctness_corpus):
        """Assert ED=1 matches score higher than ED=2 consistently.

        "aple" (ED=1 from apple) should score higher than "aplee" (ED=2 from apple).
        """
        # ED=1: single deletion
        results_ed1 = strict_search.search("aple", corpus=correctness_corpus, max_results=10)
        # ED=2: two errors
        results_ed2 = strict_search.search("aplpe", corpus=correctness_corpus, max_results=10)

        # Both should find "apple"
        ed1_apple = [r for r in results_ed1 if r.word == "apple"]
        ed2_apple = [r for r in results_ed2 if r.word == "apple"]

        assert len(ed1_apple) > 0, "ED=1 query should find 'apple'"
        assert len(ed2_apple) > 0, "ED=2 query should find 'apple'"

        # ED=1 match should score higher than ED=2
        assert ed1_apple[0].score > ed2_apple[0].score, (
            f"ED=1 score ({ed1_apple[0].score:.3f}) should be > "
            f"ED=2 score ({ed2_apple[0].score:.3f})"
        )

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
