"""
Unified text normalization and processing utilities.

Provides comprehensive and fast normalization functions for text processing,
search operations, and linguistic analysis.
"""

from .normalize import (
    basic_lemmatize,
    batch_lemmatize,
    clean_word,
    clear_lemma_cache,
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
from .patterns import (
    ADVANCED_WORD_PATTERN,
    COLLOCATION_PATTERN,
    COMPOUND_PATTERN,
    HYPHENATED_PATTERN,
    IDIOM_PATTERN,
    PREPOSITIONAL_PATTERN,
    PUNCTUATION_PATTERN,
    QUOTED_PATTERN,
    SENTENCE_PATTERN,
    # Regex patterns
    WHITESPACE_PATTERN,
    WORD_PATTERN,
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
from .search import (
    # Semantic search
    create_subword_text,
    generate_diacritic_variants,
    generate_word_variants,
    get_vocabulary_hash,
    # Search utilities
    normalize_for_search,
    normalize_lexicon_entry,
    split_word_into_subwords,
)
from .tokenizer import (
    advanced_word_tokenize,
    sentence_tokenize,
    smart_tokenize,
    # Tokenization
    tokenize,
    tokenize_for_search,
    word_tokenize,
)

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
    # Search
    "normalize_for_search",
    "generate_word_variants",
    "generate_diacritic_variants",
    "normalize_lexicon_entry",
    "create_subword_text",
    "split_word_into_subwords",
    "get_vocabulary_hash",
    # Tokenization
    "tokenize",
    "word_tokenize",
    "sentence_tokenize",
    "advanced_word_tokenize",
    "smart_tokenize",
    "tokenize_for_search",
    # Patterns
    "WHITESPACE_PATTERN",
    "PUNCTUATION_PATTERN",
    "WORD_PATTERN",
    "ADVANCED_WORD_PATTERN",
    "SENTENCE_PATTERN",
    "HYPHENATED_PATTERN",
    "QUOTED_PATTERN",
    "COMPOUND_PATTERN",
    "IDIOM_PATTERN",
    "COLLOCATION_PATTERN",
    "PREPOSITIONAL_PATTERN",
]
