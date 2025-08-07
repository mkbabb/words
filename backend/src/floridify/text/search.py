"""
Search-specific text processing utilities.

Functions optimized for search operations and variant generation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from .constants import (
    WHITESPACE_PATTERN,
)
from .normalize import normalize_fast, normalize_word, remove_diacritics


def normalize_for_search(text: str) -> str:
    """
    Normalize text specifically for search operations.

    Aggressive normalization for better matching.

    Args:
        text: Text to normalize

    Returns:
        Search-normalized text
    """
    if not text:
        return ""

    # Use fast normalization
    normalized = normalize_fast(text, lowercase=True)

    # Remove all punctuation for search
    normalized = re.sub(r"[^\w\s]", " ", normalized)

    # Collapse whitespace
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()

    return normalized


def generate_word_variants(word: str) -> list[str]:
    """
    Generate common variants of a word for fuzzy matching.

    Args:
        word: Input word

    Returns:
        List of word variants including the original
    """
    if not word:
        return []

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


def generate_diacritic_variants(text: str) -> set[str]:
    """
    Generate all diacritic variants for improved search coverage.

    Returns both normalized and diacritic-free versions of the input.

    Args:
        text: Input text

    Returns:
        Set of text variants
    """
    if not text:
        return set()

    # Normalize text
    normalized = unicodedata.normalize("NFC", text.strip().lower())
    variants = {normalized}

    # Add diacritic-free variant if different
    without_diacritics = remove_diacritics(normalized)
    if without_diacritics != normalized:
        variants.add(without_diacritics)

    return variants


def get_vocabulary_hash(vocabulary: list[str], max_length: int = 16, is_sorted: bool = False) -> str:
    """
    Generate a stable hash for vocabulary content using deterministic sampling.

    Args:
        vocabulary: List of words to hash
        max_length: Maximum length of hash string to return
        is_sorted: If True, skip sorting step for performance (vocabulary must be pre-sorted)

    Returns:
        Truncated hash string for cache key
    """
    # Use pre-sorted vocabulary if available, otherwise sort
    if is_sorted:
        sorted_vocab = vocabulary
    else:
        sorted_vocab = sorted(vocabulary)

    # Use sample words + length for fast, stable hashing
    vocab_len = len(sorted_vocab)
    sample_size = min(20, vocab_len)
    
    if vocab_len > sample_size:
        # Take samples from beginning and end for better distribution
        half_sample = sample_size // 2
        sample_words = sorted_vocab[:half_sample] + sorted_vocab[-half_sample:]
    else:
        sample_words = sorted_vocab

    # Use join() directly to avoid f-string overhead for large samples
    content = str(vocab_len) + ':' + '|'.join(sample_words)

    return hashlib.sha256(content.encode()).hexdigest()[:max_length]
