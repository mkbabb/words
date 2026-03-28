"""Tests for text canonicalization used in definition dedup."""

from __future__ import annotations

from floridify.ai.dedup.canonicalize import canonicalize, extract_content_words


class TestCanonicalize:
    def test_lowercases(self) -> None:
        assert canonicalize("Hello World") == "hello world"

    def test_strips_punctuation(self) -> None:
        assert canonicalize("a large body of water.") == "a large body of water"

    def test_collapses_whitespace(self) -> None:
        assert canonicalize("a   large   body") == "a large body"

    def test_strips_leading_trailing(self) -> None:
        assert canonicalize("  hello  ") == "hello"

    def test_identical_after_canonicalization(self) -> None:
        a = "A large body of water."
        b = "a large body of water"
        assert canonicalize(a) == canonicalize(b)

    def test_preserves_content(self) -> None:
        assert "sloping" in canonicalize("Sloping land beside a river.")


class TestExtractContentWords:
    def test_excludes_stopwords(self) -> None:
        words = extract_content_words("a large body of water")
        assert "a" not in words
        assert "of" not in words
        assert "large" in words
        assert "body" in words
        assert "water" in words

    def test_returns_set(self) -> None:
        result = extract_content_words("the quick brown fox")
        assert isinstance(result, set)

    def test_empty_for_all_stopwords(self) -> None:
        result = extract_content_words("the is a of to")
        assert len(result) == 0
