"""Lookup endpoints for word definitions."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...caching.decorators import cached_api_call
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...core.state_tracker import lookup_state_tracker
from ...models.models import Definition, Pronunciation
from ...utils.logging import get_logger
from ...utils.state_tracker import PipelineStage, StateTracker
from .common import PipelineMetrics

logger = get_logger(__name__)
router = APIRouter()


# Models specific to lookup endpoints
class LookupParams(BaseModel):
    """Parameters for word lookup endpoint."""

    force_refresh: bool = Field(default=False, description="Force refresh of cached data")
    providers: list[DictionaryProvider] = Field(
        default=[DictionaryProvider.WIKTIONARY],
        description="Dictionary providers to use",
    )
    no_ai: bool = Field(default=False, description="Skip AI synthesis")


class LookupResponse(BaseModel):
    """Response for word lookup."""

    word: str = Field(..., description="The word that was looked up")
    pronunciation: Pronunciation = Field(..., description="Pronunciation information")
    definitions: list[Definition] = Field(default_factory=list, description="Word definitions")
    last_updated: datetime = Field(..., description="When this entry was last updated")
    pipeline_metrics: PipelineMetrics | None = Field(
        None, description="Pipeline execution metrics (optional)"
    )


class RegenerateExamplesRequest(BaseModel):
    """Request to regenerate examples for a definition."""

    definition_index: int = Field(
        ..., description="Index of the definition to regenerate examples for"
    )
    definition_text: str | None = Field(None, description="Optional custom definition text to use")
    count: int | None = Field(2, description="Number of examples to generate", ge=1, le=5)


class RegenerateExamplesResponse(BaseModel):
    """Response for regenerating examples."""

    word: str = Field(..., description="The word examples were regenerated for")
    definition_index: int = Field(..., description="Index of the definition")
    examples: list[dict[str, Any]] = Field(..., description="New generated examples")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence in examples")




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
    key_func=lambda word, params: (
        "api_lookup",
        word,
        params.force_refresh,
        tuple(params.providers),
        params.no_ai,
    ),
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
        pipeline_metrics=None,
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
            raise HTTPException(status_code=404, detail=f"No definition found for word: {word}")

        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Lookup completed: {word} in {elapsed_ms}ms")

        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is (like 404)
        raise
    except Exception as e:
        logger.error(f"Lookup failed for {word}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during lookup: {str(e)}")


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
            last_partial_results: dict[str, Any] = {}

            while True:
                try:
                    # Wait for state update with timeout
                    state = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Format as SSE event
                    if state.is_complete:
                        # Process any remaining events in the queue before sending complete
                        while not queue.empty():
                            try:
                                pending_state = queue.get_nowait()
                                if not pending_state.is_complete and not pending_state.error:
                                    # Emit any pending provider_data events
                                    if (
                                        pending_state.details
                                        and "partial_results" in pending_state.details
                                    ):
                                        partial_results = pending_state.details["partial_results"]
                                        if "provider_data" in partial_results:
                                            provider_data_list = partial_results["provider_data"]
                                            if len(provider_data_list) > len(
                                                last_partial_results.get("provider_data", [])
                                            ):
                                                latest_provider_data = provider_data_list[-1]
                                                if hasattr(latest_provider_data, "model_dump"):
                                                    serialized_data = (
                                                        latest_provider_data.model_dump()
                                                    )
                                                else:
                                                    serialized_data = latest_provider_data

                                                provider_event = {
                                                    "stage": "provider_data",
                                                    "provider": serialized_data.get(
                                                        "provider_name", "unknown"
                                                    ),
                                                    "definitions_count": len(
                                                        serialized_data.get("definitions", [])
                                                    ),
                                                    "data": serialized_data,
                                                }
                                                yield f"event: provider_data\ndata: {json.dumps(jsonable_encoder(provider_event))}\n\n"
                                                last_partial_results = partial_results
                            except asyncio.QueueEmpty:
                                break

                        # Get the final result
                        result = await lookup_task
                        if result:
                            event_data = {
                                "word": result.word,
                                "pronunciation": result.pronunciation.model_dump(),
                                "definitions": [d.model_dump() for d in result.definitions],
                                "last_updated": result.last_updated.isoformat(),
                            }
                            yield f"event: complete\ndata: {json.dumps(jsonable_encoder(event_data))}\n\n"
                        else:
                            yield 'event: error\ndata: {"error": "No definition found"}\n\n'
                        break
                    elif state.error:
                        yield f'event: error\ndata: {{"error": "{state.error}"}}\n\n'
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
                                if len(provider_data_list) > len(
                                    last_partial_results.get("provider_data", [])
                                ):
                                    # Get the latest provider data (already serialized as dict)
                                    latest_provider_data = provider_data_list[-1]
                                    # Ensure the provider data is properly serialized
                                    if hasattr(latest_provider_data, "model_dump"):
                                        # Still a Pydantic model, serialize it
                                        serialized_data = latest_provider_data.model_dump()
                                    else:
                                        # Already a dict
                                        serialized_data = latest_provider_data

                                    provider_event = {
                                        "stage": "provider_data",
                                        "provider": serialized_data.get("provider_name", "unknown"),
                                        "definitions_count": len(
                                            serialized_data.get("definitions", [])
                                        ),
                                        "data": serialized_data,
                                    }
                                    yield f"event: provider_data\ndata: {json.dumps(jsonable_encoder(provider_event))}\n\n"
                                    last_partial_results = partial_results

                        # Always emit the progress event
                        yield f"event: progress\ndata: {json.dumps(jsonable_encoder(event_data))}\n\n"

                except TimeoutError:
                    yield 'event: error\ndata: {"error": "Timeout waiting for updates"}\n\n'
                    break

    except Exception as e:
        logger.error(f"SSE generation failed: {e}")
        yield f'event: error\ndata: {{"error": "{str(e)}"}}\n\n'
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
        def __init__(self) -> None:
            super().__init__()
            self.partial_results: dict[str, Any] = {}

        async def update(
            self,
            stage: PipelineStage,
            progress: float,
            message: str,
            metadata: dict[str, Any] | None = None,
            partial_data: Any | None = None,
        ) -> None:
            await super().update(stage, progress, message, metadata, partial_data)

            # Store partial data for later
            if partial_data:
                if "provider_data" in partial_data:
                    if "provider_data" not in self.partial_results:
                        self.partial_results["provider_data"] = []
                    # Serialize ProviderData object to dict for JSON compatibility
                    provider_data = partial_data["provider_data"]
                    if hasattr(provider_data, "model_dump"):
                        # It's a Pydantic model, convert to dict
                        self.partial_results["provider_data"].append(provider_data.model_dump())
                    else:
                        # It's already a dict
                        self.partial_results["provider_data"].append(provider_data)
                elif "best_match" in partial_data:
                    self.partial_results["best_match"] = partial_data["best_match"]

            # Map PipelineStage to string stages for the global tracker
            stage_map = {
                PipelineStage.SEARCH: "search",
                PipelineStage.PROVIDER_FETCH: "provider_fetch",
                PipelineStage.PROVIDER_START: "provider_start",
                PipelineStage.PROVIDER_CONNECTED: "provider_connected",
                PipelineStage.PROVIDER_DOWNLOADING: "provider_downloading",
                PipelineStage.PROVIDER_PARSING: "provider_parsing",
                PipelineStage.PROVIDER_COMPLETE: "provider_complete",
                PipelineStage.AI_CLUSTERING: "ai_clustering",
                PipelineStage.AI_SYNTHESIS: "ai_synthesis",
                PipelineStage.AI_EXAMPLES: "ai_examples",
                PipelineStage.AI_SYNONYMS: "ai_synonyms",
                PipelineStage.STORAGE_SAVE: "storage_save",
                PipelineStage.COMPLETE: "complete",
            }

            # Progress comes in as 0-100, convert to 0-1 for frontend
            overall_progress = progress / 100.0

            # Update global state tracker with timing info
            details = metadata or {}
            details["elapsed_ms"] = self.get_total_duration_ms()

            # Add partial results to details for streaming
            if self.partial_results:
                details["partial_results"] = self.partial_results

            # Map stage to string, with fallback
            mapped_stage = stage_map.get(stage)
            if mapped_stage is None:
                logger.warning(f"Unknown pipeline stage: {stage}")
                mapped_stage = str(stage.value) if hasattr(stage, "value") else str(stage)

            await lookup_state_tracker.update_state(
                stage=mapped_stage,
                progress=overall_progress,
                message=message,
                details=details,
                is_complete=(stage == PipelineStage.COMPLETE),
            )

    bridge_tracker = BridgeStateTracker()

    try:
        # Start tracking
        await lookup_state_tracker.update_state(
            stage="search",
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
            pipeline_metrics=None,
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


@router.post("/lookup/{word}/regenerate-examples", response_model=RegenerateExamplesResponse)
async def regenerate_examples(
    word: str,
    request: RegenerateExamplesRequest,
) -> RegenerateExamplesResponse:
    """Regenerate examples for a specific definition.

    Generates fresh AI examples for a given word definition, replacing
    the existing generated examples while preserving literature examples.

    Args:
        word: The word to regenerate examples for
        request: Contains definition_index and optionally the definition text

    Returns:
        New generated examples for the specified definition

    Raises:
        404: Word not found in storage
        400: Invalid definition index
        500: AI generation error
    """
    from ...ai.factory import get_openai_connector
    from ...models import Examples, GeneratedExample
    from ...storage.mongodb import get_synthesized_entry, save_synthesized_entry

    logger.info(f"Regenerating examples for '{word}' definition {request.definition_index}")

    try:
        # Get the existing entry
        entry = await get_synthesized_entry(word)
        if not entry:
            raise HTTPException(status_code=404, detail=f"No stored entry found for word: {word}")

        # Validate definition index
        if request.definition_index >= len(entry.definitions):
            raise HTTPException(
                status_code=400, detail=f"Invalid definition index: {request.definition_index}"
            )

        # Get the target definition
        target_def = entry.definitions[request.definition_index]

        # Get AI connector from factory
        ai_connector = get_openai_connector()

        # Generate new examples
        example_response = await ai_connector.examples(
            word=word,
            word_type=target_def.word_type,
            definition=request.definition_text or target_def.definition,
            count=request.count or 2,
        )

        # Create new examples, preserving literature examples
        new_generated = [
            GeneratedExample(sentence=sentence, regenerable=True)
            for sentence in example_response.example_sentences
        ]

        # Update the definition's examples
        if target_def.examples:
            target_def.examples.generated = new_generated
        else:
            target_def.examples = Examples(generated=new_generated)

        # Save the updated entry
        await save_synthesized_entry(entry)

        logger.success(f"✅ Regenerated {len(new_generated)} examples for '{word}'")

        return RegenerateExamplesResponse(
            word=word,
            definition_index=request.definition_index,
            examples=[ex.model_dump() for ex in new_generated],
            confidence=example_response.confidence,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate examples for '{word}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate examples: {str(e)}")
