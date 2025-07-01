"""
Model-related constants and enums.

Contains enums for data models, dictionary structures, and literature sources.
"""

from __future__ import annotations

from enum import Enum


class WordType(Enum):
    """Enumeration for part of speech types."""

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"
    DETERMINER = "determiner"
    PHRASE = "phrase"
    OTHER = "other"


class LiteratureSourceType(Enum):
    """Enumeration for different types of literature sources."""

    BOOK = "book"
    ARTICLE = "article"
    DOCUMENT = "document"