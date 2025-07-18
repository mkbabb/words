"""Lookup endpoints for word definitions."""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ...caching.decorators import cached_api_call
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...core.state_tracker import lookup_state_tracker
from ...utils.logging import get_logger
from ...utils.state_tracker import PipelineStage, StateTracker, StateUpdate
from ..models.pipeline import PipelineState
from ..models.requests import LookupParams
from ..models.responses import LookupResponse

logger = get_logger(__name__)
router = APIRouter()


def parse_lookup_params(
    force_refresh: bool = Query(default=False, description="Force refresh of cached data"),
    providers: list[str] = Query(default=["wiktionary"], description="Dictionary providers"),
    no_ai: bool = Query(default=False, description="Skip AI synthesis"),
) -> LookupParams:
    """Parse and validate lookup parameters."""
    # Convert string providers to enum
    provider_enums = []
    for provider_str in providers:
        try:
            provider_enums.append(DictionaryProvider(provider_str.lower()))
        except ValueError:
            # Skip invalid providers
            logger.warning(f"Invalid provider: {provider_str}")
    
    if not provider_enums:
        provider_enums = [DictionaryProvider.WIKTIONARY]
    
    return LookupParams(
        force_refresh=force_refresh,
        providers=provider_enums,
        no_ai=no_ai,
    )


@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda word, params: ("api_lookup", word, params.force_refresh, tuple(params.providers), params.no_ai),
)
async def _cached_lookup(word: str, params: LookupParams) -> LookupResponse | None:
    """Cached word lookup implementation."""
    logger.info(f"Looking up word: {word}")
    
    # Use existing lookup pipeline without state tracking for cached version
    entry = await lookup_word_pipeline(
        word=word,
        providers=params.providers,
        languages=[Language.ENGLISH],
        force_refresh=params.force_refresh,
        no_ai=params.no_ai,
        state_tracker=None,  # No state tracking for cached lookups
    )
    
    if not entry:
        return None
    
    return LookupResponse(
        word=entry.word,
        pronunciation=entry.pronunciation,
        definitions=entry.definitions,
        last_updated=entry.last_updated,
    )


@router.get("/lookup/{word}", response_model=LookupResponse)
async def lookup_word(
    word: str,
    params: LookupParams = Depends(parse_lookup_params),
) -> LookupResponse:
    """Comprehensive word definition lookup with AI-enhanced synthesis.
    
    Performs intelligent word resolution through multi-stage processing:
    1. Word normalization and search across indexed lexicon
    2. Provider-based definition retrieval (Wiktionary, Dictionary.com)
    3. AI-powered meaning extraction and synthesis
    4. Semantic clustering of related definitions
    
    Features:
    - Multi-provider aggregation for comprehensive coverage
    - AI synthesis for coherent, unified definitions
    - Pronunciation data in multiple formats (phonetic, IPA)
    - Rich examples from literature and AI generation
    - Semantic clustering to prevent confusion between unrelated meanings
    
    Performance:
    - Cached responses (1-hour TTL) for optimal speed
    - Typical response time: < 500ms for cached entries
    - Force refresh available for latest data
    
    Args:
        word: Target word for definition lookup (path parameter)
        force_refresh: Bypass all caches for fresh data (default: false)
        providers: Dictionary sources to query (default: wiktionary)
        no_ai: Skip AI synthesis, return raw provider data (default: false)
        
    Returns:
        Comprehensive word entry with pronunciation, definitions, examples,
        and metadata. Each definition includes word type, meaning cluster,
        synonyms, and contextual examples.
        
    Raises:
        404: Word not found in any provider or search index
        500: Internal processing error (provider failure, AI synthesis error)
        422: Invalid parameters (malformed word, unsupported provider)
        
    Example:
        GET /api/v1/lookup/serendipity?providers=wiktionary&force_refresh=false
        
        Returns detailed entry with pronunciation, multiple meanings,
        examples, and AI-synthesized coherent definitions.
    """
    start_time = time.perf_counter()
    
    try:
        result = await _cached_lookup(word, params)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No definition found for word: {word}"
            )
        
        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Lookup completed: {word} in {elapsed_ms}ms")
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (like 404)
        raise
    except Exception as e:
        logger.error(f"Lookup failed for {word}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during lookup: {str(e)}"
        )


