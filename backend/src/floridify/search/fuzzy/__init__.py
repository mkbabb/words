"""Fuzzy search sub-module.

Heavy imports (FuzzySearch, FuzzyIndex) are lazy to avoid circular imports
with corpus.core which imports candidates.py from this package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Pure-function modules — safe to import eagerly (no corpus dependency)
from .bk_tree import BKTree, adaptive_max_distance, cascading_search
from .candidates import (
    POSTING_DTYPE,
    LengthBuckets,
    TrigramIndex,
    build_candidate_index,
    get_candidates,
    get_substring_candidates,
    word_substring_trigrams,
    word_trigrams,
)
from .scoring import apply_length_correction, calculate_default_frequency
from .suffix_array import SuffixArray

if TYPE_CHECKING:
    from .index import FuzzyIndex
    from .search import FuzzySearch

__all__ = [
    "FuzzySearch",
    "FuzzyIndex",
    "BKTree",
    "cascading_search",
    "adaptive_max_distance",
    "SuffixArray",
    "apply_length_correction",
    "calculate_default_frequency",
    "build_candidate_index",
    "get_candidates",
    "get_substring_candidates",
    "word_trigrams",
    "word_substring_trigrams",
    "POSTING_DTYPE",
    "TrigramIndex",
    "LengthBuckets",
]


def __getattr__(name: str):
    """Lazy import for heavy modules to avoid circular imports."""
    if name == "FuzzySearch":
        from .search import FuzzySearch

        return FuzzySearch
    if name == "FuzzyIndex":
        from .index import FuzzyIndex

        return FuzzyIndex
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
