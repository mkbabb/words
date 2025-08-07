"""
Phrase detection and processing utilities.

Functions for handling multi-word expressions, compounds, and phrases.
"""

from __future__ import annotations

import re

from .constants import (
    WHITESPACE_PATTERN,
)
from .normalize import normalize_fast


def is_phrase(text: str) -> bool:
    """
    Check if text contains multiple words (is a phrase).

    Args:
        text: Text to check

    Returns:
        True if text contains multiple words
    """
    if not text:
        return False

    # Check for whitespace (simple phrase detection)
    normalized = text.strip()
    return len(normalized.split()) > 1


def clean_phrase(phrase: str) -> str:
    """
    Clean a phrase by normalizing whitespace and removing excess punctuation.

    Args:
        phrase: Phrase to clean

    Returns:
        Cleaned phrase
    """
    if not phrase:
        return ""

    # Basic normalization
    cleaned = normalize_fast(phrase)

    # Normalize whitespace
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip()

    return cleaned


def split_phrase(phrase: str) -> list[str]:
    """
    Split phrase into individual words.

    Args:
        phrase: Phrase to split

    Returns:
        List of words
    """
    if not phrase:
        return []

    cleaned = clean_phrase(phrase)
    return cleaned.split() if cleaned else []


def join_words(words: list[str], separator: str = " ") -> str:
    """
    Join words into a phrase.

    Args:
        words: List of words
        separator: Separator to use

    Returns:
        Joined phrase
    """
    if not words:
        return ""

    return separator.join(str(word).strip() for word in words if word)


def normalize_phrase(phrase: str) -> str:
    """
    Normalize a phrase for consistent processing.

    Args:
        phrase: Phrase to normalize

    Returns:
        Normalized phrase
    """
    return clean_phrase(phrase)


def get_phrase_variants(phrase: str) -> set[str]:
    """
    Generate variants of a phrase for search.

    Args:
        phrase: Input phrase

    Returns:
        Set of phrase variants
    """
    if not phrase:
        return set()

    variants = {phrase}

    # Add cleaned version
    cleaned = clean_phrase(phrase)
    if cleaned and cleaned != phrase:
        variants.add(cleaned)

    # Add lowercase version
    lower = phrase.lower()
    if lower != phrase:
        variants.add(lower)

    return variants


# Legacy functions for compatibility - simplified implementations
def extract_phrases(text: str) -> list[str]:
    """Extract phrases from text (simplified)."""
    if not text:
        return []
    return [phrase.strip() for phrase in text.split(".") if phrase.strip()]


def find_hyphenated_phrases(text: str) -> list[str]:
    """Find hyphenated phrases (simplified)."""
    if not text:
        return []
    # Simple hyphen detection
    return re.findall(r"\b\w+(?:-\w+)+\b", text)


def find_quoted_phrases(text: str) -> list[str]:
    """Find quoted phrases (simplified)."""
    if not text:
        return []
    # Simple quote detection
    return re.findall(r'["\']([^"\']+)["\']', text)


def detect_multiword_expressions(text: str) -> list[str]:
    """Detect multiword expressions (simplified)."""
    if not text:
        return []
    # Return phrases with 2+ words
    words = text.split()
    expressions = []
    for i in range(len(words) - 1):
        if len(words[i]) > 2 and len(words[i + 1]) > 2:
            expressions.append(f"{words[i]} {words[i + 1]}")
    return expressions
