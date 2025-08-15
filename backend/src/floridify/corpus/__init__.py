"""Corpus management module.

Provides unified corpus loading, management, and processing for both
language lexicons and literature texts.
"""

from .constants import LexiconFormat
from .core import Corpus
from .parser import parse_text_lines
from .sources import LEXICON_SOURCES

__all__ = [
    # Core
    "Corpus",
    # Constants
    "LexiconFormat",
    "LEXICON_SOURCES",
    # Utils
    "parse_text_lines",
]
