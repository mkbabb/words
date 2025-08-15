"""Corpus loaders module.

Provides specialized loaders for different corpus types.
"""

from .language import CorpusLanguageLoader
from .literature import LiteratureCorpusLoader

__all__ = [
    "CorpusLanguageLoader",
    "LiteratureCorpusLoader",
]
