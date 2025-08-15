"""Corpus management module.

Provides unified corpus loading, management, and processing for both
language lexicons and literature texts.
"""

from .constants import LexiconFormat
from .core import Corpus
from .manager import CorpusManager
from .models import CorpusMetadata, LexiconData
from .parser import parse_text_lines
from .sources import LEXICON_SOURCES

__all__ = [
    # Core
    "Corpus",
    "CorpusManager",
    # Models
    "CorpusMetadata",
    "LexiconData",
    # Constants
    "LexiconFormat",
    "LEXICON_SOURCES",
    # Utils
    "parse_text_lines",
]
