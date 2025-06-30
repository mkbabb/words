"""Word normalization utilities for search and lookup."""

from __future__ import annotations

import re
import unicodedata


def normalize_word(word: str) -> str:
    """Normalize a word for search and lookup.

    Args:
        word: Input word to normalize

    Returns:
        Normalized word
    """
    if not word:
        return ""

    # Convert to lowercase
    normalized = word.lower()

    # Remove extra whitespace and normalize spaces
    normalized = re.sub(r"\s+", " ", normalized.strip())

    # Normalize unicode characters (NFD form to separate accents)
    normalized = unicodedata.normalize("NFD", normalized)

    # Remove diacritics/accents but keep the base characters
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))

    # Convert back to composed form
    normalized = unicodedata.normalize("NFC", normalized)

    return normalized


def generate_word_variants(word: str) -> list[str]:
    """Generate common variants of a word for fuzzy matching.

    Args:
        word: Input word

    Returns:
        List of word variants including the original
    """
    variants = []
    normalized = normalize_word(word)

    # Add the normalized form
    if normalized:
        variants.append(normalized)

    # Add original if different from normalized
    if word.lower() != normalized:
        variants.append(word.lower())

    # Add capitalized versions if the original was capitalized
    if word and word[0].isupper():
        variants.append(word.lower())
        if normalized != word.lower():
            variants.append(normalized)

    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for variant in variants:
        if variant and variant not in seen:
            seen.add(variant)
            unique_variants.append(variant)

    return unique_variants


def is_phrase(word: str) -> bool:
    """Check if the input contains multiple words (is a phrase).

    Args:
        word: Input to check

    Returns:
        True if the input is a phrase (contains spaces)
    """
    return " " in word.strip()


def clean_phrase(phrase: str) -> str:
    """Clean and normalize a phrase for lookup.

    Args:
        phrase: Input phrase

    Returns:
        Cleaned phrase
    """
    if not phrase:
        return ""

    # Normalize the phrase
    cleaned = normalize_word(phrase)

    # Remove extra punctuation but keep hyphens and apostrophes
    cleaned = re.sub(r"[^\w\s\'-]", " ", cleaned)

    # Normalize spaces again after punctuation removal
    cleaned = re.sub(r"\s+", " ", cleaned.strip())

    return cleaned
