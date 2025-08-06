"""
Corpus loading and management package.

Provides comprehensive corpus loading with support for multiple languages,
phrases, idioms, and expressions with MongoDB-based caching.
"""

from __future__ import annotations

from ...models.definition import Language
from .constants import LexiconFormat
from .core import Corpus

# Cache functionality removed - using unified caching system
from .language_loader import CorpusLanguageLoader, LexiconData
from .manager import CorpusManager, get_corpus_manager
from .sources import LEXICON_SOURCES, LexiconSourceConfig

__all__ = [
    # Core corpus
    "Corpus",
    # Corpus managers
    "CorpusManager",
    "get_corpus_manager",
    # Corpus loaders
    "CorpusLanguageLoader", 
    "LexiconData",
    # Configuration
    "LexiconSourceConfig",
    "LEXICON_SOURCES",
    "Language",
    "LexiconFormat",
]
