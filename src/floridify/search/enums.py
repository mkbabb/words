"""Enums for search algorithms and configuration values."""

from __future__ import annotations

from enum import Enum


class SearchMethod(Enum):
    """Available search methods."""

    HYBRID = "hybrid"
    VECTORIZED = "vectorized"
    RAPIDFUZZ = "rapidfuzz"
    PREFIX = "prefix"
    SEMANTIC = "semantic"
    TRADITIONAL = "traditional"


class VectorSearchMethod(Enum):
    """Vectorized search method types."""

    CHARACTER = "character"
    SUBWORD = "subword"
    TFIDF = "tfidf"
    FUSION = "fusion"


class TraditionalSearchMethod(Enum):
    """Traditional fuzzy search method types."""

    RAPIDFUZZ = "rapidfuzz"
    JARO_WINKLER = "jaro_winkler"
    VSCODE = "vscode"
    PHONETIC = "phonetic"
    LEVENSHTEIN = "levenshtein"


class IndexType(Enum):
    """Index data structure types."""

    TRIE = "trie"
    BK_TREE = "bk_tree"
    NGRAM_BIGRAM = "bigram"
    NGRAM_TRIGRAM = "trigram"
    VECTOR_CHARACTER = "vector_character"
    VECTOR_SUBWORD = "vector_subword"
    VECTOR_TFIDF = "vector_tfidf"
    VECTOR_COMBINED = "vector_combined"


class LanguageCode(Enum):
    """Supported language codes."""

    ENGLISH = "en"
    FRENCH = "fr"
    ALL = "all"


class LexiconSource(Enum):
    """Lexicon data source types."""

    ENGLISH_COMMON = "english_common"
    ENGLISH_COMPREHENSIVE = "english_comprehensive"
    FRENCH_COMMON = "french_common"
    FRENCH_CONJUGATED = "french_conjugated"
    ACADEMIC = "academic"
    SCIENTIFIC = "scientific"
    PROPER_NOUNS = "proper"
    FRENCH_PHRASES = "french"
    DATABASE = "database"


class CacheType(Enum):
    """Cache file types."""

    INDEX = "index"
    VECTORS = "vectors"
    LEXICONS = "lexicons"
    EMBEDDINGS = "embeddings"


class EmbeddingType(Enum):
    """Types of embeddings used in vectorized search."""

    CHARACTER = "character"
    SUBWORD = "subword"
    TFIDF = "tfidf"
    COMBINED = "combined"


class ScoringMethod(Enum):
    """Scoring methods for search results."""

    EXACT_MATCH = "exact"
    EDIT_DISTANCE = "edit_distance"
    COSINE_SIMILARITY = "cosine"
    WEIGHTED_RATIO = "weighted_ratio"
    JARO_WINKLER = "jaro_winkler"
    VSCODE_SEQUENCE = "vscode_sequence"
    PHONETIC_MATCH = "phonetic"
    NGRAM_OVERLAP = "ngram_overlap"


class PhoneticAlgorithm(Enum):
    """Phonetic matching algorithms."""

    SOUNDEX = "soundex"
    METAPHONE = "metaphone"
    DOUBLE_METAPHONE = "double_metaphone"


class SearchResultStatus(Enum):
    """Search result status types."""

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    ERROR = "error"
    TIMEOUT = "timeout"
    CACHE_HIT = "cache_hit"


class FileFormat(Enum):
    """Supported file formats for caching."""

    PICKLE = ".pkl"
    JSON = ".json"
    FAISS = ".faiss"
    TEXT = ".txt"
    BINARY = ".bin"
