"""
Tests for phrase normalization and multi-word expression handling.

Comprehensive testing of PhraseNormalizer and MultiWordExpression functionality.
"""

from __future__ import annotations

import pytest

from src.floridify.search.phrase import MultiWordExpression, PhraseNormalizer


class TestPhraseNormalizer:
    """Test phrase normalization functionality."""

    @pytest.fixture
    def normalizer(self) -> PhraseNormalizer:
        """Create a phrase normalizer for testing."""
        return PhraseNormalizer()

    def test_basic_normalization(self, normalizer: PhraseNormalizer) -> None:
        """Test basic text normalization."""

        # Case normalization
        assert normalizer.normalize("HELLO WORLD") == "hello world"
        assert normalizer.normalize("Hello World") == "hello world"

        # Whitespace normalization
        assert normalizer.normalize("hello    world") == "hello world"
        assert normalizer.normalize("  hello world  ") == "hello world"
        assert normalizer.normalize("hello\t\nworld") == "hello world"

        # Empty string handling
        assert normalizer.normalize("") == ""
        assert normalizer.normalize("   ") == ""

    def test_unicode_normalization(self, normalizer: PhraseNormalizer) -> None:
        """Test Unicode character normalization."""

        # Accented characters
        assert normalizer.normalize("café") == "café"
        assert normalizer.normalize("naïve") == "naïve"
        assert normalizer.normalize("résumé") == "résumé"

        # Special quotation marks
        assert normalizer.normalize('"hello"') == "hello"
        assert normalizer.normalize("'hello'") == "'hello'"  # Single quotes preserved
        assert normalizer.normalize("«hello»") == "hello"

        # Various dash types
        assert normalizer.normalize("state-of-the-art") == "state-of-the-art"
        assert normalizer.normalize("state–of–the–art") == "state-of-the-art"
        assert normalizer.normalize("state—of—the—art") == "state-of-the-art"

    def test_punctuation_handling(self, normalizer: PhraseNormalizer) -> None:
        """Test punctuation removal and handling."""

        # Remove most punctuation
        assert normalizer.normalize("hello, world!") == "hello world"
        assert normalizer.normalize("hello; world?") == "hello world"
        assert normalizer.normalize("hello: world.") == "hello world"

        # Preserve hyphens and apostrophes
        assert normalizer.normalize("state-of-the-art") == "state-of-the-art"
        assert normalizer.normalize("don't") == "do not"  # Contractions expanded
        assert normalizer.normalize("it's") == "it is"  # Contractions expanded

        # Various apostrophe types (all should expand contractions)
        assert normalizer.normalize("don't") == "do not"
        assert normalizer.normalize("don't") == "do not"
        assert normalizer.normalize("don`t") == "do not"

    def test_contraction_expansion(self, normalizer: PhraseNormalizer) -> None:
        """Test expansion of English contractions."""

        # Common contractions
        assert normalizer.normalize("don't") == "do not"
        assert normalizer.normalize("won't") == "will not"  # Note: correct contraction expansion
        assert normalizer.normalize("they're") == "they are"
        assert normalizer.normalize("I've") == "i have"
        assert normalizer.normalize("you'll") == "you will"
        assert normalizer.normalize("I'd") == "i would"
        assert normalizer.normalize("I'm") == "i am"

        # With 's (could be "is" or possessive - assuming "is")
        assert normalizer.normalize("it's") == "it is"
        assert normalizer.normalize("that's") == "that is"

    def test_phrase_detection(self, normalizer: PhraseNormalizer) -> None:
        """Test detection of multi-word expressions."""

        # Multi-word phrases
        assert normalizer.is_phrase("hello world")
        assert normalizer.is_phrase("state of the art")
        assert normalizer.is_phrase("ad hoc")

        # Single words
        assert not normalizer.is_phrase("hello")
        assert not normalizer.is_phrase("world")
        assert not normalizer.is_phrase("definition")

        # Hyphenated compounds (should be considered phrases)
        assert normalizer.is_phrase("state-of-the-art")
        assert normalizer.is_phrase("twenty-first")
        assert normalizer.is_phrase("co-worker")

        # Single hyphenated word (borderline case)
        assert normalizer.is_phrase("twenty-one")  # 2 parts = phrase
        assert normalizer.is_phrase("re-do")  # Hyphenated words are considered phrases

    def test_phrase_splitting(self, normalizer: PhraseNormalizer) -> None:
        """Test splitting phrases into component words."""

        # Regular spaces
        assert normalizer.split_phrase("hello world") == ["hello", "world"]
        assert normalizer.split_phrase("state of the art") == ["state", "of", "the", "art"]

        # Hyphens
        assert normalizer.split_phrase("state-of-the-art") == ["state", "of", "the", "art"]
        assert normalizer.split_phrase("twenty-first") == ["twenty", "first"]

        # Mixed
        assert normalizer.split_phrase("twenty-first century") == ["twenty", "first", "century"]

        # Single words
        assert normalizer.split_phrase("hello") == ["hello"]

        # Empty strings
        assert normalizer.split_phrase("") == []
        assert normalizer.split_phrase("   ") == []

    def test_phrase_joining(self, normalizer: PhraseNormalizer) -> None:
        """Test joining words into phrases."""

        # With spaces
        assert normalizer.join_words(["hello", "world"]) == "hello world"
        assert normalizer.join_words(["state", "of", "the", "art"]) == "state of the art"

        # With hyphens
        assert (
            normalizer.join_words(["state", "of", "the", "art"], prefer_hyphens=True)
            == "state-of-the-art"
        )
        assert normalizer.join_words(["twenty", "first"], prefer_hyphens=True) == "twenty-first"

        # Edge cases
        assert normalizer.join_words([]) == ""
        assert normalizer.join_words(["hello"]) == "hello"

    def test_extract_phrases_hyphenated(self, normalizer: PhraseNormalizer) -> None:
        """Test extraction of hyphenated phrases."""

        text = "The state-of-the-art technology was cutting-edge."
        phrases = normalizer.extract_phrases(text)

        # Should find hyphenated compounds
        hyphenated_phrases = [p for p in phrases if "-" in p.text]
        assert len(hyphenated_phrases) >= 2

        # Check specific phrases
        phrase_texts = [p.text for p in phrases]
        assert "state-of-the-art" in phrase_texts
        assert "cutting-edge" in phrase_texts

        # Check metadata
        for phrase in phrases:
            if phrase.text == "state-of-the-art":
                assert phrase.word_count == 4
                assert not phrase.is_idiom  # Hyphenated compounds not marked as idioms

    def test_extract_phrases_quoted(self, normalizer: PhraseNormalizer) -> None:
        """Test extraction of quoted phrases."""

        text = 'The phrase "ad hoc" is Latin. He said "hello world" to everyone.'
        phrases = normalizer.extract_phrases(text)

        # Should find quoted phrases
        quoted_phrases = [p for p in phrases if p.is_idiom]
        assert len(quoted_phrases) >= 2

        # Check specific phrases
        phrase_texts = [p.normalized for p in phrases]
        assert "ad hoc" in phrase_texts
        assert "hello world" in phrase_texts

        # Check that they're marked as idioms
        for phrase in phrases:
            if phrase.normalized == "ad hoc":
                assert phrase.is_idiom
                assert phrase.word_count == 2

    def test_extract_phrases_patterns(self, normalizer: PhraseNormalizer) -> None:
        """Test extraction of common phrase patterns."""

        text = "In order to succeed, we need to take advantage of this opportunity."
        phrases = normalizer.extract_phrases(text)

        # Should find common patterns
        phrase_texts = [p.text for p in phrases]
        assert "in order to" in phrase_texts
        assert "take advantage" in phrase_texts

        # Check idiom marking
        for phrase in phrases:
            if phrase.text == "in order to":
                assert phrase.is_idiom  # Prepositional phrases marked as idioms
            elif phrase.text == "take advantage":
                assert not phrase.is_idiom  # Common collocations not marked as idioms

    def test_edge_cases(self, normalizer: PhraseNormalizer) -> None:
        """Test edge cases and error handling."""

        # None input (should not crash)
        assert normalizer.normalize(None) == ""  # type: ignore

        # Very long strings
        long_text = "word " * 1000
        normalized = normalizer.normalize(long_text)
        assert len(normalized) > 0
        assert not normalized.endswith(" ")  # Should strip trailing space

        # Special characters
        assert normalizer.normalize("@#$%^&*()") == ""
        assert normalizer.normalize("123 456") == "123 456"  # Numbers preserved

        # Multiple spaces and mixed whitespace
        assert normalizer.normalize("a   \t\n   b") == "a b"

    def test_phrase_normalization_consistency(self, normalizer: PhraseNormalizer) -> None:
        """Test that phrase normalization is consistent."""

        # Same phrase with different formatting should normalize identically
        phrases = [
            "hello world",
            "Hello World",
            "HELLO WORLD",
            "  hello   world  ",
            "hello\tworld",
            "hello\nworld",
        ]

        normalized_results = [normalizer.normalize(phrase) for phrase in phrases]

        # All should be identical
        assert all(result == "hello world" for result in normalized_results)

    def test_language_specific_handling(self, normalizer: PhraseNormalizer) -> None:
        """Test handling of different language characteristics."""

        # French phrases with accents
        french_phrase = "vis-à-vis"
        normalized = normalizer.normalize(french_phrase)
        assert normalized == "vis-à-vis"  # Accents preserved

        # French apostrophes
        french_contraction = "l'eau"
        normalized = normalizer.normalize(french_contraction)
        assert "l" in normalized and "eau" in normalized

        # Mixed language text
        mixed = "The café serves café au lait"
        normalized = normalizer.normalize(mixed)
        assert "café" in normalized
        assert "au lait" in normalized