async def generate_lookup_events(
    word: str,
    params: LookupParams,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for lookup pipeline progress."""
    # Reset the state tracker
    lookup_state_tracker.reset()
    
    # Start the lookup in a background task
    lookup_task = asyncio.create_task(_lookup_with_tracking(word, params))
    
    try:
        # Subscribe to state updates
        async with lookup_state_tracker.subscribe() as queue:
            last_partial_results = {}
            
            while True:
                try:
                    # Wait for state update with timeout
                    state = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE event
                    if state.is_complete:
                        # Get the final result
                        result = await lookup_task
                        if result:
                            event_data = {
                                "word": result.word,
                                "pronunciation": result.pronunciation.model_dump(),
                                "definitions": [d.model_dump() for d in result.definitions],
                                "last_updated": result.last_updated.isoformat(),
                            }
                            yield f"event: complete\ndata: {json.dumps(event_data)}\n\n"
                        else:
                            yield f"event: error\ndata: {{\"error\": \"No definition found\"}}\n\n"
                        break
                    elif state.error:
                        yield f"event: error\ndata: {{\"error\": \"{state.error}\"}}\n\n"
                        break
                    else:
                        # Progress event with timing metrics
                        event_data = {
                            "stage": state.stage,
                            "progress": state.progress,
                            "message": state.message,
                            "details": state.details,
                            "timestamp": state.timestamp.isoformat(),
                        }
                        
                        # Check for partial results and emit provider_data events
                        if state.details and "partial_results" in state.details:
                            partial_results = state.details["partial_results"]
                            
                            # Emit provider data as it becomes available
                            if "provider_data" in partial_results:
                                provider_data_list = partial_results["provider_data"]
                                # Check if we have new provider data
                                if len(provider_data_list) > len(last_partial_results.get("provider_data", [])):
                                    # Get the latest provider data
                                    latest_provider_data = provider_data_list[-1]
                                    provider_event = {
                                        "stage": "provider_data",
                                        "provider": latest_provider_data.provider_name,
                                        "definitions_count": len(latest_provider_data.definitions) if latest_provider_data.definitions else 0,
                                        "has_pronunciation": bool(latest_provider_data.pronunciation),
                                        "has_etymology": bool(latest_provider_data.etymology),
                                        "data": {
                                            "provider_name": latest_provider_data.provider_name,
                                            "definitions": [d.model_dump() for d in latest_provider_data.definitions] if latest_provider_data.definitions else [],
                                            "pronunciation": latest_provider_data.pronunciation.model_dump() if latest_provider_data.pronunciation else None,
                                            "etymology": latest_provider_data.etymology,
                                        }
                                    }
                                    yield f"event: provider_data\ndata: {json.dumps(provider_event)}\n\n"
                                    last_partial_results = partial_results
                        
                        # Always emit the progress event
                        yield f"event: progress\ndata: {json.dumps(event_data)}\n\n"
                        
                except asyncio.TimeoutError:
                    yield f"event: error\ndata: {{\"error\": \"Timeout waiting for updates\"}}\n\n"
                    break
                    
    except Exception as e:
        logger.error(f"SSE generation failed: {e}")
        yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
    finally:
        # Ensure the lookup task is completed or cancelled
        if not lookup_task.done():
            lookup_task.cancel()
            try:
                await lookup_task
            except asyncio.CancelledError:
                pass


async def _lookup_with_tracking(word: str, params: LookupParams) -> LookupResponse | None:
    """Perform lookup with state tracking."""
    # Create a custom state tracker that bridges to the global one
    class BridgeStateTracker(StateTracker):
        def __init__(self):
            super().__init__()
            self.partial_results = {}
            
        async def update(
            self,
            stage: PipelineStage,
            progress: float,
            message: str,
            metadata: Optional[dict] = None,
            partial_data: Optional[any] = None
        ) -> None:
            await super().update(stage, progress, message, metadata, partial_data)
            
            # Store partial data for later
            if partial_data:
                if "provider_data" in partial_data:
                    if "provider_data" not in self.partial_results:
                        self.partial_results["provider_data"] = []
                    self.partial_results["provider_data"].append(partial_data["provider_data"])
                elif "best_match" in partial_data:
                    self.partial_results["best_match"] = partial_data["best_match"]
            
            # Map PipelineStage to string stages for the global tracker
            stage_map = {
                PipelineStage.SEARCH: "search",
                PipelineStage.PROVIDER_FETCH: "provider_fetch",
                PipelineStage.AI_CLUSTERING: "ai_clustering",
                PipelineStage.AI_SYNTHESIS: "ai_synthesis",
                PipelineStage.AI_EXAMPLES: "ai_examples",
                PipelineStage.AI_SYNONYMS: "ai_synonyms",
                PipelineStage.STORAGE_SAVE: "storage_save",
                PipelineStage.COMPLETE: "complete",
            }
            
            # Calculate overall progress (0-100 scale)
            overall_progress = progress / 100.0
            
            # Update global state tracker with timing info
            details = metadata or {}
            details["elapsed_ms"] = self.get_total_duration_ms()
            
            # Add partial results to details for streaming
            if self.partial_results:
                details["partial_results"] = self.partial_results
            
            await lookup_state_tracker.update_state(
                stage=stage_map.get(stage, str(stage.value)),
                progress=overall_progress,
                message=message,
                details=details,
                is_complete=(stage == PipelineStage.COMPLETE),
            )
    
    bridge_tracker = BridgeStateTracker()
    
    try:
        # Start tracking
        await lookup_state_tracker.update_state(
            stage="initialization",
            progress=0.0,
            message=f"Starting lookup for '{word}'",
            details={"word": word, "providers": [p.value for p in params.providers]},
        )
        
        # Execute the actual lookup pipeline with state tracking
        logger.info(f"Looking up word: {word} with state tracking")
        
        entry = await lookup_word_pipeline(
            word=word,
            providers=params.providers,
            languages=[Language.ENGLISH],
            force_refresh=params.force_refresh,
            no_ai=params.no_ai,
            state_tracker=bridge_tracker,
        )
        
        if not entry:
            await lookup_state_tracker.update_state(
                stage="complete",
                progress=1.0,
                message="Lookup completed - word not found",
                is_complete=True,
                details={"found": False},
            )
            return None
        
        # Convert to response model
        result = LookupResponse(
            word=entry.word,
            pronunciation=entry.pronunciation,
            definitions=entry.definitions,
            last_updated=entry.last_updated,
        )
        
        # Mark as complete with result
        await lookup_state_tracker.update_state(
            stage="complete",
            progress=1.0,
            message="Lookup completed successfully",
            is_complete=True,
            details={
                "found": True,
                "definitions_count": len(result.definitions),
                "total_duration_ms": bridge_tracker.get_total_duration_ms(),
            },
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Lookup with tracking failed for {word}: {e}")
        await lookup_state_tracker.update_state(
            stage="error",
            progress=0.0,
            message="Lookup failed",
            error=str(e),
            is_complete=True,
        )
        raise


@router.get("/lookup/{word}/stream")
async def lookup_word_stream(
    word: str,
    params: LookupParams = Depends(parse_lookup_params),
) -> StreamingResponse:
    """Stream word lookup progress via Server-Sent Events (SSE).
    
    Provides real-time progress updates during the word lookup pipeline,
    including search, provider fetching, and AI synthesis stages.
    
    SSE Event Types:
    - **progress**: Pipeline stage updates with progress percentage and timing metrics
    - **provider_data**: Partial results from each provider as they complete
    - **complete**: Final result with full word entry data  
    - **error**: Error message if lookup fails
    
    Event Format:
    ```
    event: progress
    data: {"stage": "search", "progress": 0.1, "message": "Searching for 'word'", "details": {"elapsed_ms": 123}}
    
    event: provider_data
    data: {"stage": "provider_data", "provider": "wiktionary", "definitions_count": 5, "data": {...}}
    
    event: complete
    data: {"word": "...", "definitions": [...], ...}
    ```
    
    Usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/lookup/word/stream');
    
    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        updateProgressBar(data.progress);
        updateStatusMessage(data.message);
    });
    
    eventSource.addEventListener('provider_data', (e) => {
        const data = JSON.parse(e.data);
        displayProviderResults(data.provider, data.data);
    });
    
    eventSource.addEventListener('complete', (e) => {
        const result = JSON.parse(e.data);
        displayFinalDefinitions(result);
        eventSource.close();
    });
    
    eventSource.addEventListener('error', (e) => {
        const error = JSON.parse(e.data);
        displayError(error.error);
        eventSource.close();
    });
    ```
    
    Args:
        word: Target word for definition lookup (path parameter)
        force_refresh: Bypass all caches for fresh data (default: false)
        providers: Dictionary sources to query (default: wiktionary)
        no_ai: Skip AI synthesis, return raw provider data (default: false)
        
    Returns:
        Server-Sent Events stream with progress updates, partial provider results,
        and final synthesized result. Includes timing metrics for performance monitoring.
        Content-Type: text/event-stream
    """
    return StreamingResponse(
        generate_lookup_events(word, params),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )