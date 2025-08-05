"""
Search-specific text processing utilities.

Functions optimized for search operations and variant generation.
"""

from __future__ import annotations

import hashlib
import unicodedata

from .constants import (
    MIN_WORD_LENGTH_FOR_LONG_PREFIX,
    MIN_WORD_LENGTH_FOR_SLIDING_WINDOW,
    MIN_WORD_LENGTH_FOR_SUBWORDS,
    SLIDING_WINDOW_SIZE,
    SUBWORD_PREFIX_LENGTH_LONG,
    SUBWORD_PREFIX_LENGTH_SHORT,
)
from .normalize import normalize_fast, normalize_word, remove_diacritics
from .patterns import WHITESPACE_PATTERN


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
    import re
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


def normalize_lexicon_entry(text: str) -> set[str]:
    """
    Comprehensive lexicon entry normalization with variant generation.
    
    Combines text normalization with diacritic variant generation
    for maximum search coverage.
    
    Args:
        text: Lexicon entry text
        
    Returns:
        Set of normalized variants
    """
    return generate_diacritic_variants(text)


# Semantic search utilities



def create_subword_text(word: str) -> str:
    """
    Create subword representation for a word or phrase.
    
    Used for semantic search embeddings.
    
    Args:
        word: Word or phrase to process
        
    Returns:
        Space-separated subword units
    """
    # For phrases, split into words first
    if " " in word:
        words = word.split()
        subwords = []
        for w in words:
            subwords.extend(split_word_into_subwords(w))
        return " ".join(subwords)
    else:
        return " ".join(split_word_into_subwords(word))


def split_word_into_subwords(word: str) -> list[str]:
    """
    Split a word into subword units using configurable parameters.
    
    This function creates multiple representations of a word:
    - The full word itself
    - Prefixes and suffixes of varying lengths
    - Sliding window subwords for long words
    
    Args:
        word: Single word to split
        
    Returns:
        List of subword units
    """
    if len(word) <= MIN_WORD_LENGTH_FOR_SUBWORDS:
        return [word]
    
    subwords = [word]  # Include full word
    
    # Add short prefixes and suffixes
    if len(word) >= SUBWORD_PREFIX_LENGTH_SHORT + 1:
        subwords.append(word[:SUBWORD_PREFIX_LENGTH_SHORT])  # Prefix
        subwords.append(word[-SUBWORD_PREFIX_LENGTH_SHORT:])  # Suffix
    
    # Add longer prefixes and suffixes for longer words
    if len(word) >= MIN_WORD_LENGTH_FOR_LONG_PREFIX:
        subwords.append(word[:SUBWORD_PREFIX_LENGTH_LONG])  # Longer prefix
        subwords.append(word[-SUBWORD_PREFIX_LENGTH_LONG:])  # Longer suffix
    
    # Add sliding window subwords for long words
    if len(word) >= MIN_WORD_LENGTH_FOR_SLIDING_WINDOW:
        for i in range(len(word) - SLIDING_WINDOW_SIZE + 1):
            subwords.append(word[i : i + SLIDING_WINDOW_SIZE])
    
    return subwords


def get_vocabulary_hash(vocabulary: list[str], max_length: int = 16) -> str:
    """
    Generate a hash of vocabulary for cache validation.
    
    Args:
        vocabulary: List of words to hash
        max_length: Maximum length of hash string to return
        
    Returns:
        Truncated hash string for cache key
    """
    vocab_str = "|".join(sorted(vocabulary))
    full_hash = hashlib.sha256(vocab_str.encode()).hexdigest()
    return full_hash[:max_length]