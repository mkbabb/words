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
    normalize,
    normalize_comprehensive,
    normalize_fast,
    normalize_simple,
    # Diacritics
    remove_diacritics,
)
from .phrase import is_phrase

# Search functions moved to search/utils.py

# Tokenization functions removed - module no longer exists

__all__ = [
    # Core normalization
    "normalize",
    "normalize_comprehensive",
    "normalize_fast",
    "normalize_simple",
    "batch_normalize",
    "is_valid_word",
    "remove_diacritics",
    # Lemmatization
    "lemmatize_word",
    "batch_lemmatize",
    "clear_lemma_cache",
    "get_lemma_cache_stats",
    # Phrase
    "is_phrase",
    # Patterns
    "WHITESPACE_PATTERN",
    "PUNCTUATION_PATTERN",
]
