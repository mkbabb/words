"""Generalized search pipeline with singleton search engine for word resolution and discovery."""

from __future__ import annotations

import time

from ..models.base import Language
from ..search.constants import SearchMode
from ..search.core import SearchResult
from ..search.language import LanguageSearch, get_language_search
from ..utils.logging import (
    get_logger,
    log_metrics,
    log_search_method,
    log_stage,
    log_timing,
)

logger = get_logger(__name__)

# Global singleton instance
_search_engine: LanguageSearch | None = None


async def get_search_engine(
    languages: list[Language] | None = None,
    force_rebuild: bool = False,
) -> LanguageSearch:
    """Get or create the global LanguageSearch singleton.

    Args:
        languages: Languages to support (defaults to English)
        force_rebuild: Force rebuild of search indices

    Returns:
        Initialized LanguageSearch instance

    """
    global _search_engine

    # Use simplified approach - delegate to get_language_search
    target_languages = languages or [Language.ENGLISH]

    # Check if we need to recreate
    if _search_engine is None or _search_engine.languages != target_languages or force_rebuild:
        _search_engine = await get_language_search(target_languages, force_rebuild=force_rebuild)

    return _search_engine


async def reset_search_engine() -> None:
    """Reset the search engine singleton (for testing/cleanup)."""
    global _search_engine
    _search_engine = None
    logger.info("SearchEngine singleton reset")


@log_timing
@log_stage("Search Pipeline", "🔍")
async def search_word_pipeline(
    word: str,
    languages: list[Language] | None = None,
    mode: SearchMode = SearchMode.SMART,
    max_results: int = 20,
    min_score: float | None = None,
    force_rebuild: bool = False,
) -> list[SearchResult]:
    """Generalized word search pipeline - isomorphic with backend API.

    This pipeline can be used by any component that needs to search for words,
    including lookup, synonyms, suggestions, and other features.

    Args:
        word: Word to search for
        languages: Languages to search in (defaults to English)
        mode: Search mode (SMART, EXACT, FUZZY, SEMANTIC)
        max_results: Maximum number of results
        min_score: Minimum score threshold
        force_rebuild: Force rebuild of search indices

    Returns:
        List of search results ranked by relevance

    """
    # Set defaults
    if languages is None:
        languages = [Language.ENGLISH]

    # Track timing for performance metrics
    pipeline_start = time.perf_counter()

    try:
        # Query processing

        # Get language search (replace get_search_engine)
        language_search = await get_language_search(
            languages=languages,
            force_rebuild=force_rebuild,
        )

        # Perform search with specified mode
        results = await language_search.search_with_mode(
            query=word,
            mode=mode,
            max_results=max_results,
            min_score=min_score,
        )

        # Search completed

        # Log search metrics
        pipeline_time = time.perf_counter() - pipeline_start
        logger.info(
            f"✅ Search completed: {len(results)} results for '{word}' in {pipeline_time:.2f}s",
        )

        # Log detailed metrics
        if results:
            scores = [r.score for r in results]
            log_search_method(
                method="pipeline_total",
                query=word,
                result_count=len(results),
                duration=pipeline_time,
                scores=scores,
            )

        return results

    except Exception as e:
        pipeline_time = time.perf_counter() - pipeline_start
        logger.error(f"❌ Search pipeline failed for '{word}' after {pipeline_time:.2f}s: {e}")

        log_metrics(
            word=word,
            error=str(e),
            pipeline_time=pipeline_time,
            stage="search_pipeline_error",
        )
        # Search failed
        return []


@log_timing
async def find_best_match(
    word: str,
    languages: list[Language] | None = None,
    semantic: bool = True,
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
    # Map semantic parameter to SearchMode
    mode = SearchMode.SMART if semantic else SearchMode.FAST

    results = await search_word_pipeline(
        word=word,
        languages=languages,
        mode=mode,
        max_results=1,
    )

    if results:
        best = results[0]
        logger.debug(
            f"✅ Best match for '{word}': '{best.word}' (score: {best.score:.3f}, method: {best.method})",
        )
        return best
    logger.debug(f"❌ No match found for '{word}'")
    return None


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
        results = [result for result in results if result.word.lower() != word.lower()]
        # Limit to requested number after filtering
        results = results[:max_results]

    return results
