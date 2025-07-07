"""Singleton search engine manager for efficient resource usage."""

from __future__ import annotations

from ..constants import Language
from ..search import SearchEngine
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Global singleton instance
_search_engine: SearchEngine | None = None


async def get_search_engine(
    languages: list[Language] | None = None,
    enable_semantic: bool = True,
    force_rebuild: bool = False,
) -> SearchEngine:
    """Get or create the global SearchEngine singleton.
    
    Args:
        languages: Languages to support (defaults to English)
        enable_semantic: Whether to enable semantic search
        force_rebuild: Force rebuild of search indices
        
    Returns:
        Initialized SearchEngine instance
    """
    global _search_engine
    
    # Use defaults
    if languages is None:
        languages = [Language.ENGLISH]
    
    # Check if we need to create or recreate the search engine
    needs_recreation = (
        _search_engine is None or
        force_rebuild or
        _search_engine.languages != languages or
        _search_engine.enable_semantic != enable_semantic
    )
    
    if needs_recreation:
        logger.info(f"Initializing SearchEngine: languages={[l.value for l in languages]}, semantic={enable_semantic}")
        
        _search_engine = SearchEngine(
            languages=languages,
            enable_semantic=enable_semantic,
            force_rebuild=force_rebuild,
        )
        await _search_engine.initialize()
        
        logger.success("SearchEngine singleton initialized")
    
    # At this point, _search_engine is guaranteed to be non-None
    assert _search_engine is not None
    return _search_engine


async def reset_search_engine() -> None:
    """Reset the search engine singleton (for testing/cleanup)."""
    global _search_engine
    _search_engine = None
    logger.info("SearchEngine singleton reset")