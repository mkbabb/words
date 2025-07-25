"""
Advanced phrase normalization and multi-word expression handling.

Uses modern NLP libraries for robust processing of phrases, idioms, and
multi-word expressions with state-of-the-art text normalization.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..constants import Language
from ..text import (
    TextProcessor,
    extract_phrases,
    is_phrase,
    join_words,
    normalize_text,
    split_phrase,
)


class MultiWordExpression(BaseModel):
    """Represents a multi-word expression or phrase."""

    text: str = Field(..., description="Original text")
    normalized: str = Field(..., description="Normalized form")
    word_count: int = Field(..., gt=0, description="Number of words")
    is_idiom: bool = Field(default=False, description="Whether this is an idiomatic expression")
    language: Language = Field(default=Language.ENGLISH, description="Language code")
    frequency: float = Field(default=0.0, ge=0.0, description="Usage frequency if available")

    model_config = {"frozen": True}


class PhraseNormalizer:
    """
    Advanced phrase normalization using modern NLP libraries.

    Leverages the text processing abstraction layer for robust processing
    of phrases, idioms, and multi-word expressions.
    """

    def __init__(self, language: Language = Language.ENGLISH) -> None:
        """Initialize the advanced phrase normalizer with performance optimizations."""
        self.language = language
        self.text_processor = TextProcessor()

        # Performance optimizations: cache frequently used functions (KISS)
        self._normalize = normalize_text
        self._extract_phrases = extract_phrases
        self._is_phrase = is_phrase
        self._split_phrase = split_phrase
        self._join_words = join_words

    def normalize(self, text: str) -> str:
        """
        Advanced text normalization using modern NLP libraries.

        Args:
            text: Raw input text

        Returns:
            Normalized text suitable for search operations
        """
        if not text:
            return ""

        # Use cached function reference for better performance
        return self._normalize(text, fix_encoding=True, expand_contractions=True)

    def extract_phrases(self, text: str) -> list[MultiWordExpression]:
        """
        Extract multi-word expressions using advanced NLP techniques.

        Args:
            text: Input text to analyze

        Returns:
            List of identified multi-word expressions
        """
        if not text.strip():
            return []

        phrases: list[MultiWordExpression] = []

        # Extract phrases using cached function for performance
        extracted_phrases = self._extract_phrases(text)

        for phrase_text in extracted_phrases:
            normalized = self.normalize(phrase_text)
            if normalized:
                phrases.append(
                    MultiWordExpression(
                        text=phrase_text,
                        normalized=normalized,
                        word_count=len(normalized.split()),
                        is_idiom='"' in text,  # Simple heuristic for quoted phrases
                        language=self.language,
                    )
                )

        return phrases

    def is_phrase(self, text: str) -> bool:
        """
        Determine if text represents a multi-word expression.

        Args:
            text: Text to analyze

        Returns:
            True if text is a multi-word expression
        """
        return self._is_phrase(text)

    def split_phrase(self, phrase: str) -> list[str]:
        """
        Split a phrase into component words.

        Args:
            phrase: Phrase to split

        Returns:
            List of component words
        """
        return self._split_phrase(phrase)

    def join_words(self, words: list[str], prefer_hyphens: bool = False) -> str:
        """
        Join words into a phrase with intelligent separator selection.

        Args:
            words: List of words to join
            prefer_hyphens: Whether to use hyphens instead of spaces

        Returns:
            Joined phrase
        """
        return self._join_words(words, prefer_hyphens)
