"""Floridify Search Engine

A unified, high-performance search system for dictionary and vocabulary lookup.
Supports exact, fuzzy, and semantic search with first-class phrase/idiom support.
"""

from __future__ import annotations

from ..models.base import Language
from .constants import SearchMethod
from .core import Search
from .fuzzy import FuzzySearch
from .language import LanguageSearch
from .models import SearchResult

# Semantic search with graceful degradation when dependencies unavailable
from .semantic.core import SemanticSearch
from .trie import TrieSearch

__all__ = [
    "FuzzySearch",
    "Language",
    "LanguageSearch",
    "Search",
    "SearchMethod",
    "SearchResult",
    "SemanticSearch",
    "TrieSearch",
]
