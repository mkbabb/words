"""Floridify Search Engine

A unified, high-performance search system for dictionary and vocabulary lookup.
Supports exact, fuzzy, substring, and semantic search with multilingual phrase support.

Heavy imports (Search, FuzzySearch, etc.) are lazy to avoid circular imports
with corpus.core which imports candidates from search.fuzzy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .constants import SearchMethod
from .result import SearchResult

if TYPE_CHECKING:
    from .engine import Search
    from .fuzzy.search import FuzzySearch
    from .semantic.search import SemanticSearch
    from .trie.search import TrieSearch

__all__ = [
    "FuzzySearch",
    "Search",
    "SearchMethod",
    "SearchResult",
    "SemanticSearch",
    "TrieSearch",
]


def __getattr__(name: str):
    """Lazy import for heavy modules to avoid circular imports."""
    if name == "Search":
        from .engine import Search

        return Search
    if name == "FuzzySearch":
        from .fuzzy.search import FuzzySearch

        return FuzzySearch
    if name == "SemanticSearch":
        from .semantic.search import SemanticSearch

        return SemanticSearch
    if name == "TrieSearch":
        from .trie.search import TrieSearch

        return TrieSearch
    if name == "Language":
        from ..models.base import Language

        return Language
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
