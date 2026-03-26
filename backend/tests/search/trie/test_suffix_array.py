"""Tests for suffix array substring/infix search.

Covers: substring search, infix match, suffix match, multi-word substring,
coverage scoring, exact self-match exclusion, and edge cases.
"""

from __future__ import annotations

import pytest

from floridify.search.fuzzy.suffix_array import SuffixArray


@pytest.fixture(scope="module")
def multilingual_vocab() -> list[str]:
    return sorted([
        "en coulisses", "a fond", "joie de vivre", "raison d etre",
        "coup de grace", "creme de la creme", "faux pas", "carte blanche",
        "bon voyage", "rendez vous", "mise en scene", "haute couture",
        "c est la vie", "entrepreneur", "bourgeois", "restaurant",
        "accommodate", "necessary", "perspicacious", "coulisses",
        "apple", "application", "apply", "banana", "beautiful",
        "cat", "dog", "elephant", "philosophy", "government",
    ])


@pytest.fixture(scope="module")
def suffix_array(multilingual_vocab: list[str]) -> SuffixArray:
    return SuffixArray(multilingual_vocab)


class TestSuffixArray:
    """Tests for suffix array substring/infix search."""

    def test_substring_found(self, suffix_array: SuffixArray, multilingual_vocab: list[str]):
        """Substring 'couliss' finds 'en coulisses' and 'coulisses'."""
        results = suffix_array.search("couliss", max_results=10)
        found = [multilingual_vocab[i] for i, _ in results]
        assert any("couliss" in w for w in found)

    def test_infix_match(self, suffix_array: SuffixArray, multilingual_vocab: list[str]):
        """Infix 'plicat' finds 'application'."""
        results = suffix_array.search("plicat", max_results=10)
        found = [multilingual_vocab[i] for i, _ in results]
        assert "application" in found

    def test_suffix_match(self, suffix_array: SuffixArray, multilingual_vocab: list[str]):
        """Suffix 'ophy' finds 'philosophy'."""
        results = suffix_array.search("ophy", max_results=10)
        found = [multilingual_vocab[i] for i, _ in results]
        assert "philosophy" in found

    def test_multi_word_substring(self, suffix_array: SuffixArray, multilingual_vocab: list[str]):
        """Substring spanning words: 'de vivre' finds 'joie de vivre'."""
        results = suffix_array.search("de vivre", max_results=10)
        found = [multilingual_vocab[i] for i, _ in results]
        assert "joie de vivre" in found

    def test_coverage_scoring(self, suffix_array: SuffixArray, multilingual_vocab: list[str]):
        """Shorter words with same substring score higher (better coverage)."""
        results = suffix_array.search("app", max_results=10)
        if len(results) >= 2:
            # First result should have higher coverage (query/word ratio)
            assert results[0][1] >= results[1][1]

    def test_no_exact_self_match(self, suffix_array: SuffixArray, multilingual_vocab: list[str]):
        """Exact matches are excluded (handled by exact search)."""
        results = suffix_array.search("apple", max_results=10)
        found = [multilingual_vocab[i] for i, _ in results]
        assert "apple" not in found  # Exact match excluded

    def test_empty_query(self, suffix_array: SuffixArray):
        """Empty query returns empty."""
        assert suffix_array.search("") == []

    def test_short_query(self, suffix_array: SuffixArray):
        """Single char query returns results."""
        results = suffix_array.search("a", max_results=5)
        # May or may not find results, but shouldn't crash
        assert isinstance(results, list)

    def test_empty_vocabulary(self):
        """Empty vocabulary produces working but empty suffix array."""
        sa = SuffixArray([])
        assert sa.search("test") == []
