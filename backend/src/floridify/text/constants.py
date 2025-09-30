"""Consolidated constants and patterns for text processing.

Contains regex patterns, lemmatization rules, and other constants
used throughout the text processing system.
"""

from __future__ import annotations

import re

# Basic text patterns
WHITESPACE_PATTERN = re.compile(r"\s+")
PUNCTUATION_PATTERN = re.compile(r"[^\w\s\'-]", re.UNICODE)
MULTIPLE_SPACE_PATTERN = re.compile(r"\s{2,}")

# Article patterns for normalization
ARTICLE_PATTERN = re.compile(
    r"^(the|a|an|le|la|les|der|die|das|el|la|los|las|il|lo|gli)\s+",
    re.IGNORECASE,
)

# ======================================================================
# Performance-optimized regex patterns (pre-compiled for speed)
# ======================================================================

# Fast punctuation removal (used in normalize_fast)
FAST_PUNCTUATION_PATTERN = re.compile(r"[^\w\s\'-]")

# Word validation patterns
ALPHABETIC_PATTERN = re.compile(r"[a-zA-Z]")
NON_ALPHABETIC_PATTERN = re.compile(r"[^a-zA-Z\-'\s]")

# Combined cleanup pattern for single-pass optimization
COMBINED_CLEANUP_PATTERN = re.compile(r"[^\w\s\'-]+|\s+")

# Character translation tables
UNICODE_TO_ASCII = str.maketrans(
    {
        # Dashes
        "—": "-",  # em dash
        "–": "-",  # en dash
        "‒": "-",  # figure dash
        "―": "-",  # horizontal bar
        # Quotes
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote (also used as apostrophe)
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "‚": "'",  # single low quote
        "„": '"',  # double low quote
        # Apostrophes
        "´": "'",  # acute accent (sometimes misused as apostrophe)
        "`": "'",  # grave accent (sometimes misused as apostrophe)
        # Spaces
        "\xa0": " ",  # non-breaking space
        "\u2009": " ",  # thin space
        "\u200a": " ",  # hair space
    },
)

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

# Subword generation constants (for search)
MIN_WORD_LENGTH_FOR_SUBWORDS = 3
SUBWORD_PREFIX_LENGTH_SHORT = 3
SUBWORD_PREFIX_LENGTH_LONG = 4
MIN_WORD_LENGTH_FOR_LONG_PREFIX = 6
MIN_WORD_LENGTH_FOR_SLIDING_WINDOW = 8
SLIDING_WINDOW_SIZE = 4

# Common diacritic mappings
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
