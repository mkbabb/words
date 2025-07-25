"""Text processing utilities with spacy fallbacks."""

from .normalizer import basic_lemmatize, lemmatize_word, normalize_text
from .processor import ProcessingResult, TextProcessor
from .tokenizer import sentence_tokenize, tokenize, word_tokenize
from .utils import (
    calculate_mwe_confidence,
    detect_multiword_expressions,
    extract_phrases,
    find_hyphenated_phrases,
    find_quoted_phrases,
    get_phrase_variants,
    is_compound_word,
    is_phrase,
    join_words,
    normalize_phrase,
    phrase_word_count,
    split_phrase,
)

__all__ = [
    "TextProcessor",
    "ProcessingResult",
    "tokenize",
    "sentence_tokenize",
    "word_tokenize",
    "normalize_text",
    "lemmatize_word",
    "basic_lemmatize",
    "is_phrase",
    "split_phrase",
    "join_words",
    "extract_phrases",
    "find_hyphenated_phrases",
    "find_quoted_phrases",
    "detect_multiword_expressions",
    "calculate_mwe_confidence",
    "get_phrase_variants",
    "normalize_phrase",
    "phrase_word_count",
    "is_compound_word",
]
