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
    JSON_PHRASAL_VERBS = "json_phrasal_verbs"  # JSON format with phrasal verbs, definitions
    CUSTOM_SCRAPER = "custom_scraper"  # Custom scraper function for dynamic data extraction


# ============================================================================
# SEMANTIC SEARCH CONSTANTS
# ============================================================================

# Model Configuration
DEFAULT_SENTENCE_MODEL = "all-MiniLM-L6-v2"  # 384D embeddings, fast and accurate
SENTENCE_EMBEDDING_DIM = 384  # Expected dimension for all-MiniLM-L6-v2

# TF-IDF Configuration
CHAR_NGRAM_RANGE = (2, 5)  # Character n-grams for typo tolerance
SUBWORD_NGRAM_RANGE = (1, 3)  # Subword units for morphology
WORD_NGRAM_RANGE = (1, 2)  # Unigrams and bigrams for semantic meaning
MAX_FEATURES = 50000  # Maximum features per vectorizer
CHAR_MAX_FEATURES_RATIO = 4  # Divisor for character-level features
SUBWORD_MAX_FEATURES_RATIO = 2  # Divisor for subword-level features

# Search Weights (must sum to 1.0)
SENTENCE_TRANSFORMER_WEIGHT = 0.7  # Primary semantic understanding
CHAR_TFIDF_WEIGHT = 0.1  # Morphological similarity
SUBWORD_TFIDF_WEIGHT = 0.1  # Subword decomposition
WORD_TFIDF_WEIGHT = 0.1  # Word-level patterns

# Subword Generation Parameters
MIN_WORD_LENGTH_FOR_SUBWORDS = 3  # Don't split words shorter than this
SUBWORD_PREFIX_LENGTH_SHORT = 3  # Short prefix/suffix length
SUBWORD_PREFIX_LENGTH_LONG = 4  # Long prefix/suffix length
MIN_WORD_LENGTH_FOR_LONG_PREFIX = 6  # When to use longer prefixes
MIN_WORD_LENGTH_FOR_SLIDING_WINDOW = 8  # When to use sliding window
SLIDING_WINDOW_SIZE = 4  # Size of sliding window for long words

# Cache Configuration
DEFAULT_TTL_HOURS = 168.0  # 1 week default cache TTL
DEFAULT_CACHE_MAX_SIZE = 100  # Maximum number of cached corpora
DEFAULT_CLEANUP_INTERVAL = 300.0  # Cleanup interval in seconds

# Search Configuration
DEFAULT_MAX_RESULTS = 20  # Default maximum search results
SEARCH_EXPANSION_FACTOR = 2  # Multiply max_results for initial retrieval
MIN_SCORE_DEFAULT = 0.6  # Default minimum similarity score

# FAISS Configuration
L2_DISTANCE_NORMALIZATION = 2  # Divisor for L2 distance to similarity conversion

# Batch Processing
EMBEDDING_BATCH_SIZE = 512  # Batch size for sentence transformer encoding
SHOW_PROGRESS_BAR = False  # Whether to show progress during encoding
