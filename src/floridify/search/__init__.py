"""Advanced search infrastructure for Floridify.

This module provides hyper-efficient fuzzy search capabilities using:
1. Traditional data structures (Trie, BK-Tree) for exact and approximate matching
2. Vectorized approaches using embeddings and approximate nearest neighbors
3. Comprehensive lexicon support for English, French, and other languages
"""

from .fuzzy_traditional import TraditionalFuzzySearch
from .fuzzy_vectorized import VectorizedFuzzySearch
from .index import WordIndex
from .lexicon_loader import LexiconLoader
from .search_manager import SearchManager

__all__ = [
    "WordIndex",
    "TraditionalFuzzySearch",
    "VectorizedFuzzySearch",
    "LexiconLoader",
    "SearchManager",
]
