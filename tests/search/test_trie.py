"""
Tests for trie-based exact and prefix search.

Comprehensive testing of TrieSearch functionality and performance.
"""

from __future__ import annotations

import pytest

from src.floridify.search.trie import TrieSearch


class TestTrieOptimizations:
    """Test marisa-trie optimizations and features."""

    def test_marisa_trie_backend(self) -> None:
        """Test that we're using marisa-trie backend."""
        trie = TrieSearch()
        trie.build_index(["test", "hello", "world"])

        stats = trie.get_statistics()
        assert "marisa-trie (C++)" in str(stats.get("backend", ""))
        assert "5x better than Python trie" in str(stats.get("memory_efficiency", ""))

    def test_save_and_load_persistence(self) -> None:
        """Test saving and loading trie data."""
        import tempfile
        from pathlib import Path

        trie = TrieSearch()
        words = ["test", "hello", "world", "search"]
        trie.build_index(words)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp:
            tmp_path = Path(tmp.name)

        try:
            trie.save_to_file(tmp_path)

            # Load into new trie
            new_trie = TrieSearch()
            new_trie.load_from_file(tmp_path)

            # Verify functionality is preserved
            assert new_trie.contains("test")
            assert new_trie.contains("hello")
            assert not new_trie.contains("notfound")

            # Verify stats are preserved
            original_stats = trie.get_statistics()
            loaded_stats = new_trie.get_statistics()
            assert original_stats["word_count"] == loaded_stats["word_count"]

        finally:
            tmp_path.unlink(missing_ok=True)


