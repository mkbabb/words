"""
Search-related constants and enums.

Contains enums for different search methods, embedding levels, fuzzy search
algorithms, and lexicon formats used throughout the search system.
"""

from __future__ import annotations

from enum import Enum


class SearchMethod(Enum):
    """Available search methods with performance characteristics."""

    EXACT = "exact"  # Fastest: ~0.001ms - exact string matching
    PREFIX = "prefix"  # Fast: ~0.001ms - prefix/autocomplete matching  
    FUZZY = "fuzzy"  # Fast: ~0.01ms - typo tolerance, abbreviations
    SEMANTIC = "semantic"  # Slower: ~0.1ms - meaning-based similarity
    AUTO = "auto"  # Automatic method selection based on query


class EmbeddingLevel(Enum):
    """
    Different embedding levels for semantic search operations.
    
    - CHAR: Character-level embeddings (64D) for morphological similarity
    - SUBWORD: Subword-level embeddings (128D) for decomposition  
    - WORD: Word-level embeddings (384D) for semantic relationships
    """

    CHAR = "char"
    SUBWORD = "subword"
    WORD = "word"


class FuzzySearchMethod(Enum):
    """Available fuzzy search methods with their characteristics."""

    RAPIDFUZZ = "rapidfuzz"  # General-purpose, C++ optimized
    LEVENSHTEIN = "levenshtein"  # Classic edit distance
    JARO_WINKLER = "jaro_winkler"  # Good for names and abbreviations
    SOUNDEX = "soundex"  # Phonetic matching
    METAPHONE = "metaphone"  # Advanced phonetic matching
    AUTO = "auto"  # Automatic method selection


class LexiconFormat(Enum):
    """
    Data formats supported for lexicon sources.
    
    These formats define how lexicon data is structured and should be parsed.
    """

    TEXT_LINES = "text_lines"  # Simple text file with one word/phrase per line
    JSON_IDIOMS = "json_idioms"  # JSON file containing idioms and phrases
    FREQUENCY_LIST = "frequency_list"  # Word frequency list with scores
    JSON_DICT = "json_dict"  # JSON dictionary format (key-value pairs)
    JSON_ARRAY = "json_array"  # JSON array of words/phrases
    JSON_GITHUB_API = "json_github_api"  # GitHub API response format
    CSV_IDIOMS = "csv_idioms"  # CSV format with idiom,definition columns
    DICEWARE = "diceware"  # Diceware format (number:word pairs)
    JSON_PHRASAL_VERBS = "json_phrasal_verbs"  # JSON format with phrasal verbs, definitions, examples
    CUSTOM_SCRAPER = "custom_scraper"  # Custom scraper function for dynamic data extraction