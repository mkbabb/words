"""
Phrase detection and processing utilities.

Functions for handling multi-word expressions, compounds, and phrases.
"""

from __future__ import annotations

import re

from .normalize import normalize_fast
from .patterns import (
    COLLOCATION_PATTERN,
    HYPHEN_PATTERN,
    HYPHENATED_PATTERN,
    IDIOM_PATTERN,
    PREPOSITIONAL_PATTERN,
    PUNCTUATION_PATTERN,
    QUOTED_PATTERN,
    WHITESPACE_PATTERN,
)


def is_phrase(text: str) -> bool:
    """
    Check if text contains multiple words (is a phrase).

    Args:
        text: Text to check

    Returns:
        True if text is a phrase
    """
    if not text:
        return False

    # Quick check for spaces
    return " " in text.strip()


def clean_phrase(phrase: str) -> str:
    """
    Clean and normalize a phrase for lookup.

    Args:
        phrase: Input phrase

    Returns:
        Cleaned phrase
    """
    if not phrase:
        return ""

    # Quick normalization
    cleaned = normalize_fast(phrase, lowercase=True)

    # Remove extra punctuation but keep hyphens and apostrophes
    cleaned = re.sub(r"[^\w\s\'-]", " ", cleaned)

    # Normalize spaces
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip()

    return cleaned


def split_phrase(phrase: str) -> list[str]:
    """
    Split a phrase into component words.

    Handles hyphenated words intelligently.

    Args:
        phrase: Phrase to split

    Returns:
        List of component words
    """
    if not phrase:
        return []

    # Clean the phrase first
    phrase = clean_phrase(phrase)

    # Split on spaces and hyphens
    words = re.split(r"[\s\-]+", phrase)

    # Filter out empty strings
    return [w for w in words if w]


def join_words(words: list[str], prefer_hyphens: bool = False) -> str:
    """
    Join words into a phrase intelligently.

    Args:
        words: List of words to join
        prefer_hyphens: Use hyphens instead of spaces

    Returns:
        Joined phrase
    """
    if not words:
        return ""

    # Filter out empty strings
    words = [w for w in words if w]

    if prefer_hyphens:
        return "-".join(words)
    else:
        return " ".join(words)


def find_hyphenated_phrases(text: str) -> list[str]:
    """
    Find all hyphenated phrases in text.

    Args:
        text: Text to search

    Returns:
        List of hyphenated phrases
    """
    if not text:
        return []

    return HYPHENATED_PATTERN.findall(text)


def find_quoted_phrases(text: str) -> list[str]:
    """
    Find all quoted phrases in text.

    Args:
        text: Text to search

    Returns:
        List of quoted phrases
    """
    if not text:
        return []

    return QUOTED_PATTERN.findall(text)


def extract_phrases(
    text: str,
    include_hyphenated: bool = True,
    include_quoted: bool = True,
    include_idioms: bool = True,
    min_words: int = 2,
    max_words: int = 5,
) -> list[str]:
    """
    Extract all types of phrases from text.

    Args:
        text: Text to analyze
        include_hyphenated: Include hyphenated compounds
        include_quoted: Include quoted phrases
        include_idioms: Include common idioms
        min_words: Minimum words in phrase
        max_words: Maximum words in phrase

    Returns:
        List of extracted phrases
    """
    if not text:
        return []

    phrases = []

    # Extract hyphenated phrases
    if include_hyphenated:
        phrases.extend(find_hyphenated_phrases(text))

    # Extract quoted phrases
    if include_quoted:
        quoted = find_quoted_phrases(text)
        # Filter by word count
        for phrase in quoted:
            word_count = len(phrase.split())
            if min_words <= word_count <= max_words:
                phrases.append(phrase)

    # Extract idioms
    if include_idioms:
        idioms = IDIOM_PATTERN.findall(text)
        phrases.extend(idioms)

    # Extract collocations
    collocations = COLLOCATION_PATTERN.findall(text)
    phrases.extend(collocations)

    # Remove duplicates while preserving order
    seen = set()
    unique_phrases = []
    for phrase in phrases:
        normalized = normalize_fast(phrase)
        if normalized not in seen:
            seen.add(normalized)
            unique_phrases.append(phrase)

    return unique_phrases


def detect_multiword_expressions(
    text: str, confidence_threshold: float = 0.7
) -> list[tuple[str, float]]:
    """
    Detect multi-word expressions with confidence scores.

    Args:
        text: Text to analyze
        confidence_threshold: Minimum confidence score

    Returns:
        List of (phrase, confidence) tuples
    """
    if not text:
        return []

    mwes = []

    # Check for idioms (high confidence)
    for match in IDIOM_PATTERN.finditer(text):
        mwes.append((match.group(), 0.95))

    # Check for collocations (high confidence)
    for match in COLLOCATION_PATTERN.finditer(text):
        mwes.append((match.group(), 0.90))

    # Check for prepositional phrases (medium confidence)
    for match in PREPOSITIONAL_PATTERN.finditer(text):
        phrase = match.group()
        # Adjust confidence based on length
        word_count = len(phrase.split())
        confidence = 0.85 - (word_count - 2) * 0.05
        confidence = max(0.6, confidence)
        mwes.append((phrase, confidence))

    # Check for hyphenated compounds (high confidence)
    for match in HYPHENATED_PATTERN.finditer(text):
        mwes.append((match.group(), 0.95))

    # Filter by confidence threshold
    filtered = [(phrase, conf) for phrase, conf in mwes if conf >= confidence_threshold]

    # Remove duplicates and overlaps
    seen = set()
    result = []
    for phrase, conf in sorted(filtered, key=lambda x: x[1], reverse=True):
        normalized = normalize_fast(phrase)
        if normalized not in seen:
            seen.add(normalized)
            result.append((phrase, conf))

    return result


def normalize_phrase(phrase: str, preserve_hyphens: bool = True) -> str:
    """
    Advanced phrase normalization.

    Args:
        phrase: Phrase to normalize
        preserve_hyphens: Keep hyphens in compound words

    Returns:
        Normalized phrase
    """
    if not phrase:
        return ""

    # Start with fast normalization
    normalized = normalize_fast(phrase, lowercase=True)

    if preserve_hyphens:
        # Keep hyphens for compound words
        # But normalize different dash types to standard hyphen
        normalized = HYPHEN_PATTERN.sub("-", normalized)
    else:
        # Replace hyphens with spaces
        normalized = HYPHEN_PATTERN.sub(" ", normalized)

    # Collapse multiple spaces
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)

    return normalized.strip()


def get_phrase_variants(phrase: str) -> list[str]:
    """
    Generate common variants of a phrase.

    Args:
        phrase: Input phrase

    Returns:
        List of phrase variants
    """
    if not phrase:
        return []

    variants = []

    # Original
    variants.append(phrase)

    # Normalized
    normalized = normalize_phrase(phrase)
    if normalized != phrase:
        variants.append(normalized)

    # With spaces instead of hyphens
    space_variant = HYPHEN_PATTERN.sub(" ", phrase)
    if space_variant not in variants:
        variants.append(space_variant)

    # With hyphens instead of spaces (if multi-word)
    if " " in phrase:
        hyphen_variant = phrase.replace(" ", "-")
        if hyphen_variant not in variants:
            variants.append(hyphen_variant)

    # Lowercase variant
    lower = phrase.lower()
    if lower not in variants:
        variants.append(lower)

    # Without punctuation
    no_punct = PUNCTUATION_PATTERN.sub(" ", phrase).strip()
    if no_punct not in variants:
        variants.append(no_punct)

    return variants
