"""
Consolidated regex patterns for text processing.

All pre-compiled patterns used throughout the normalization system.
"""

import re

# Basic text patterns
WHITESPACE_PATTERN = re.compile(r"\s+")
PUNCTUATION_PATTERN = re.compile(r"[^\w\s\'-]", re.UNICODE)
WORD_BOUNDARY_PATTERN = re.compile(r"\b")

# Word extraction patterns
WORD_PATTERN = re.compile(r"\b\w+\b")
ADVANCED_WORD_PATTERN = re.compile(r"\b\w+(?:'\w+)?\b|[^\w\s]")
ALPHANUM_PATTERN = re.compile(r"[a-zA-Z0-9]", re.UNICODE)

# Sentence patterns
SENTENCE_PATTERN = re.compile(r"[.!?]+\s*")
SENTENCE_END_PATTERN = re.compile(r"[.!?]+$")

# Hyphenation and compound patterns
HYPHEN_PATTERN = re.compile(r"[-–—]")
HYPHENATED_PATTERN = re.compile(r"\b\w+(?:[-–—]\w+){1,4}\b", re.UNICODE)
COMPOUND_PATTERN = re.compile(r"\b\w+(?:[\s-]\w+)+\b", re.UNICODE)

# Quote patterns
QUOTED_PATTERN = re.compile(r'["\'\'""\«]([^"\'\'""\»]+)["\'\'""\»]')
SMART_QUOTE_PATTERN = re.compile(r"[''" "]")

# Multi-word expression patterns
IDIOM_PATTERN = re.compile(
    r"\b(?:out of|in order to|as well as|in spite of|on behalf of|"
    r"at least|at most|by means of|for the sake of|in addition to|"
    r"in case of|in front of|in lieu of|in place of|in terms of|"
    r"on account of|on top of|with regard to|with respect to)\b",
    re.IGNORECASE,
)

COLLOCATION_PATTERN = re.compile(
    r"\b(?:strongly|highly|deeply|fully|completely|absolutely|"
    r"entirely|totally|utterly|thoroughly)\s+"
    r"(?:recommend|suggest|believe|agree|disagree|support|"
    r"oppose|endorse|approve|condemn)\b",
    re.IGNORECASE,
)

PREPOSITIONAL_PATTERN = re.compile(
    r"\b(?:in|on|at|by|for|with|under|over|through|across|"
    r"between|among|within|without|beneath|beside|beyond)\s+"
    r"(?:the|a|an)?\s*\w+(?:\s+\w+)*\b",
    re.IGNORECASE,
)

# Markdown patterns
MARKDOWN_BOLD_PATTERN = re.compile(r"\*\*(.*?)\*\*")
MARKDOWN_ITALIC_PATTERN = re.compile(r"\*(.*?)\*")
MARKDOWN_CODE_PATTERN = re.compile(r"`(.*?)`")
MARKDOWN_LINK_PATTERN = re.compile(r"\[(.*?)\]\(.*?\)")
MARKDOWN_HEADING_PATTERN = re.compile(r"^#+\s+", re.MULTILINE)

# Special character patterns
UNICODE_DASH_PATTERN = re.compile(r"[–—]")
UNICODE_QUOTE_PATTERN = re.compile(r"[''" "]")
MULTIPLE_SPACE_PATTERN = re.compile(r"\s{2,}")
LEADING_TRAILING_SPACE_PATTERN = re.compile(r"^\s+|\s+$")

# Article patterns for normalization
ARTICLE_PATTERN = re.compile(
    r"^(the|a|an|le|la|les|der|die|das|el|la|los|las|il|lo|gli)\s+", re.IGNORECASE
)

# Number patterns
NUMBER_PATTERN = re.compile(r"\d+")
ORDINAL_PATTERN = re.compile(r"\d+(st|nd|rd|th)\b", re.IGNORECASE)

# URL and email patterns (for cleaning)
URL_PATTERN = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

# List item patterns (for parsing)
NUMBERED_LIST_PATTERN = re.compile(r"^\s*(\d+\.?|\d+\))\s+")
BULLET_LIST_PATTERN = re.compile(r"^\s*[-*•·○□▪▫◦‣⁃]\s+")

# Contraction patterns
CONTRACTION_PATTERN = re.compile(r"\b\w+'\w+\b")
POSSESSIVE_PATTERN = re.compile(r"\b\w+'s\b")

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
    }
)
