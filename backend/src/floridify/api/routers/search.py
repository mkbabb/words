"""Search endpoints for word and phrase discovery."""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ...caching.decorators import cached_api_call
from ...core.search_pipeline import get_search_engine, search_word_pipeline
from ...core.state_tracker import search_state_tracker
from ...models.pipeline_state import StateTracker as PipelineStateTracker
from ...search.constants import SearchMethod
from ...utils.logging import get_logger
from ..models.pipeline import PipelineState
from ..models.requests import SearchParams
from ..models.responses import (
    SearchResponse,
    SearchResultItem,
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





@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda params: ("api_search", params.q, params.method, params.max_results, params.min_score),
)
async def _cached_search(params: SearchParams) -> SearchResponse:
    """Cached search implementation using the search pipeline."""
    # Map string method to SearchMethod enum
    method_map = {
        "exact": SearchMethod.EXACT,
        "fuzzy": SearchMethod.FUZZY,
        "semantic": SearchMethod.SEMANTIC,
        "hybrid": SearchMethod.AUTO,
    }
    search_method = method_map.get(params.method, SearchMethod.AUTO)
    
    # Determine if semantic search should be enabled
    # For now, disable semantic search for all methods since it's temporarily disabled
    enable_semantic = False  # search_method in (SearchMethod.SEMANTIC, SearchMethod.AUTO)
    
    # Perform search
    start_time = time.perf_counter()
    
    if search_method in (SearchMethod.EXACT, SearchMethod.FUZZY) and not enable_semantic:
        # For specific non-semantic methods, use search engine directly
        search_engine = await get_search_engine(enable_semantic=False)
        results = await search_engine.search(
            query=params.q,
            max_results=params.max_results,
            min_score=0.0,  # We'll filter later
            methods=[search_method],
        )
    else:
        # Use the pipeline for hybrid/semantic search
        results = await search_word_pipeline(
            word=params.q,
            semantic=enable_semantic,
            max_results=params.max_results,
            normalize=True,
            state_tracker=None,  # No state tracking for cached searches
        )
    
    search_time_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Convert to response format and filter by min_score
    result_items = [
        SearchResultItem(
            word=result.word,
            score=result.score,
            method=result.method.value,
            is_phrase=result.is_phrase,
        )
        for result in results
        if result.score >= params.min_score
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


async def generate_search_events(
    params: SearchParams,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for search pipeline progress."""
    # Reset the state tracker
    search_state_tracker.reset()
    
    # Start the search in a background task
    search_task = asyncio.create_task(_search_with_tracking(params))
    
    try:
        # Subscribe to state updates
        async with search_state_tracker.subscribe() as queue:
            while True:
                try:
                    # Wait for state update with timeout
                    state = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE event
                    if state.is_complete and not state.error:
                        # Get the final result
                        result = await search_task
                        event_data = {
                            "query": result.query,
                            "results": [
                                {
                                    "word": r.word,
                                    "score": r.score,
                                    "method": r.method,
                                    "is_phrase": r.is_phrase,
                                }
                                for r in result.results
                            ],
                            "total_results": result.total_results,
                            "search_time_ms": result.search_time_ms,
                        }
                        yield f"event: complete\ndata: {json.dumps(event_data)}\n\n"
                        break
                    elif state.error:
                        yield f"event: error\ndata: {{\"error\": \"{state.error}\"}}\n\n"
                        break
                    else:
                        # Progress event with partial results if available
                        event_data = {
                            "stage": state.stage,
                            "progress": state.progress,
                            "message": state.message,
                            "timestamp": state.timestamp.isoformat(),
                        }
                        
                        # Include partial results if available in state details
                        if state.details and isinstance(state.details, dict):
                            details = state.details
                            
                            # Extract partial results from pipeline data
                            if "data" in details and isinstance(details["data"], dict):
                                data = details["data"]
                                if "partial_results" in data:
                                    event_data["partial_results"] = data["partial_results"]
                                elif "results" in data:
                                    event_data["partial_results"] = data["results"]
                            
                            # Include metadata if available
                            if "metadata" in details:
                                event_data["metadata"] = details["metadata"]
                        
                        yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"
                        
                except asyncio.TimeoutError:
                    yield f"event: error\ndata: {{\"error\": \"Timeout waiting for updates\"}}\n\n"
                    break
                    
    except Exception as e:
        logger.error(f"SSE generation failed: {e}")
        yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
    finally:
        # Ensure the search task is completed or cancelled
        if not search_task.done():
            search_task.cancel()
            try:
                await search_task
            except asyncio.CancelledError:
                pass


async def _search_with_tracking(params: SearchParams) -> SearchResponse:
    """Perform search with state tracking using the real search pipeline."""
    try:
        # Create a pipeline state tracker for the search_word_pipeline
        pipeline_tracker = PipelineStateTracker()
        
        # Map string method to SearchMethod enum
        method_map = {
            "exact": SearchMethod.EXACT,
            "fuzzy": SearchMethod.FUZZY,
            "semantic": SearchMethod.SEMANTIC,
            "hybrid": SearchMethod.AUTO,
        }
        search_method = method_map.get(params.method, SearchMethod.AUTO)
        
        # Determine if semantic search should be enabled
        # For now, disable semantic search for all methods since it's temporarily disabled
        enable_semantic = False  # search_method in (SearchMethod.SEMANTIC, SearchMethod.AUTO)
        
        # Special handling for specific search methods
        if search_method == SearchMethod.EXACT:
            # For exact search, we want the pipeline to only use exact method
            enable_semantic = False
        elif search_method == SearchMethod.FUZZY:
            # For fuzzy search, we want the pipeline to use fuzzy methods
            enable_semantic = False
        elif search_method == SearchMethod.SEMANTIC:
            # For semantic search, ensure semantic is enabled
            enable_semantic = True
        
        # Create a task to monitor pipeline state and update search state tracker
        async def monitor_pipeline_state():
            """Monitor pipeline state updates and forward to search state tracker."""
            async for state in pipeline_tracker.get_state_updates():
                # Convert pipeline state to search state tracker format
                await search_state_tracker.update_state(
                    stage=state.stage,
                    progress=state.progress,
                    message=state.message,
                    details={
                        "data": state.data,
                        "metadata": state.metadata,
                        "timestamp": state.timestamp,
                    },
                    is_complete=state.stage == "completed",
                    error=state.stage == "error" and state.message or None,
                )
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(monitor_pipeline_state())
        
        try:
            # Execute search with pipeline state tracking
            start_time = time.perf_counter()
            
            # For specific search methods, we need to use the search engine directly
            # to ensure only the requested method is used
            if search_method in (SearchMethod.EXACT, SearchMethod.FUZZY) and not enable_semantic:
                # Get the search engine and call it with specific methods
                search_engine = await get_search_engine(enable_semantic=False)
                
                # Create a wrapper to add state tracking
                async def search_with_method():
                    await pipeline_tracker.update_state(
                        stage="search_query_processing",
                        progress=0.1,
                        message=f"Processing query: {params.q}",
                        metadata={"query": params.q, "method": search_method.value}
                    )
                    
                    # Call search with specific method
                    results = await search_engine.search(
                        query=params.q,
                        max_results=params.max_results,
                        min_score=0.0,  # We'll filter later
                        methods=[search_method],
                    )
                    
                    await pipeline_tracker.update_state(
                        stage="completed",
                        progress=1.0,
                        message=f"Search completed: {len(results)} results",
                        data={"results": [r.model_dump() for r in results[:5]]},
                        metadata={
                            "total_results": len(results),
                            "method": search_method.value,
                        }
                    )
                    
                    return results
                
                results = await search_with_method()
            else:
                # Use the full pipeline for hybrid/semantic search
                results = await search_word_pipeline(
                    word=params.q,
                    semantic=enable_semantic,
                    max_results=params.max_results,
                    normalize=True,
                    state_tracker=pipeline_tracker,
                )
            
            search_time_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Convert search results to API response format
            result_items = []
            for result in results:
                # Filter by min_score
                if result.score >= params.min_score:
                    result_items.append(
                        SearchResultItem(
                            word=result.word,
                            score=result.score,
                            method=result.method.value,
                            is_phrase=result.is_phrase,
                        )
                    )
            
            # Create response
            response = SearchResponse(
                query=params.q,
                results=result_items,
                total_results=len(result_items),
                search_time_ms=search_time_ms,
            )
            
            # Ensure final complete state is sent
            await search_state_tracker.update_state(
                stage="complete",
                progress=1.0,
                message="Search completed successfully",
                is_complete=True,
                details={
                    "total_results": response.total_results,
                    "search_time_ms": response.search_time_ms,
                },
            )
            
            return response
            
        finally:
            # Cancel monitoring task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
    except Exception as e:
        logger.error(f"Search with tracking failed: {e}")
        await search_state_tracker.update_state(
            stage="error",
            progress=0.0,
            message="Search failed",
            error=str(e),
            is_complete=True,
        )
        raise


@router.get("/search/stream")
async def search_words_stream(
    params: SearchParams = Depends(parse_search_params),
) -> StreamingResponse:
    """Stream search progress via Server-Sent Events (SSE).
    
    Provides real-time progress updates during the search pipeline,
    including method selection, search execution, and result ranking.
    
    SSE Event Types:
    - **progress**: Pipeline stage updates with progress percentage
    - **complete**: Final results with scores and metadata
    - **error**: Error message if search fails
    
    Event Format:
    ```
    event: progress
    data: {"stage": "searching", "progress": 0.5, "message": "Executing search"}
    
    event: complete
    data: {"query": "...", "results": [...], "total_results": 10}
    ```
    
    Usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/search/stream?q=cognition');
    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        updateSearchProgress(data.progress);
    });
    eventSource.addEventListener('complete', (e) => {
        const results = JSON.parse(e.data);
        displaySearchResults(results);
        eventSource.close();
    });
    ```
    
    Args:
        q: Search query string (1-100 characters, required)
        method: Algorithm selection (exact|fuzzy|semantic|hybrid, default: hybrid)
        max_results: Maximum results to return (1-100, default: 20)
        min_score: Minimum relevance threshold (0.0-1.0, default: 0.6)
        
    Returns:
        Server-Sent Events stream with progress updates and final results.
        Content-Type: text/event-stream
    """
    return StreamingResponse(
        generate_search_events(params),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


