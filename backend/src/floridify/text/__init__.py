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
    batch_lemmatize,
    batch_normalize,
    clear_lemma_cache,
    get_lemma_cache_stats,
    # Validation
    is_valid_word,
    # Lemmatization
    lemmatize_word,
    # Core normalization
    normalize_comprehensive,
    normalize_fast,
    # Diacritics
    remove_diacritics,
)
from .phrase import is_phrase

# Search functions moved to search/utils.py

# Tokenization functions removed - module no longer exists

__all__ = [
    # Core
    "normalize_comprehensive",
    "normalize_fast",
    "batch_normalize",
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
    # Search functions moved to search/utils.py
    # Tokenization functions removed - module no longer exists
    # Patterns
    "WHITESPACE_PATTERN",
    "PUNCTUATION_PATTERN",
]
