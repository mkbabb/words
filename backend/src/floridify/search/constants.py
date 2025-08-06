"""Search-related constants and enums."""

from __future__ import annotations

from enum import Enum


class SearchMethod(Enum):
    """Available search methods with performance characteristics."""

    EXACT = "exact"  # Fastest: ~0.001ms - exact string matching
    PREFIX = "prefix"  # Fast: ~0.001ms - prefix/autocomplete matching
    FUZZY = "fuzzy"  # Fast: ~0.01ms - typo tolerance, abbreviations
    SEMANTIC = "semantic"  # Slower: ~0.1ms - meaning-based similarity
    AUTO = "auto"  # Automatic method selection based on query


class FuzzySearchMethod(Enum):
    """Available fuzzy search methods with their characteristics."""

    RAPIDFUZZ = "rapidfuzz"  # General-purpose, C++ optimized
    LEVENSHTEIN = "levenshtein"  # Classic edit distance
    JARO_WINKLER = "jaro_winkler"  # Good for names and abbreviations
    SOUNDEX = "soundex"  # Phonetic matching
    METAPHONE = "metaphone"  # Advanced phonetic matching
    AUTO = "auto"  # Automatic method selection


# Search scoring constants
DEFAULT_MIN_SCORE = 0.6  # Default minimum score threshold for search results
