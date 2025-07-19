"""
Lexicon loading and management package.

Provides comprehensive lexicon loading with support for multiple languages,
phrases, idioms, and expressions with singular meanings.
"""

from __future__ import annotations

from ...constants import Language
from ..constants import LexiconFormat
from .language_loader import LexiconData, LexiconLanguageLoader
from .core import SimpleLexicon, Lexicon
from .sources import LEXICON_SOURCES, LexiconSourceConfig

__all__ = [
    "LexiconLanguageLoader",
    "LexiconData", 
    "SimpleLexicon",
    "Lexicon",
    "LexiconSourceConfig",
    "LEXICON_SOURCES",
    "Language",
    "LexiconFormat",
]