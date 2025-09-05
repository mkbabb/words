"""Corpus management module.

Provides unified corpus loading, management, and processing for both
language lexicons and literature texts.
"""

from .core import Corpus
from .language.core import LanguageCorpus
from .literature.core import LiteratureCorpus
from .manager import TreeCorpusManager, get_tree_corpus_manager
from .models import CorpusSource, CorpusType

__all__ = [
    # Core
    "Corpus",
    "CorpusSource",
    "CorpusType",
    # Language
    "LanguageCorpus",
    # Literature
    "LiteratureCorpus",
    # Manager
    "TreeCorpusManager",
    "get_tree_corpus_manager",
]
