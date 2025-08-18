"""Corpus management module.

Provides unified corpus loading, management, and processing for both
language lexicons and literature texts.
"""

from .core import Corpus
from .models import CorpusSource

# TODO: Missing classes that need to be implemented:
# from .language import LANGUAGE_CORPUS_SOURCES, LanguageCorpus, LanguageCorpusLoader
# from .literature import LiteratureCorpus, LiteratureCorpusLoader

__all__ = [
    # Core
    "Corpus",
    "CorpusSource",
    # Language - TODO: Implement these classes
    # "LanguageCorpus",
    # "LanguageCorpusLoader",
    # "LANGUAGE_CORPUS_SOURCES",
    # Literature - TODO: Implement these classes
    # "LiteratureCorpus",
    # "LiteratureCorpusLoader",
]
