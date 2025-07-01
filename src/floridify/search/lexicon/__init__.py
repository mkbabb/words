"""
Lexicon loading and management package.

Provides comprehensive lexicon loading with support for multiple languages,
phrases, idioms, and expressions with singular meanings.
"""

from __future__ import annotations

from ...constants import Language
from ..constants import LexiconFormat
from .lexicon import LexiconData, LexiconLoader
from .sources import LEXICON_SOURCES, LexiconSourceConfig

__all__ = [
    "LexiconLoader",
    "LexiconData", 
    "LexiconSourceConfig",
    "LEXICON_SOURCES",
    "Language",
    "LexiconFormat",
]