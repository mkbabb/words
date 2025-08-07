"""
Floridify Search Engine

A unified, high-performance search system for dictionary and vocabulary lookup.
Supports exact, fuzzy, and semantic search with first-class phrase/idiom support.
"""

from __future__ import annotations

from ..models.definition import Language
from .constants import SearchMethod
from .core import SearchEngine
from .corpus import CorpusLanguageLoader, LexiconSourceConfig
from .fuzzy import FuzzySearch
from .language import LanguageSearch
from .models import SearchResult

# Semantic search with graceful degradation when dependencies unavailable
from .semantic.core import SemanticSearch
from .trie import TrieSearch

__all__ = [
    "SearchEngine",
    "SearchResult",
    "SearchMethod",
    "LanguageSearch",
    "CorpusLanguageLoader",
    "Language",
    "LexiconSourceConfig",
    "TrieSearch",
    "FuzzySearch",
    "SemanticSearch",
]
