"""Word and text normalization utilities for search and lookup.

Provides comprehensive handling of accented characters, diacritics, and
Unicode normalization for improved search coverage across languages.
"""

from __future__ import annotations

import re
import unicodedata

from ..utils.text_utils import normalize_word

# Common diacritic mappings for reference
DIACRITIC_MAPPINGS = {
    # French
    "à": "a",
    "á": "a",
    "â": "a",
    "ã": "a",
    "ä": "a",
    "å": "a",
    "è": "e",
    "é": "e",
    "ê": "e",
    "ë": "e",
    "ì": "i",
    "í": "i",
    "î": "i",
    "ï": "i",
    "ò": "o",
    "ó": "o",
    "ô": "o",
    "õ": "o",
    "ö": "o",
    "ù": "u",
    "ú": "u",
    "û": "u",
    "ü": "u",
    "ý": "y",
    "ÿ": "y",
    "ç": "c",
    "ñ": "n",
    # German
    "ß": "ss",
    # Common ligatures
    "æ": "ae",
    "œ": "oe",
}


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


def remove_diacritics(text: str) -> str:
    """
    Remove diacritics from text while preserving base characters.

    Examples:
        >>> remove_diacritics("à la carte")
        "a la carte"
        >>> remove_diacritics("café")
        "cafe"
        >>> remove_diacritics("naïve")
        "naive"
    """
    # Normalize to NFD (decomposed form)
    nfd_text = unicodedata.normalize("NFD", text)

    # Remove combining marks (diacritics)
    without_diacritics = "".join(char for char in nfd_text if unicodedata.category(char) != "Mn")

    # Normalize back to NFC (composed form)
    return unicodedata.normalize("NFC", without_diacritics)


def normalize_text(text: str) -> str:
    """
    Normalize text for consistent lexicon processing.

    Steps:
    1. Strip whitespace
    2. Convert to lowercase
    3. Unicode NFC normalization
    """
    return unicodedata.normalize("NFC", text.strip().lower())


def generate_diacritic_variants(text: str) -> set[str]:
    """
    Generate all diacritic variants for improved search coverage.

    Returns both normalized and diacritic-free versions of the input.

    Examples:
        >>> generate_diacritic_variants("à la carte")
        {"à la carte", "a la carte"}
        >>> generate_diacritic_variants("café")
        {"café", "cafe"}
    """
    normalized = normalize_text(text)
    variants = {normalized}

    # Add diacritic-free variant if different
    without_diacritics = remove_diacritics(normalized)
    if without_diacritics != normalized:
        variants.add(without_diacritics)

    return variants


def normalize_lexicon_entry(text: str) -> set[str]:
    """
    Comprehensive lexicon entry normalization with variant generation.

    Combines text normalization with diacritic variant generation
    for maximum search coverage.
    """
    return generate_diacritic_variants(text)
