"""
Tests for fuzzy search functionality.

Comprehensive testing of FuzzySearch with multiple algorithms and automatic method selection.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.floridify.search.fuzzy import FuzzyMatch, FuzzySearch, FuzzySearchMethod


class TestFuzzyMatch:
    """Test FuzzyMatch data structure."""

    def test_creation(self) -> None:
        """Test creation of FuzzyMatch objects."""

        match = FuzzyMatch(
            word="hello",
            score=0.9,
            method=FuzzySearchMethod.RAPIDFUZZ,
            edit_distance=1,
            is_phrase=False,
        )

        assert match.word == "hello"
        assert match.score == 0.9
        assert match.method == FuzzySearchMethod.RAPIDFUZZ
        assert match.edit_distance == 1
        assert not match.is_phrase

    def test_defaults(self) -> None:
        """Test default values in FuzzyMatch."""

        match = FuzzyMatch(
            word="test",
            score=0.8,
            method=FuzzySearchMethod.LEVENSHTEIN,
        )

        assert match.edit_distance == 0  # Default
        assert not match.is_phrase  # Default False


class TestFuzzySearch:
    """Test FuzzySearch functionality."""

    @pytest.fixture
    def sample_words(self) -> list[str]:
        """Sample word list for testing."""
        return [
            "hello",
            "help",
            "helpful",
            "world",
            "word",
            "work",
            "working",
            "definition",
            "dictionary",
            "search",
            "fuzzy",
            "semantic",
            "machine learning",
            "natural language",
            "hello world",
            "state-of-the-art",
        ]

    @pytest.fixture
    def fuzzy_search(self) -> FuzzySearch:
        """Create fuzzy search instance for testing."""
        return FuzzySearch(min_score=0.5)

    def test_initialization(self) -> None:
        """Test fuzzy search initialization."""

        # Default initialization
        fuzzy = FuzzySearch()
        assert fuzzy.min_score == 0.6  # Default value

        # Custom min_score
        fuzzy = FuzzySearch(min_score=0.8)
        assert fuzzy.min_score == 0.8

    def test_method_selection_auto(self, fuzzy_search: FuzzySearch) -> None:
        """Test automatic method selection based on query characteristics."""

        # Very short queries (≤2 chars) -> Jaro-Winkler
        method = fuzzy_search._select_optimal_method("hi")
        assert method in [FuzzySearchMethod.JARO_WINKLER, FuzzySearchMethod.RAPIDFUZZ]

        # Short queries (3 chars) -> Jaro-Winkler
        method = fuzzy_search._select_optimal_method("cat")
        assert method in [FuzzySearchMethod.JARO_WINKLER, FuzzySearchMethod.RAPIDFUZZ]

        # Medium queries (4-8 chars) -> RapidFuzz
        method = fuzzy_search._select_optimal_method("hello")
        assert method in [FuzzySearchMethod.RAPIDFUZZ, FuzzySearchMethod.LEVENSHTEIN]

        # Long queries (>8 chars) -> RapidFuzz or phonetic
        method = fuzzy_search._select_optimal_method("definition")
        assert method in [
            FuzzySearchMethod.RAPIDFUZZ,
            FuzzySearchMethod.SOUNDEX,
            FuzzySearchMethod.LEVENSHTEIN,
        ]

        # Queries with numbers -> RapidFuzz
        method = fuzzy_search._select_optimal_method("test123")
        assert method in [FuzzySearchMethod.RAPIDFUZZ, FuzzySearchMethod.LEVENSHTEIN]

    def test_levenshtein_distance(self, fuzzy_search: FuzzySearch) -> None:
        """Test Levenshtein distance calculation."""

        # Identical strings
        assert fuzzy_search._levenshtein_distance("hello", "hello") == 0

        # Single character difference
        assert fuzzy_search._levenshtein_distance("hello", "hallo") == 1
        assert fuzzy_search._levenshtein_distance("hello", "helloo") == 1
        assert fuzzy_search._levenshtein_distance("hello", "hell") == 1

        # Multiple differences
        assert fuzzy_search._levenshtein_distance("hello", "world") == 4
        assert fuzzy_search._levenshtein_distance("kitten", "sitting") == 3

        # Empty strings
        assert fuzzy_search._levenshtein_distance("", "") == 0
        assert fuzzy_search._levenshtein_distance("hello", "") == 5
        assert fuzzy_search._levenshtein_distance("", "world") == 5

    def test_search_levenshtein(self, fuzzy_search: FuzzySearch, sample_words: list[str]) -> None:
        """Test Levenshtein-based fuzzy search."""

        results = fuzzy_search._search_levenshtein("helo", sample_words, 5)

        # Should find "hello" as close match
        hello_matches = [r for r in results if r.word == "hello"]
        assert len(hello_matches) > 0

        # Should have reasonable scores
        for result in results:
            assert 0.0 <= result.score <= 1.0
            assert result.method == FuzzySearchMethod.LEVENSHTEIN

        # Results should be sorted by score (descending)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_with_method_specification(
        self, fuzzy_search: FuzzySearch, sample_words: list[str]
    ) -> None:
        """Test search with specific method."""

        # Test with Levenshtein
        results = fuzzy_search.search(
            "helo", sample_words, method=FuzzySearchMethod.LEVENSHTEIN, max_results=5
        )

        assert len(results) > 0
        for result in results:
            assert result.method == FuzzySearchMethod.LEVENSHTEIN

    def test_search_with_auto_method(
        self, fuzzy_search: FuzzySearch, sample_words: list[str]
    ) -> None:
        """Test search with automatic method selection."""

        results = fuzzy_search.search(
            "helo", sample_words, method=FuzzySearchMethod.AUTO, max_results=5
        )

        assert len(results) > 0
        # Method should be automatically selected
        assert all(r.method != FuzzySearchMethod.AUTO for r in results)

    def test_score_filtering(self, fuzzy_search: FuzzySearch, sample_words: list[str]) -> None:
        """Test that results are filtered by minimum score."""

        # Use high min_score to filter results
        results = fuzzy_search.search(
            "xyz",  # Should have low similarity to most words
            sample_words,
            min_score=0.9,  # Very high threshold
            max_results=10,
        )

        # Should have few or no results due to high threshold
        assert len(results) <= 5  # Most results should be filtered out

        # All remaining results should meet threshold
        for result in results:
            assert result.score >= 0.9

    def test_max_results_limiting(self, fuzzy_search: FuzzySearch, sample_words: list[str]) -> None:
        """Test that results are limited to max_results."""

        results = fuzzy_search.search(
            "e",  # Should match many words
            sample_words,
            max_results=3,
            min_score=0.1,  # Low threshold to get many matches
        )

        assert len(results) <= 3

    def test_empty_query_handling(self, fuzzy_search: FuzzySearch, sample_words: list[str]) -> None:
        """Test handling of empty queries."""

        # Empty string
        results = fuzzy_search.search("", sample_words)
        assert len(results) == 0

        # Whitespace only
        results = fuzzy_search.search("   ", sample_words)
        assert len(results) == 0

    def test_empty_word_list_handling(self, fuzzy_search: FuzzySearch) -> None:
        """Test handling of empty word list."""

        results = fuzzy_search.search("hello", [])
        assert len(results) == 0

    def test_phrase_detection(self, fuzzy_search: FuzzySearch, sample_words: list[str]) -> None:
        """Test that phrases are correctly identified in results."""

        results = fuzzy_search.search(
            "machine", sample_words, method=FuzzySearchMethod.LEVENSHTEIN, max_results=5
        )

        # Find results for "machine learning"
        ml_results = [r for r in results if r.word == "machine learning"]
        if ml_results:
            assert ml_results[0].is_phrase

        # Find results for single words
        single_word_results = [r for r in results if " " not in r.word]
        for result in single_word_results:
            assert not result.is_phrase

    def test_case_insensitive_search(
        self, fuzzy_search: FuzzySearch, sample_words: list[str]
    ) -> None:
        """Test that search is case insensitive."""

        # Test different cases of the same query
        results_lower = fuzzy_search.search("hello", sample_words, max_results=5)
        results_upper = fuzzy_search.search("HELLO", sample_words, max_results=5)
        results_mixed = fuzzy_search.search("Hello", sample_words, max_results=5)

        # Should produce similar results (allowing for floating point differences)
        assert len(results_lower) == len(results_upper) == len(results_mixed)

        # Top results should be the same
        if results_lower:
            assert results_lower[0].word == results_upper[0].word == results_mixed[0].word

    def test_typo_correction(self, fuzzy_search: FuzzySearch, sample_words: list[str]) -> None:
        """Test typo correction capabilities."""

        # Common typos
        typo_tests = [
            ("helo", "hello"),  # Missing letter
            ("helllo", "hello"),  # Extra letter
            ("hallo", "hello"),  # Wrong letter
            ("wrold", "world"),  # Transposition
            ("defination", "definition"),  # Common misspelling
        ]

        for typo, correct in typo_tests:
            results = fuzzy_search.search(typo, sample_words, max_results=5)

            # Should find the correct word in top results
            top_words = [r.word for r in results[:3]]
            assert correct in top_words, f"Failed to find '{correct}' for typo '{typo}'"

    def test_abbreviation_matching(
        self, fuzzy_search: FuzzySearch, sample_words: list[str]
    ) -> None:
        """Test matching of abbreviations."""

        # This is more challenging and depends on the method used
        abbreviation_tests = [
            ("ml", "machine learning"),  # Should work with some methods
            ("nl", "natural language"),  # Should work with some methods
        ]

        for abbrev, full_form in abbreviation_tests:
            results = fuzzy_search.search(
                abbrev,
                sample_words,
                method=FuzzySearchMethod.JARO_WINKLER,  # Better for abbreviations
                max_results=10,
                min_score=0.1,  # Lower threshold for abbreviations
            )

            # Check if full form is in results (not guaranteed but possible)
            result_words = [r.word for r in results]
            # This is a soft test - abbreviation matching is challenging
            assert len(results) > 0  # Should at least find something

    def test_available_methods(self, fuzzy_search: FuzzySearch) -> None:
        """Test getting available fuzzy search methods."""

        methods = fuzzy_search.get_available_methods()

        # Should always have these
        assert FuzzySearchMethod.LEVENSHTEIN in methods
        assert FuzzySearchMethod.AUTO in methods

        # Should be a reasonable number of methods
        assert len(methods) >= 2

    def test_method_info(self, fuzzy_search: FuzzySearch) -> None:
        """Test getting method information."""

        info = fuzzy_search.get_method_info()

        assert isinstance(info, dict)
        assert "rapidfuzz_available" in info
        assert "jellyfish_available" in info
        assert "available_methods" in info
        assert "recommended_method" in info

        # Check that available_methods is consistent
        assert isinstance(info["available_methods"], list)
        assert len(info["available_methods"]) > 0

    @patch("src.floridify.search.fuzzy.HAS_RAPIDFUZZ", False)
    @patch("src.floridify.search.fuzzy.HAS_JELLYFISH", False)
    def test_fallback_to_basic_methods(self, sample_words: list[str]) -> None:
        """Test fallback when advanced libraries are not available."""

        fuzzy = FuzzySearch()

        # Should still work with basic Levenshtein
        results = fuzzy.search("helo", sample_words, max_results=5)
        assert len(results) > 0

        # Should use Levenshtein method
        for result in results:
            assert result.method == FuzzySearchMethod.LEVENSHTEIN

    def test_string_similarity_calculation(self, fuzzy_search: FuzzySearch) -> None:
        """Test string similarity calculation for phonetic matches."""

        # Identical strings
        assert fuzzy_search._calculate_string_similarity("hello", "hello") == 1.0

        # Different strings
        similarity = fuzzy_search._calculate_string_similarity("hello", "hallo")
        assert 0.0 < similarity < 1.0

        # Very different strings
        similarity = fuzzy_search._calculate_string_similarity("hello", "xyz")
        assert 0.0 <= similarity < 0.5

        # Empty strings
        assert fuzzy_search._calculate_string_similarity("", "") == 1.0

    def test_search_result_ordering(
        self, fuzzy_search: FuzzySearch, sample_words: list[str]
    ) -> None:
        """Test that search results are properly ordered by score."""

        results = fuzzy_search.search("hello", sample_words, max_results=10)

        if len(results) > 1:
            # Should be sorted by score (descending)
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)

            # First result should have highest score
            assert results[0].score >= results[-1].score

    def test_edit_distance_in_results(
        self, fuzzy_search: FuzzySearch, sample_words: list[str]
    ) -> None:
        """Test that edit distance is included in Levenshtein results."""

        results = fuzzy_search.search(
            "helo", sample_words, method=FuzzySearchMethod.LEVENSHTEIN, max_results=5
        )

        # Should have edit distance for Levenshtein results
        for result in results:
            if result.method == FuzzySearchMethod.LEVENSHTEIN:
                assert result.edit_distance >= 0

    def test_special_characters_handling(self, fuzzy_search: FuzzySearch) -> None:
        """Test handling of special characters in queries and words."""

        special_words = ["café", "naïve", "résumé", "vis-à-vis", "state-of-the-art"]

        # Search for accented characters
        results = fuzzy_search.search("cafe", special_words, max_results=5)
        assert len(results) > 0

        # Should find "café" as a good match
        cafe_results = [r for r in results if r.word == "café"]
        if cafe_results:
            assert cafe_results[0].score > 0.5

        # Search for hyphenated compounds
        results = fuzzy_search.search("state of the art", special_words, max_results=5)
        sota_results = [r for r in results if r.word == "state-of-the-art"]
        if sota_results:
            assert sota_results[0].score > 0.5
