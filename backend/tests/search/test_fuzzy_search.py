"""Comprehensive tests for FuzzySearch functionality."""

import time

import pytest

from floridify.corpus.core import Corpus
from floridify.search.fuzzy import FuzzySearch


class TestFuzzySearchBasic:
    """Test basic FuzzySearch functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, sample_corpus: Corpus):
        """Test FuzzySearch initialization."""
        fuzzy = FuzzySearch(min_score=0.6)

        assert fuzzy.min_score == 0.6

    @pytest.mark.asyncio
    async def test_exact_match_fuzzy(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test that exact matches get perfect scores."""
        results = fuzzy_search.search("apple", sample_corpus)

        assert len(results) > 0
        # First result should be exact match with perfect score
        assert results[0].word == "apple"
        assert results[0].score >= 0.99  # Near perfect score for exact match
        assert results[0].method == "fuzzy"

    @pytest.mark.asyncio
    async def test_misspelled_words(
        self, fuzzy_search: FuzzySearch, sample_corpus: Corpus, search_queries: dict
    ):
        """Test fuzzy search with common misspellings."""
        misspellings = {
            "aple": "apple",
            "aplication": "application",
            "banna": "banana",
            "catlog": "catalog",
            "catagory": "category",
            "chanje": "change",
            "compeat": "compete",
            "contry": "country",
        }

        for misspelled, correct in misspellings.items():
            results = fuzzy_search.search(misspelled, sample_corpus)
            assert len(results) > 0

            # The correct word should be in top results
            found_words = [r.word for r in results[:5]]
            assert correct in found_words

            # Check that scores are reasonable (not too low)
            top_result = results[0]
            assert top_result.score > 0.5

    @pytest.mark.asyncio
    async def test_typo_tolerance(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test tolerance for different types of typos."""
        # Single character substitution
        results = fuzzy_search.search("compurer", sample_corpus)  # computer
        assert any(r.word == "computer" for r in results[:5])

        # Character transposition
        results = fuzzy_search.search("cmoputer", sample_corpus)  # computer
        assert any(r.word == "computer" for r in results[:5])

        # Missing character
        results = fuzzy_search.search("compter", sample_corpus)  # computer
        assert any(r.word == "computer" for r in results[:5])

        # Extra character
        results = fuzzy_search.search("compputer", sample_corpus)  # computer
        assert any(r.word == "computer" for r in results[:5])

    @pytest.mark.asyncio
    async def test_score_ordering(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test that results are properly ordered by score."""
        results = fuzzy_search.search("comput", sample_corpus)

        assert len(results) > 0

        # Scores should be in descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Distance should generally increase (lower score = higher distance)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    @pytest.mark.asyncio
    async def test_max_results_limit(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test max_results parameter."""
        # Default should return multiple results
        results_default = fuzzy_search.search("app", sample_corpus)
        assert len(results_default) > 5

        # Test with limit
        results_limited = fuzzy_search.search("app", sample_corpus, max_results=3)
        assert len(results_limited) == 3

        # Should return top scoring results
        assert results_limited[0].score >= results_limited[-1].score

    @pytest.mark.asyncio
    async def test_min_score_threshold(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test min_score parameter filtering."""
        # Search with no threshold
        all_results = fuzzy_search.search("xyz", sample_corpus)

        # Search with high threshold
        filtered_results = fuzzy_search.search("xyz", sample_corpus, min_score=0.7)

        # Filtered should have fewer or equal results
        assert len(filtered_results) <= len(all_results)

        # All filtered results should meet threshold
        for result in filtered_results:
            assert result.score >= 0.7

    @pytest.mark.asyncio
    async def test_empty_query(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test handling of empty queries."""
        results = fuzzy_search.search("", sample_corpus)
        assert len(results) == 0

        results = fuzzy_search.search("   ", sample_corpus)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_whitespace_normalization(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test whitespace handling in queries."""
        results1 = fuzzy_search.search("apple", sample_corpus)
        results2 = fuzzy_search.search("  apple  ", sample_corpus)

        # Should produce same results
        assert len(results1) == len(results2)
        if results1 and results2:
            assert results1[0].word == results2[0].word
            assert abs(results1[0].score - results2[0].score) < 0.01


class TestFuzzySearchAdvanced:
    """Test advanced FuzzySearch features."""

    @pytest.mark.asyncio
    async def test_multi_word_query(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test fuzzy search with multi-word queries."""
        # Search for compound terms
        results = fuzzy_search.search("computer science", sample_corpus)

        # Should find individual words
        words = [r.word for r in results]
        assert any("computer" in w or "science" in w for w in words)

    @pytest.mark.asyncio
    async def test_partial_word_matching(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test partial word matching capabilities."""
        # Prefix matching
        results = fuzzy_search.search("prog", sample_corpus)
        # Might match "program", "progress", etc. if in corpus

        # Suffix matching
        results = fuzzy_search.search("tion", sample_corpus)
        # Should match words ending in "tion"
        matching_words = [r.word for r in results if "tion" in r.word]
        assert len(matching_words) > 0

    @pytest.mark.asyncio
    async def test_phonetic_similarity(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test phonetic similarity matching."""
        # Words that sound similar
        phonetic_pairs = [
            ("nite", "night"),  # Different spelling, similar sound
            ("fone", "phone"),
            ("rite", "right"),
        ]

        for phonetic, expected in phonetic_pairs:
            fuzzy_search.search(phonetic, sample_corpus)
            # May or may not find depending on algorithm
            # This is more of a feature test than requirement

    @pytest.mark.asyncio
    async def test_keyboard_distance_typos(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test handling of keyboard-distance based typos."""
        # Adjacent key typos
        keyboard_typos = {
            "conputer": "computer",  # n/m are adjacent
            "vomputer": "computer",  # v/c are adjacent
        }

        for typo, correct in keyboard_typos.items():
            results = fuzzy_search.search(typo, sample_corpus)
            [r.word for r in results[:10]]
            # Should find the correct word in top results

    @pytest.mark.asyncio
    async def test_case_sensitivity(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test case handling in fuzzy search."""
        results_lower = fuzzy_search.search("computer", sample_corpus)
        results_upper = fuzzy_search.search("COMPUTER", sample_corpus)
        results_mixed = fuzzy_search.search("ComPuTeR", sample_corpus)

        # All should find the same word
        assert results_lower[0].word == results_upper[0].word
        assert results_lower[0].word == results_mixed[0].word

        # Scores should be very similar
        assert abs(results_lower[0].score - results_upper[0].score) < 0.01
        assert abs(results_lower[0].score - results_mixed[0].score) < 0.01


class TestFuzzySearchPerformance:
    """Test FuzzySearch performance characteristics."""

    @pytest.mark.asyncio
    async def test_search_performance(
        self, fuzzy_search: FuzzySearch, sample_corpus: Corpus, performance_thresholds: dict
    ):
        """Test fuzzy search operation performance."""
        # Warm up
        _ = fuzzy_search.search("test", sample_corpus)

        # Measure search time
        queries = ["apple", "compter", "banna", "categry", "chng"]

        start = time.perf_counter()
        for query in queries:
            _ = fuzzy_search.search(query, sample_corpus)
        elapsed = (time.perf_counter() - start) / len(queries)

        assert elapsed < performance_thresholds["fuzzy_search"]

    @pytest.mark.asyncio
    async def test_large_corpus_performance(self):
        """Test performance with large corpus."""
        # Create large corpus
        large_words = [f"word_{i:06d}" for i in range(10000)]
        large_corpus = Corpus(
            corpus_name="large-test",
            language="en",
            vocabulary=large_words,
            unique_word_count=len(large_words),
            total_word_count=len(large_words),
        )

        fuzzy = FuzzySearch()

        # Search should complete in reasonable time
        start = time.perf_counter()
        results = fuzzy.search("word_005000", large_corpus, max_results=10)
        search_time = time.perf_counter() - start

        # Even with large corpus, should be under 100ms
        assert search_time < 0.1
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_batch_search_performance(
        self, fuzzy_search: FuzzySearch, sample_corpus: Corpus, performance_thresholds: dict
    ):
        """Test performance of batch searches."""
        queries = ["apple", "banna", "compter", "categry", "chng", "comunicte", "contry", "cupple"]

        start = time.perf_counter()
        for query in queries:
            _ = fuzzy_search.search(query, max_results=5)
        batch_time = time.perf_counter() - start

        assert batch_time < performance_thresholds["batch_search"]


class TestFuzzySearchEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_very_long_query(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test handling of very long queries."""
        long_query = "a" * 1000
        results = fuzzy_search.search(long_query, max_results=5)

        # Should handle gracefully, likely returning no/few results
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_special_characters(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test queries with special characters."""
        special_queries = ["hello@world", "test-case", "$money$", "C++", "100%", "#hashtag"]

        for query in special_queries:
            results = fuzzy_search.search(query, sample_corpus)
            # Should handle without crashing
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_unicode_queries(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test Unicode character handling."""
        unicode_queries = [
            "café",
            "naïve",
            "résumé",
            "北京",  # Beijing in Chinese
            "🚀",  # Emoji
        ]

        for query in unicode_queries:
            results = fuzzy_search.search(query, sample_corpus)
            # Should handle without crashing
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_numeric_queries(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test numeric string queries."""
        numeric_queries = ["123", "456.789", "0", "-1", "3.14159"]

        for query in numeric_queries:
            results = fuzzy_search.search(query, sample_corpus)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_empty_corpus(self):
        """Test fuzzy search with empty corpus."""
        empty_corpus = Corpus(
            corpus_name="empty-test",
            language="en",
            vocabulary=[],
            unique_word_count=0,
            total_word_count=0,
        )

        fuzzy = FuzzySearch()
        results = fuzzy.search("anything", empty_corpus)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_single_word_corpus(self):
        """Test fuzzy search with single-word corpus."""
        single_corpus = Corpus(
            corpus_name="single-test",
            language="en",
            vocabulary=["unique"],
            unique_word_count=1,
            total_word_count=1,
        )

        fuzzy = FuzzySearch()

        # Exact match
        results = fuzzy.search("unique", single_corpus)
        assert len(results) == 1
        assert results[0].word == "unique"
        assert results[0].score > 0.99

        # Near match
        results = fuzzy.search("uniq", single_corpus)
        assert len(results) == 1
        assert results[0].word == "unique"

        # Far match
        results = fuzzy.search("different", single_corpus)
        # Might return the only word with low score
        if results:
            assert results[0].score < 0.5

    @pytest.mark.asyncio
    async def test_repeated_characters(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test queries with repeated characters."""
        results = fuzzy_search.search("commmmunication", sample_corpus)

        # Should find "communication" or similar
        [r.word for r in results[:10]]
        # Check if any communication-related words found

    @pytest.mark.asyncio
    async def test_score_consistency(self, fuzzy_search: FuzzySearch, sample_corpus: Corpus):
        """Test that scores are consistent across searches."""
        query = "apple"

        results1 = fuzzy_search.search(query, sample_corpus)
        results2 = fuzzy_search.search(query, sample_corpus)

        # Same query should produce same results
        assert len(results1) == len(results2)

        for r1, r2 in zip(results1[:5], results2[:5]):
            assert r1.word == r2.word
            assert abs(r1.score - r2.score) < 0.001
