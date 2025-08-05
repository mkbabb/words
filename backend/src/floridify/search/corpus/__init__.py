"""
Corpus loading and management package.

Provides comprehensive corpus loading with support for multiple languages,
phrases, idioms, and expressions with MongoDB-based caching.
"""

from __future__ import annotations

from ...models.definition import Language
from ..constants import LexiconFormat
from .cache import CorpusCache, CorpusEntry, CorpusMetadata, get_corpus_cache
from .language_loader import CorpusLanguageLoader, LexiconData
from .sources import LEXICON_SOURCES, LexiconSourceConfig

__all__ = [
    # Corpus loaders
    "CorpusLanguageLoader",
    "LexiconData",
    # Corpus cache
    "CorpusCache",
    "CorpusEntry",
    "CorpusMetadata",
    "get_corpus_cache",
    # Configuration
    "LexiconSourceConfig",
    "LEXICON_SOURCES",
    "Language",
    "LexiconFormat",
]
