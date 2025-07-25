"""Tokenization utilities with fallback implementations."""

from __future__ import annotations

import re

from ..utils.logging import get_logger
from .processor import get_text_processor

logger = get_logger(__name__)


# Pre-compiled regex patterns for performance
WORD_PATTERN = re.compile(r"\b\w+\b")
ADVANCED_WORD_PATTERN = re.compile(r"\b\w+(?:'\w+)?\b|[^\w\s]")
SENTENCE_PATTERN = re.compile(r"[.!?]+\s*")
WHITESPACE_PATTERN = re.compile(r"\s+")


def tokenize(text: str, method: str = "auto") -> list[str]:
    """
    Tokenize text using best available method.

    Args:
        text: Input text to tokenize
        method: Preferred method ("auto", "spacy", "nltk", "regex")

    Returns:
        List of tokens
    """
    if not text.strip():
        return []

    processor = get_text_processor()
    return processor.tokenize(text)


def word_tokenize(text: str) -> list[str]:
    """
    Fast word tokenization with consistent results.

    Args:
        text: Input text

    Returns:
        List of word tokens
    """
    if not text.strip():
        return []

    return WORD_PATTERN.findall(text.lower())


def advanced_word_tokenize(text: str) -> list[str]:
    """
    Advanced word tokenization handling contractions and punctuation.

    Args:
        text: Input text

    Returns:
        List of tokens including contractions
    """
    if not text.strip():
        return []

    return ADVANCED_WORD_PATTERN.findall(text)


def sentence_tokenize(text: str) -> list[str]:
    """
    Basic sentence tokenization.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    if not text.strip():
        return []

    sentences = SENTENCE_PATTERN.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def smart_tokenize(text: str, preserve_contractions: bool = True) -> list[str]:
    """
    Intelligent tokenization with configurable behavior.

    Args:
        text: Input text
        preserve_contractions: Whether to keep contractions intact

    Returns:
        List of tokens
    """
    if not text.strip():
        return []

    # Use advanced pattern if contractions should be preserved
    if preserve_contractions:
        return advanced_word_tokenize(text)

    return word_tokenize(text)


def tokenize_for_search(text: str) -> list[str]:
    """
    Tokenize text optimized for search operations.

    Args:
        text: Input text

    Returns:
        Normalized tokens suitable for search
    """
    if not text.strip():
        return []

    # Use fast regex tokenization for search
    tokens = word_tokenize(text)

    # Filter out very short tokens and normalize
    return [token for token in tokens if len(token) >= 2 and token.isalpha()]
