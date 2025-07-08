"""Search endpoints for word and phrase discovery."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ...caching.decorators import cached_api_call
from ...constants import Language
from ...core.search_manager import get_search_engine
from ...search.constants import SearchMethod
from ...utils.logging import get_logger
from ..models.requests import SearchParams, SuggestionParams
from ..models.responses import (
    SearchResponse,
    SearchResultItem,
    SuggestionResponse,
)

logger = get_logger(__name__)
router = APIRouter()


def parse_search_params(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    method: str = Query(default="hybrid", pattern="^(exact|fuzzy|semantic|hybrid)$"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(default=0.6, ge=0.0, le=1.0, description="Minimum score"),
) -> SearchParams:
    """Parse and validate search parameters."""
    return SearchParams(
        q=q,
        method=method,
        max_results=max_results,
        min_score=min_score,
    )


def parse_suggestion_params(
    q: str = Query(..., min_length=2, max_length=50, description="Partial query"),
    limit: int = Query(default=10, ge=1, le=20, description="Maximum suggestions"),
) -> SuggestionParams:
    """Parse and validate suggestion parameters."""
    return SuggestionParams(q=q, limit=limit)




@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda params: ("api_search", params.q, params.method, params.max_results, params.min_score),
)
async def _cached_search(params: SearchParams) -> SearchResponse:
    """Cached search implementation."""
    search_engine = await get_search_engine()
    
    # Convert method string to enum
    method_map = {
        "exact": SearchMethod.EXACT,
        "fuzzy": SearchMethod.FUZZY,
        "semantic": SearchMethod.SEMANTIC,
        "hybrid": SearchMethod.AUTO,
    }
    search_method = method_map.get(params.method, SearchMethod.AUTO)
    
    # Perform search
    start_time = time.perf_counter()
    results = await search_engine.search(
        query=params.q,
        max_results=params.max_results,
        min_score=params.min_score,
        methods=[search_method] if search_method != SearchMethod.AUTO else None,
    )
    search_time_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Convert to response format
    result_items = [
        SearchResultItem(
            word=result.word,
            score=result.score,
            method=result.method,
            is_phrase=result.is_phrase,
        )
        for result in results
    ]
    
    return SearchResponse(
        query=params.q,
        results=result_items,
        total_results=len(result_items),
        search_time_ms=search_time_ms,
    )


@router.get("/search", response_model=SearchResponse)
async def search_words(
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    """Multi-algorithm word and phrase search with intelligent ranking.
    
    Advanced search system supporting exact, fuzzy, and semantic queries
    across indexed vocabulary with automatic method selection and
    relevance-based ranking.
    
    Search Methods:
    - **exact**: Perfect string matches with highest confidence
    - **fuzzy**: Typo-tolerant matching using edit distance algorithms
    - **semantic**: Meaning-based search using transformer embeddings
    - **hybrid**: Intelligent combination of all methods (recommended)
    
    Algorithm Selection:
    - Short queries (≤3 chars): Prefix matching for autocomplete
    - Medium queries (4-8 chars): Exact + fuzzy for typo correction
    - Long queries (>8 chars): Comprehensive multi-method search
    - Phrases (contains spaces): Exact + semantic for meaning analysis
    
    Performance:
    - FAISS-accelerated semantic search for sub-50ms responses
    - Memory-cached results (1-hour TTL) for repeated queries
    - Parallel algorithm execution for optimal speed
    
    Args:
        q: Search query string (1-100 characters, required)
        method: Algorithm selection (exact|fuzzy|semantic|hybrid, default: hybrid)
        max_results: Maximum results to return (1-100, default: 20)
        min_score: Minimum relevance threshold (0.0-1.0, default: 0.6)
        
    Returns:
        Ranked list of matching words/phrases with relevance scores,
        search method used, phrase detection, and performance metrics.
        
    Example:
        GET /api/v1/search?q=cogn&method=hybrid&max_results=10&min_score=0.7
        
        Returns words like "cognitive", "cognition", "recognize" with
        scores indicating relevance and method that found each match.
    """
    try:
        result = await _cached_search(params)
        
        logger.info(
            f"Search completed: '{params.q}' -> {result.total_results} results in {result.search_time_ms}ms"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Search failed for '{params.q}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during search: {str(e)}"
        )


@cached_api_call(
    ttl_hours=6.0,  # Prefix matches are relatively stable
    key_func=lambda params: ("api_suggestions", params.q, params.limit),
)
async def _cached_suggestions(params: SuggestionParams) -> SuggestionResponse:
    """Cached suggestions implementation."""
    search_engine = await get_search_engine([Language.ENGLISH])
    
    # Use prefix search for fast autocomplete
    results = await search_engine.search(
        query=params.q,
        max_results=params.limit,
        methods=[SearchMethod.PREFIX],
    )
    
    suggestions = [result.word for result in results]
    
    return SuggestionResponse(
        query=params.q,
        suggestions=suggestions,
    )


@router.get("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    params: SuggestionParams = Depends(parse_suggestion_params),
) -> SuggestionResponse:
    """Get word suggestions for search-as-you-type autocomplete.
    
    Optimized for real-time user input with fast prefix matching.
    Designed for client-side debouncing (recommended 200-300ms delay).
    
    Features:
    - Ultra-fast prefix search for immediate responses
    - Optimized for partial word input (minimum 2 characters)  
    - Cached results for performance (6-hour TTL)
    - Rate-limited to prevent abuse
    
    Best Practices:
    - Implement 200ms debouncing on client side
    - Abort previous requests when new input arrives
    - Limit requests to reasonable frequency (max 5-10/second)
    
    Args:
        q: Partial query string (2-50 characters)
        limit: Maximum suggestions to return (1-20, default: 10)
        
    Returns:
        List of suggested completions matching the prefix
        
    Example:
        GET /api/v1/suggestions?q=ser&limit=5
        Returns: ["serendipity", "serene", "serious", "service", "sermon"]
    """
    start_time = time.perf_counter()
    
    try:
        result = await _cached_suggestions(params)
        
        # Log performance for monitoring
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.debug(f"Suggestions: '{params.q}' -> {len(result.suggestions)} results in {elapsed_ms}ms")
        
        return result
        
    except Exception as e:
        logger.error(f"Suggestions failed for '{params.q}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error getting suggestions: {str(e)}"
        )


