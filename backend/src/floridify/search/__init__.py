"""
Floridify Search Engine

A unified, high-performance search system for dictionary and vocabulary lookup.
Supports exact, fuzzy, and semantic search with first-class phrase/idiom support.
"""

from __future__ import annotations

from ..constants import Language
from .constants import EmbeddingLevel, FuzzySearchMethod, SearchMethod
from .core import SearchEngine, SearchResult
from .fuzzy import FuzzySearch
from .language import LanguageSearch
from .lexicon import LexiconLanguageLoader, LexiconSourceConfig
from .phrase import MultiWordExpression, PhraseNormalizer
# TEMPORARILY DISABLED FOR LIGHTWEIGHT DEPLOYMENT
# from .semantic import SemanticSearch
from .semantic_stub import SemanticSearch
from .trie import TrieSearch

__all__ = [
    "SearchEngine",
    "SearchResult",
    "SearchMethod",
    "LanguageSearch",
    "LexiconLanguageLoader",
    "Language",
    "LexiconSourceConfig",
    "TrieSearch",
    "FuzzySearch",
    "FuzzySearchMethod",
    "SemanticSearch",
    "EmbeddingLevel",
    "PhraseNormalizer",
    "MultiWordExpression",
]
