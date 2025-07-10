"""Generalized search pipeline with singleton search engine for word resolution and discovery."""

from __future__ import annotations

from ..constants import Language
from ..search import SearchEngine
from ..search.constants import SearchMethod
from ..search.core import SearchResult
from ..utils.logging import get_logger
from ..utils.text_utils import normalize_word

logger = get_logger(__name__)

# Global singleton instance
_search_engine: SearchEngine | None = None


async def get_search_engine(
    languages: list[Language] | None = None,
    enable_semantic: bool = False,  # DISABLED BY DEFAULT
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
        logger.info(f"Initializing SearchEngine: languages={[lang.value for lang in languages]}, semantic={enable_semantic}")
        
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


async def search_word_pipeline(
    word: str,
    languages: list[Language] | None = None,
    semantic: bool = False,
    max_results: int = 10,
    normalize: bool = True,
) -> list[SearchResult]:
    """Generalized word search pipeline.
    
    This pipeline can be used by any component that needs to search for words,
    including lookup, synonyms, suggestions, and other features.
    
    Args:
        word: Word to search for
        languages: Languages to search in (defaults to English)
        semantic: Enable semantic search
        max_results: Maximum number of results
        normalize: Whether to normalize the word before searching
        
    Returns:
        List of search results ranked by relevance
    """
    # Set defaults
    if languages is None:
        languages = [Language.ENGLISH]
    
    try:
        # Normalize the query if requested
        search_word = normalize_word(word) if normalize else word
        if normalize and search_word != word:
            logger.debug(f"Normalized: '{word}' → '{search_word}'")

        # Get singleton search engine
        search_engine = await get_search_engine(
            languages=languages,
            enable_semantic=semantic,
        )

        # Perform search based on method preference
        if semantic:
            # Force semantic search
            results = await search_engine.search(
                search_word, 
                max_results=max_results, 
                methods=[SearchMethod.SEMANTIC]
            )
        else:
            # Use hybrid approach (auto-selection)
            results = await search_engine.search(
                search_word, 
                max_results=max_results
            )

        logger.debug(f"Search returned {len(results)} results for '{search_word}'")
        return results

    except Exception as e:
        logger.error(f"Search pipeline failed for '{word}': {e}")
        return []


async def find_best_match(
    word: str,
    languages: list[Language] | None = None,
    semantic: bool = False,
) -> SearchResult | None:
    """Find the single best match for a word.
    
    Convenience function that wraps search_word_pipeline and returns
    only the top result, or None if no results found.
    
    Args:
        word: Word to search for
        languages: Languages to search in
        semantic: Enable semantic search
        
    Returns:
        Best matching search result or None
    """
    results = await search_word_pipeline(
        word=word,
        languages=languages,
        semantic=semantic,
        max_results=1,
    )
    
    return results[0] if results else None


async def search_similar_words(
    word: str,
    languages: list[Language] | None = None,
    max_results: int = 10,
    exclude_original: bool = True,
) -> list[SearchResult]:
    """Search for words similar to the given word.
    
    Uses semantic search to find contextually similar words,
    useful for synonym generation and word discovery.
    
    Args:
        word: Word to find similar words for
        languages: Languages to search in
        max_results: Maximum number of results
        exclude_original: Whether to exclude the original word from results
        
    Returns:
        List of similar words ranked by semantic similarity
    """
    # Always use semantic search for similarity
    results = await search_word_pipeline(
        word=word,
        languages=languages,
        semantic=True,
        max_results=max_results + (1 if exclude_original else 0),
    )
    
    # Filter out the original word if requested
    if exclude_original:
        results = [
            result for result in results 
            if result.word.lower() != word.lower()
        ]
        # Limit to requested number after filtering
        results = results[:max_results]
    
    return results