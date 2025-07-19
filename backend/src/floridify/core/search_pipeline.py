"""Generalized search pipeline with singleton search engine for word resolution and discovery."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..constants import Language
from ..search.constants import SearchMethod
from ..search.generalized import SearchResult
from ..search.language import LanguageSearch, get_language_search
from ..utils.logging import (
    get_logger,
    log_metrics,
    log_search_method,
    log_stage,
    log_timing,
)
from ..utils.text_utils import normalize_word

if TYPE_CHECKING:
    from ..models.pipeline_state import StateTracker

from ..models.pipeline_state import PipelineStage

logger = get_logger(__name__)

# Global singleton instance
_search_engine: LanguageSearch | None = None


async def get_search_engine(
    languages: list[Language] | None = None,
    enable_semantic: bool = False,  # Ignored for compatibility
    force_rebuild: bool = False,
) -> LanguageSearch:
    """Get or create the global LanguageSearch singleton.
    
    Args:
        languages: Languages to support (defaults to English)
        enable_semantic: Ignored for compatibility
        force_rebuild: Force rebuild of search indices
        
    Returns:
        Initialized LanguageSearch instance
    """
    global _search_engine
    
    # Use simplified approach - delegate to get_language_search
    target_languages = languages or [Language.ENGLISH]
    
    # Check if we need to recreate
    if _search_engine is None or _search_engine.languages != target_languages or force_rebuild:
        _search_engine = await get_language_search(target_languages)
    
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
    semantic: bool = False,
    max_results: int = 10,
    normalize: bool = True,
    state_tracker: StateTracker | None = None,
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
        state_tracker: Optional state tracker for progress updates
        
    Returns:
        List of search results ranked by relevance
    """
    # Set defaults
    if languages is None:
        languages = [Language.ENGLISH]
    
    # Track timing for performance metrics
    pipeline_start = time.time()
    
    try:
        # Update state: Query processing (0-20%)
        if state_tracker:
            await state_tracker.update_state(
                stage="search_query_processing",
                progress=0.05,
                message=f"Processing query: {word}",
                metadata={"query": word, "languages": [lang.value for lang in languages]}
            )
        
        # Normalize the query if requested
        search_word = normalize_word(word) if normalize else word
        if normalize and search_word != word:
            logger.debug(f"📝 Normalized: '{word}' → '{search_word}'")
            if state_tracker:
                await state_tracker.update_state(
                    stage="search_query_normalized",
                    progress=0.10,
                    message=f"Normalized query: {search_word}",
                    metadata={"normalized_query": search_word}
                )

        # Get singleton search engine
        search_engine = await get_search_engine(
            languages=languages,
            enable_semantic=semantic,
        )

        # Determine search methods
        if semantic:
            methods = [SearchMethod.SEMANTIC]
        else:
            # Let the engine auto-select methods
            methods = None
        
        if state_tracker:
            selected_methods = methods or "auto-selected"
            await state_tracker.update_state(
                stage="search_method_selection",
                progress=0.20,
                message="Selected search methods",
                metadata={"methods": str(selected_methods), "semantic_enabled": semantic}
            )
        
        # Perform search with integrated state tracking
        if state_tracker:
            # Pass state tracker to search engine for detailed progress
            results = await _search_with_state_tracking(
                search_engine=search_engine,
                search_word=search_word,
                max_results=max_results,
                methods=methods,
                state_tracker=state_tracker,
            )
        else:
            # Regular search without state tracking
            if semantic:
                results = await search_engine.search(
                    search_word, 
                    max_results=max_results, 
                    methods=[SearchMethod.SEMANTIC]
                )
            else:
                results = await search_engine.search(
                    search_word, 
                    max_results=max_results
                )

        # Final state update
        if state_tracker:
            pipeline_end = time.time()
            await state_tracker.update_state(
                stage=PipelineStage.COMPLETED,
                progress=1.0,
                message=f"Search completed: {len(results)} results",
                data={"results": [r.model_dump() for r in results[:5]]},  # Include top 5 results
                metadata={
                    "total_results": len(results),
                    "pipeline_time_ms": round((pipeline_end - pipeline_start) * 1000, 2),
                }
            )

        # Log search metrics
        pipeline_time = time.time() - pipeline_start
        logger.info(f"✅ Search completed: {len(results)} results for '{search_word}' in {pipeline_time:.2f}s")
        
        # Log detailed metrics
        if results:
            scores = [r.score for r in results]
            log_search_method(
                method="pipeline_total",
                query=search_word,
                result_count=len(results),
                duration=pipeline_time,
                scores=scores
            )
        
        return results

    except Exception as e:
        pipeline_time = time.time() - pipeline_start
        logger.error(f"❌ Search pipeline failed for '{word}' after {pipeline_time:.2f}s: {e}")
        
        log_metrics(
            word=word,
            error=str(e),
            pipeline_time=pipeline_time,
            stage="search_pipeline_error"
        )
        if state_tracker:
            await state_tracker.update_state(
                stage=PipelineStage.ERROR,
                progress=0.0,
                message=f"Search failed: {str(e)}",
                metadata={"error": str(e), "error_type": type(e).__name__}
            )
        return []


@log_timing
async def find_best_match(
    word: str,
    languages: list[Language] | None = None,
    semantic: bool = False,
    state_tracker: StateTracker | None = None,
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
        state_tracker=state_tracker,
    )
    
    if results:
        best = results[0]
        logger.debug(f"✅ Best match for '{word}': '{best.word}' (score: {best.score:.3f}, method: {best.method})")
        return best
    else:
        logger.debug(f"❌ No match found for '{word}'")
        return None


async def _search_with_state_tracking(
    search_engine: SearchEngine,
    search_word: str,
    max_results: int,
    methods: list[SearchMethod] | None,
    state_tracker: StateTracker,
) -> list[SearchResult]:
    """Execute search with detailed state tracking.
    
    This internal function handles the search execution with progress updates
    at each stage of the search process.
    """
    # Determine actual methods that will be used
    if methods is None or SearchMethod.AUTO in (methods or []):
        actual_methods = search_engine._select_optimal_methods(search_word)
    else:
        actual_methods = methods
    
    # Calculate progress increments
    method_count = len(actual_methods)
    if method_count == 0:
        return []
    
    # Progress allocation: 20-70% for search execution
    search_progress_range = 0.5  # 50% of total progress
    progress_per_method = search_progress_range / method_count
    
    all_results: list[SearchResult] = []
    method_results: dict[str, list[SearchResult]] = {}
    method_times: dict[str, float] = {}
    
    # Execute each search method with tracking
    for i, method in enumerate(actual_methods):
        method_start = time.time()
        base_progress = 0.20 + (i * progress_per_method)
        
        # Update state: Starting method
        stage_map = {
            SearchMethod.EXACT: PipelineStage.SEARCH_EXACT,
            SearchMethod.FUZZY: PipelineStage.SEARCH_FUZZY,
            SearchMethod.SEMANTIC: PipelineStage.SEARCH_SEMANTIC,
            SearchMethod.PREFIX: "search_prefix",  # No enum value for prefix
        }
        stage = stage_map.get(method, f"search_{method.value}")
        
        await state_tracker.update_state(
            stage=stage,
            progress=base_progress,
            message=f"Searching with {method.value} method",
            metadata={"method": method.value, "query": search_word}
        )
        
        # Execute the specific search method
        try:
            if method == SearchMethod.EXACT:
                results = await search_engine._search_exact(search_word)
            elif method == SearchMethod.PREFIX:
                results = await search_engine._search_prefix(search_word, max_results)
            elif method == SearchMethod.FUZZY:
                results = await search_engine._search_fuzzy(search_word, max_results)
            elif method == SearchMethod.SEMANTIC and search_engine.semantic_search:
                results = await search_engine._search_semantic(search_word, max_results)
            else:
                results = []
            
            method_results[method.value] = results
            all_results.extend(results)
            method_duration = time.time() - method_start
            method_times[method.value] = round(method_duration * 1000, 2)
            
            # Log method execution
            scores = [r.score for r in results] if results else []
            log_search_method(
                method=method.value,
                query=search_word,
                result_count=len(results),
                duration=method_duration,
                scores=scores
            )
            
            # Update state: Method completed
            await state_tracker.update_state(
                stage=f"search_{method.value}_completed",
                progress=base_progress + progress_per_method,
                message=f"{method.value} search found {len(results)} results",
                data={"partial_results": [r.model_dump() for r in results[:3]]},  # Top 3 from this method
                metadata={
                    "method": method.value,
                    "result_count": len(results),
                    "time_ms": method_times[method.value],
                }
            )
            
        except Exception as e:
            logger.error(f"Search method {method.value} failed: {e}")
            method_times[method.value] = round((time.time() - method_start) * 1000, 2)
    
    # Result processing phase (70-95%)
    await state_tracker.update_state(
        stage="search_deduplication",
        progress=0.75,
        message="Removing duplicate results",
        metadata={"total_before_dedup": len(all_results)}
    )
    
    # Deduplicate results
    dedup_start = time.time()
    unique_results = search_engine._deduplicate_results(all_results)
    dedup_time = time.time() - dedup_start
    
    duplicates_removed = len(all_results) - len(unique_results)
    if duplicates_removed > 0:
        logger.debug(f"🔄 Removed {duplicates_removed} duplicate results in {dedup_time:.3f}s")
    
    log_metrics(
        stage="deduplication",
        total_before=len(all_results),
        total_after=len(unique_results),
        duplicates_removed=duplicates_removed,
        duration=dedup_time
    )
    
    await state_tracker.update_state(
        stage="search_filtering",
        progress=0.85,
        message="Filtering results by score",
        metadata={
            "total_after_dedup": len(unique_results),
            "min_score": search_engine.min_score,
        }
    )
    
    # Filter by score
    filter_start = time.time()
    filtered_results = [r for r in unique_results if r.score >= search_engine.min_score]
    filter_time = time.time() - filter_start
    
    filtered_out = len(unique_results) - len(filtered_results)
    if filtered_out > 0:
        logger.debug(f"🎯 Filtered out {filtered_out} low-score results in {filter_time:.3f}s")
    
    log_metrics(
        stage="filtering",
        total_before=len(unique_results),
        total_after=len(filtered_results),
        filtered_out=filtered_out,
        min_score=search_engine.min_score,
        duration=filter_time
    )
    
    await state_tracker.update_state(
        stage=PipelineStage.SEARCH_RANKING,
        progress=0.95,
        message="Sorting results by relevance",
        metadata={
            "total_after_filter": len(filtered_results),
            "method_results": {m: len(r) for m, r in method_results.items()},
            "method_times_ms": method_times,
        }
    )
    
    # Sort and limit results
    sorted_results = sorted(filtered_results, key=lambda r: r.score, reverse=True)
    final_results = sorted_results[:max_results]
    
    return final_results


async def search_similar_words(
    word: str,
    languages: list[Language] | None = None,
    max_results: int = 10,
    exclude_original: bool = True,
    state_tracker: StateTracker | None = None,
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
        state_tracker=state_tracker,
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