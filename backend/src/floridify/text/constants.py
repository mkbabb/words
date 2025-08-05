"""
Constants for text processing.

Contains lemmatization rules, diacritic mappings, and other constants
used throughout the text processing system.
"""

from __future__ import annotations

# Common diacritic mappings for reference
DIACRITIC_MAPPINGS = {
    # French
    "à": "a",
    "á": "a",
    "â": "a",
    "ã": "a",
    "ä": "a",
    "å": "a",
    "è": "e",
    "é": "e",
    "ê": "e",
    "ë": "e",
    "ì": "i",
    "í": "i",
    "î": "i",
    "ï": "i",
    "ò": "o",
    "ó": "o",
    "ô": "o",
    "õ": "o",
    "ö": "o",
    "ù": "u",
    "ú": "u",
    "û": "u",
    "ü": "u",
    "ý": "y",
    "ÿ": "y",
    "ç": "c",
    "ñ": "n",
    # German
    "ß": "ss",
    # Common ligatures
    "æ": "ae",
    "œ": "oe",
}

# Lemmatization suffix rules
SUFFIX_RULES = {
    # Plural forms
    "ies": "y",
    "ves": "f",
    "oes": "o",
    "ses": "s",
    "xes": "x",
    "zes": "z",
    "ches": "ch",
    "shes": "sh",
    "men": "man",
    "eet": "oot",
    # Verb forms
    "ing": "",
    "ed": "",
    "ied": "y",
    # Comparative/superlative
    "er": "",
    "est": "",
    "ier": "y",
    "iest": "y",
    # Adverbs
    "ly": "",
    "ily": "y",
    # Simple plural
    "s": "",
}

# Subword generation constants
MIN_WORD_LENGTH_FOR_SUBWORDS = 3
SUBWORD_PREFIX_LENGTH_SHORT = 3
SUBWORD_PREFIX_LENGTH_LONG = 4
MIN_WORD_LENGTH_FOR_LONG_PREFIX = 6
MIN_WORD_LENGTH_FOR_SLIDING_WINDOW = 8
SLIDING_WINDOW_SIZE = 4

# Article patterns for normalization (language-specific)
ARTICLES = {
    "english": ["the", "a", "an"],
    "french": ["le", "la", "les", "un", "une", "des"],
    "german": ["der", "die", "das", "ein", "eine"],
    "spanish": ["el", "la", "los", "las", "un", "una"],
    "italian": ["il", "lo", "la", "gli", "le", "un", "una"],
}

# All articles combined for pattern matching
ALL_ARTICLES = []
for articles in ARTICLES.values():
    ALL_ARTICLES.extend(articles)
