"""
Unified text normalization and processing utilities.

Provides comprehensive and fast normalization functions for text processing,
search operations, and linguistic analysis.
"""

from .constants import (
    PUNCTUATION_PATTERN,
    WHITESPACE_PATTERN,
)
from .normalize import (
    basic_lemmatize,
    batch_lemmatize,
    clean_word,
    clear_lemma_cache,
    get_lemma_cache_stats,
    # Validation
    is_valid_word,
    # Lemmatization
    lemmatize_word,
    # Core normalization
    normalize_comprehensive,
    normalize_fast,
    normalize_word,
    # Diacritics
    remove_diacritics,
)
from .phrase import (
    clean_phrase,
    detect_multiword_expressions,
    # Advanced phrase processing
    extract_phrases,
    find_hyphenated_phrases,
    find_quoted_phrases,
    get_phrase_variants,
    # Phrase detection
    is_phrase,
    join_words,
    normalize_phrase,
    split_phrase,
)
# Search functions moved to search/utils.py

# Tokenization functions removed - module no longer exists

__all__ = [
    # Core
    "normalize_comprehensive",
    "normalize_fast",
    "normalize_word",
    "clean_word",
    "is_valid_word",
    "remove_diacritics",
    "lemmatize_word",
    "batch_lemmatize",
    "clear_lemma_cache",
    "get_lemma_cache_stats",
    "basic_lemmatize",
    # Phrase
    "is_phrase",
    "clean_phrase",
    "split_phrase",
    "join_words",
    "extract_phrases",
    "find_hyphenated_phrases",
    "find_quoted_phrases",
    "detect_multiword_expressions",
    "normalize_phrase",
    "get_phrase_variants",
    # Search functions moved to search/utils.py
    # Tokenization functions removed - module no longer exists
    # Patterns
    "WHITESPACE_PATTERN",
    "PUNCTUATION_PATTERN",
]
