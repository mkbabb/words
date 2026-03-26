"""Search instance cache with invalidation support.

Centralizes cache management that was previously scattered across
engine.py and wordlist/search.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.logging import get_logger

if TYPE_CHECKING:
    from .engine import Search

logger = get_logger(__name__)

# Module-level cache keyed by (corpus_name, semantic_model_str)
_search_instance_cache: dict[tuple[str, str], Search] = {}


def get_cached_search(key: tuple[str, str]) -> Search | None:
    """Get a cached Search instance by key, or None if not cached."""
    cached = _search_instance_cache.get(key)
    if cached and cached._initialized:
        return cached
    return None


def put_cached_search(key: tuple[str, str], instance: Search) -> None:
    """Cache a Search instance."""
    _search_instance_cache[key] = instance


def invalidate_by_corpus(corpus_name: str) -> int:
    """Invalidate all cached Search instances for a given corpus name.

    Returns the number of entries evicted.
    """
    keys_to_remove = [k for k in _search_instance_cache if k[0] == corpus_name]
    for k in keys_to_remove:
        del _search_instance_cache[k]
    if keys_to_remove:
        logger.debug(f"Evicted {len(keys_to_remove)} cached Search instance(s) for corpus '{corpus_name}'")
    return len(keys_to_remove)


def reset_search_cache() -> None:
    """Clear the entire search instance cache."""
    _search_instance_cache.clear()