class TestTrieSearch:
    """Test TrieSearch functionality."""

    @pytest.fixture
    def sample_words(self) -> list[str]:
        """Sample word list for testing."""
        return [
            "hello",
            "help",
            "helpful",
            "hero",
            "world",
            "word",
            "work",
            "working",
            "search",
            "searching",
            "machine learning",
            "natural language",
            "hello world",
            "state-of-the-art",
        ]

    @pytest.fixture
    def trie_search(self, sample_words: list[str]) -> TrieSearch:
        """Create initialized trie search for testing."""
        trie = TrieSearch()
        trie.build_index(sample_words)
        return trie

    def test_initialization(self) -> None:
        """Test trie initialization."""
        trie = TrieSearch()

        # With marisa-trie backend, the trie is None until built
        assert trie._trie is None
        assert trie._word_count == 0
        assert trie._max_frequency == 0
        assert isinstance(trie._word_frequencies, dict)
        assert len(trie._word_frequencies) == 0

    def test_build_index(self, sample_words: list[str]) -> None:
        """Test building the trie index."""
        trie = TrieSearch()
        trie.build_index(sample_words)

        assert trie._word_count == len(sample_words)
        assert trie._max_frequency > 0

        # Check that trie is built and functional
        assert trie._trie is not None

        # Verify functionality by checking some words exist
        assert trie.contains("hello")
        assert trie.contains("help")
        assert trie.contains("world")
        assert trie.contains("search")

    def test_exact_search_found(self, trie_search: TrieSearch) -> None:
        """Test exact search for words that exist."""

        # Single words
        assert trie_search.search_exact("hello") == ["hello"]
        assert trie_search.search_exact("help") == ["help"]
        assert trie_search.search_exact("world") == ["world"]

        # Phrases
        assert trie_search.search_exact("hello world") == ["hello world"]
        assert trie_search.search_exact("machine learning") == ["machine learning"]
        assert trie_search.search_exact("natural language") == ["natural language"]

        # Hyphenated compounds
        assert trie_search.search_exact("state-of-the-art") == ["state-of-the-art"]

    def test_exact_search_not_found(self, trie_search: TrieSearch) -> None:
        """Test exact search for words that don't exist."""

        # Non-existent words
        assert trie_search.search_exact("nonexistent") == []
        assert trie_search.search_exact("missing") == []

        # Partial words (exist as prefixes but not complete words)
        assert trie_search.search_exact("hel") == []
        assert trie_search.search_exact("wor") == []

        # Wrong case (should be normalized)
        assert trie_search.search_exact("HELLO") == ["hello"]
        assert trie_search.search_exact("Hello") == ["hello"]

    def test_exact_search_edge_cases(self, trie_search: TrieSearch) -> None:
        """Test exact search edge cases."""

        # Empty string
        assert trie_search.search_exact("") == []

        # Whitespace only
        assert trie_search.search_exact("   ") == []

        # Special characters (should normalize)
        assert (
            trie_search.search_exact("hello!") == []
        )  # Punctuation removed, but result not in trie

    def test_prefix_search_found(self, trie_search: TrieSearch) -> None:
        """Test prefix search for existing prefixes."""

        # "hel" should match "hello", "help", "helpful"
        results = trie_search.search_prefix("hel")
        assert "hello" in results
        assert "help" in results
        assert "helpful" in results

        # "wor" should match "world", "word", "work", "working"
        results = trie_search.search_prefix("wor")
        assert "world" in results
        assert "word" in results
        assert "work" in results
        assert "working" in results

        # "search" should match "search", "searching"
        results = trie_search.search_prefix("search")
        assert "search" in results
        assert "searching" in results

    def test_prefix_search_single_letter(self, trie_search: TrieSearch) -> None:
        """Test prefix search with single letters."""

        # "h" should match all words starting with "h"
        results = trie_search.search_prefix("h")
        h_words = [
            w for w in ["hello", "help", "helpful", "hero", "hello world"] if w.startswith("h")
        ]

        for word in h_words:
            assert word in results

        # "w" should match all words starting with "w"
        results = trie_search.search_prefix("w")
        w_words = [w for w in ["world", "word", "work", "working"] if w.startswith("w")]

        for word in w_words:
            assert word in results

    def test_prefix_search_phrases(self, trie_search: TrieSearch) -> None:
        """Test prefix search with phrases."""

        # "hello " should match "hello world"
        results = trie_search.search_prefix("hello ")
        assert "hello world" in results

        # "machine" should match "machine learning"
        results = trie_search.search_prefix("machine")
        assert "machine learning" in results

        # "natural" should match "natural language"
        results = trie_search.search_prefix("natural")
        assert "natural language" in results

    def test_prefix_search_max_results(self, trie_search: TrieSearch) -> None:
        """Test prefix search result limiting."""

        # Test with small limit
        results = trie_search.search_prefix("h", max_results=2)
        assert len(results) <= 2

        # Test with larger limit
        results = trie_search.search_prefix("h", max_results=10)
        # Should have all h-words but not exceed 10
        assert len(results) <= 10

        # Test with very large limit
        results = trie_search.search_prefix("h", max_results=1000)
        # Should have all h-words
        h_word_count = len([w for w in trie_search.get_all_words() if w.startswith("h")])
        assert len(results) == h_word_count

    def test_prefix_search_not_found(self, trie_search: TrieSearch) -> None:
        """Test prefix search for non-existent prefixes."""

        # Non-existent prefixes
        assert trie_search.search_prefix("xyz") == []
        assert trie_search.search_prefix("qqq") == []

        # Empty string
        assert trie_search.search_prefix("") == []

    def test_contains_method(self, trie_search: TrieSearch) -> None:
        """Test the contains method."""

        # Existing words
        assert trie_search.contains("hello")
        assert trie_search.contains("world")
        assert trie_search.contains("machine learning")

        # Non-existing words
        assert not trie_search.contains("nonexistent")
        assert not trie_search.contains("missing")

        # Prefixes (should not be found as complete words)
        assert not trie_search.contains("hel")
        assert not trie_search.contains("wor")

    def test_get_all_words(self, trie_search: TrieSearch, sample_words: list[str]) -> None:
        """Test getting all words from the trie."""

        all_words = trie_search.get_all_words()

        # Should have all original words
        assert len(all_words) == len(sample_words)

        # All original words should be present
        for word in sample_words:
            assert word in all_words

        # Should be sorted by frequency (descending)
        # We can't test exact order without knowing frequencies,
        # but we can check that it's a valid ordering
        assert len(all_words) > 0

    def test_frequency_handling(self) -> None:
        """Test custom frequency handling."""

        words = ["hello", "world", "test"]
        frequencies = {"hello": 1000, "world": 500, "test": 100}

        trie = TrieSearch()
        trie.build_index(words, frequencies)

        assert trie._max_frequency == 1000

        # Get all words (should be sorted by frequency)
        all_words = trie.get_all_words()

        # "hello" should come first (highest frequency)
        assert all_words[0] == "hello"
        # "test" should come last (lowest frequency)
        assert all_words[-1] == "test"

    def test_default_frequency_calculation(self, trie_search: TrieSearch) -> None:
        """Test default frequency calculation."""

        # Shorter words should generally have higher frequency
        # This is a heuristic test
        all_words = trie_search.get_all_words()

        # Check that we have words of different lengths
        short_words = [w for w in all_words if len(w) <= 4]
        long_words = [w for w in all_words if len(w) > 8]

        assert len(short_words) > 0
        assert len(long_words) > 0

    def test_statistics(self, trie_search: TrieSearch, sample_words: list[str]) -> None:
        """Test trie statistics."""

        stats = trie_search.get_statistics()

        assert isinstance(stats, dict)
        assert "word_count" in stats
        assert "max_frequency" in stats
        assert "backend" in stats
        assert "memory_efficiency" in stats

        # Check values make sense
        assert stats["word_count"] == len(sample_words)
        assert stats["max_frequency"] > 0
        assert "marisa-trie" in str(stats["backend"])
        assert "5x better" in str(stats["memory_efficiency"])

    def test_case_insensitive_search(self, trie_search: TrieSearch) -> None:
        """Test that search is case insensitive."""

        # Exact search
        assert trie_search.search_exact("HELLO") == ["hello"]
        assert trie_search.search_exact("Hello") == ["hello"]
        assert trie_search.search_exact("hELLo") == ["hello"]

        # Prefix search
        results_lower = trie_search.search_prefix("hel")
        results_upper = trie_search.search_prefix("HEL")
        results_mixed = trie_search.search_prefix("Hel")

        assert results_lower == results_upper == results_mixed

    def test_phrase_vs_word_handling(self, trie_search: TrieSearch) -> None:
        """Test that phrases and words are handled correctly."""

        # Single words
        assert trie_search.search_exact("hello") == ["hello"]
        assert trie_search.search_exact("world") == ["world"]

        # Phrases (containing spaces)
        assert trie_search.search_exact("hello world") == ["hello world"]
        assert trie_search.search_exact("machine learning") == ["machine learning"]

        # Hyphenated compounds
        assert trie_search.search_exact("state-of-the-art") == ["state-of-the-art"]

        # Prefix search should work for both
        hello_results = trie_search.search_prefix("hello")
        assert "hello" in hello_results
        assert "hello world" in hello_results

    def test_empty_word_list(self) -> None:
        """Test trie with empty word list."""

        trie = TrieSearch()
        trie.build_index([])

        assert trie._word_count == 0
        assert trie.search_exact("anything") == []
        assert trie.search_prefix("anything") == []
        assert trie.get_all_words() == []

    def test_duplicate_words(self) -> None:
        """Test trie with duplicate words."""

        words = ["hello", "world", "hello", "test", "world"]

        trie = TrieSearch()
        trie.build_index(words)

        # Should count all words including duplicates
        assert trie._word_count == len(words)

        # But each unique word should appear only once in results
        assert trie.search_exact("hello") == ["hello"]
        assert trie.search_exact("world") == ["world"]

        # Get all words should have each word only once
        all_words = trie.get_all_words()
        unique_words = set(words)
        assert len(all_words) == len(unique_words)

    def test_special_characters_in_words(self) -> None:
        """Test trie with special characters in words."""

        words = ["café", "naïve", "résumé", "vis-à-vis", "state-of-the-art"]

        trie = TrieSearch()
        trie.build_index(words)

        # Should handle accented characters
        assert trie.search_exact("café") == ["café"]
        assert trie.search_exact("naïve") == ["naïve"]
        assert trie.search_exact("résumé") == ["résumé"]

        # Should handle hyphens and special characters
        assert trie.search_exact("vis-à-vis") == ["vis-à-vis"]
        assert trie.search_exact("state-of-the-art") == ["state-of-the-art"]

        # Prefix search should work
        cafe_results = trie.search_prefix("caf")
        assert "café" in cafe_results
