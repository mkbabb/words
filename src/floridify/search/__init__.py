"""
Floridify Search Engine

A unified, high-performance search system for dictionary and vocabulary lookup.
Supports exact, fuzzy, and semantic search with first-class phrase/idiom support.
"""

from __future__ import annotations

from .core import SearchEngine, SearchMethod, SearchResult
from .fuzzy import FuzzySearch, FuzzySearchMethod
from .lexicon import Language, LexiconLoader, LexiconSourceConfig
from .phrase import MultiWordExpression, PhraseNormalizer
from .semantic import SemanticSearch
from .trie import TrieSearch

__all__ = [
    "SearchEngine",
    "SearchResult",
    "SearchMethod",
    "LexiconLoader",
    "Language",
    "LexiconSourceConfig",
    "TrieSearch",
    "FuzzySearch",
    "FuzzySearchMethod",
    "SemanticSearch",
    "PhraseNormalizer",
    "MultiWordExpression",
]
