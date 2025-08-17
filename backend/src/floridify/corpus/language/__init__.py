"""Language corpus module.

Provides language-specific corpus functionality including loading,
source management, and vocabulary processing.
"""

from .core import LanguageCorpus
from .loader import LanguageCorpusLoader
from .sources import LANGUAGE_CORPUS_SOURCES

__all__ = [
    "LanguageCorpus",
    "LanguageCorpusLoader",
    "LANGUAGE_CORPUS_SOURCES",
]
