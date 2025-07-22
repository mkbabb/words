"""Text processing utilities with spacy fallbacks."""

from .processor import TextProcessor, ProcessingResult
from .tokenizer import tokenize, sentence_tokenize, word_tokenize
from .normalizer import normalize_text, lemmatize_word, basic_lemmatize
from .utils import (
    is_phrase, 
    split_phrase, 
    join_words, 
    extract_phrases,
    find_hyphenated_phrases,
    find_quoted_phrases,
    detect_multiword_expressions,
    calculate_mwe_confidence,
    get_phrase_variants,
    normalize_phrase,
    phrase_word_count,
    is_compound_word
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