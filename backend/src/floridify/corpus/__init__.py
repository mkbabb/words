"""Corpus management module.

Provides unified corpus loading, management, and processing for both
language lexicons and literature texts.
"""

from .core import Corpus, CorpusSource
from .language import LANGUAGE_CORPUS_SOURCES, LanguageCorpus, LanguageCorpusLoader
from .literature import LiteratureCorpus, LiteratureCorpusLoader

__all__ = [
    # Core
    "Corpus",
    "CorpusSource",
    # Language
    "LanguageCorpus",
    "LanguageCorpusLoader",
    "LANGUAGE_CORPUS_SOURCES",
    # Literature
    "LiteratureCorpus",
    "LiteratureCorpusLoader",
]