class TestMultiWordExpression:
    """Test MultiWordExpression data structure."""

    def test_creation(self) -> None:
        """Test creation of MultiWordExpression objects."""

        mwe = MultiWordExpression(
            text="hello world",
            normalized="hello world",
            word_count=2,
            is_idiom=False,
            language="en",
            frequency=0.5,
        )

        assert mwe.text == "hello world"
        assert mwe.normalized == "hello world"
        assert mwe.word_count == 2
        assert not mwe.is_idiom
        assert mwe.language == "en"
        assert mwe.frequency == 0.5

    def test_defaults(self) -> None:
        """Test default values in MultiWordExpression."""

        mwe = MultiWordExpression(
            text="test phrase",
            normalized="test phrase",
            word_count=2,
        )

        assert not mwe.is_idiom  # Default False
        assert mwe.language == "en"  # Default English
        assert mwe.frequency == 0.0  # Default 0.0

    def test_idiom_vs_phrase(self) -> None:
        """Test distinction between idioms and regular phrases."""

        # Regular phrase
        phrase = MultiWordExpression(
            text="machine learning",
            normalized="machine learning",
            word_count=2,
            is_idiom=False,
        )
        assert not phrase.is_idiom

        # Idiom
        idiom = MultiWordExpression(
            text="break a leg",
            normalized="break a leg",
            word_count=3,
            is_idiom=True,
        )
        assert idiom.is_idiom
