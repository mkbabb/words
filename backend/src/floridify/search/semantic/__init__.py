"""Semantic search functionality."""

from .core import SemanticSearch
from .manager import SemanticSearchManager, get_semantic_search_manager

__all__ = [
    "SemanticSearch",
    "SemanticSearchManager",
    "get_semantic_search_manager",
]
