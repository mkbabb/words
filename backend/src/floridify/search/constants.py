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


class SearchMode(Enum):
    """Search modes for API and direct method routing."""

    SMART = "smart"  # Smart cascade: exact → fuzzy → semantic
    EXACT = "exact"  # Only exact matching
    FUZZY = "fuzzy"  # Only fuzzy matching
    SEMANTIC = "semantic"  # Only semantic matching


class FuzzySearchMethod(Enum):
    """Available fuzzy search methods with their characteristics."""

    RAPIDFUZZ = "rapidfuzz"  # C++ optimized fuzzy matching
    JARO_WINKLER = "jaro_winkler"  # Good for names and abbreviations
    SOUNDEX = "soundex"  # Phonetic matching
    LEVENSHTEIN = "levenshtein"  # Classic edit distance
    METAPHONE = "metaphone"  # Advanced phonetic matching
    AUTO = "auto"  # Automatic method selection


# Search scoring constants
DEFAULT_MIN_SCORE = 0.4  # Default minimum score threshold - lowered for better typo tolerance
