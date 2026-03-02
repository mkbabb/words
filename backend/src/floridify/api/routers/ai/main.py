"""AI endpoints: validate-query, suggest-words, suggestions, synthesize + sub-routers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from ....ai.connector import get_openai_connector
from ....ai.constants import SynthesisComponent
from ....ai.synthesizer import get_definition_synthesizer
from ....caching import cached_api_call_with_dedup
from ....core.state_tracker import StateTracker
from ....core.streaming import create_streaming_response
from ....utils.logging import get_logger
from ...core import ResourceResponse
from ...middleware.rate_limiting import ai_limiter, get_client_key
from .assess import router as assess_router
from .base import (
    QueryValidationRequest,
    SuggestionsRequest,
    SynthesizeRequest,
    WordSuggestionRequest,
    handle_ai_errors,
)
from .generate import router as generate_router

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

# Include sub-routers
router.include_router(assess_router)
router.include_router(generate_router)


# Cached suggestion helper


@cached_api_call_with_dedup(
    ttl_hours=1.0,
    key_prefix="api_suggestions",
)
async def _cached_suggestions(input_words: list[str], count: int) -> dict[str, Any]:
    """Cached suggestion generation."""
    connector = get_openai_connector()
    result = await connector.suggestions(input_words, count)
    return result.model_dump()


@router.post("/suggestions")
@handle_ai_errors
async def generate_suggestions(
    request: SuggestionsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """AI-generate related vocabulary suggestions.

    Body:
        - input_words: Seed words for context (optional, max 10)
        - count: Number of suggestions (4-12, default: 10)

    Returns:
        Suggested words with themes and difficulty levels.

    Rate Limited: ~200 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=200)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    return await _cached_suggestions(request.input_words or [], request.count)


# Query Validation & Word Suggestion Endpoints


@router.post("/validate-query")
@handle_ai_errors
async def validate_query(
    request: QueryValidationRequest,
    api_request: Request,
) -> dict[str, Any]:
    """Validate if query seeks word suggestions."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_openai_connector()
    result = await connector.validate_query(request.query)

    return result.model_dump()


@router.post("/suggest-words")
@handle_ai_errors
async def suggest_words(
    request: WordSuggestionRequest,
    api_request: Request,
) -> dict[str, Any]:
    """Generate word suggestions from descriptive query."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=500)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    # First validate the query
    connector = get_openai_connector()
    validation = await connector.validate_query(request.query)

    if not validation.is_valid:
        raise HTTPException(400, f"Invalid query: {validation.reason}")

    # Generate suggestions
    result = await connector.suggest_words(request.query, request.count)

    return result.model_dump()


@router.get("/suggest-words/stream", response_model=None)
@handle_ai_errors
async def suggest_words_stream(
    request: Request,
    query: str,
    count: int = 12,
) -> StreamingResponse:
    """Generate word suggestions with streaming progress updates.

    Returns Server-Sent Events (SSE) with progress updates.

    Query Parameters:
        - query: Descriptive query for word suggestions
        - count: Number of suggestions (1-25, default: 12)

    Event Types:
        - config: Stage definitions for progress visualization
        - progress: Update on current operation with stage and progress
        - complete: Final result with word suggestions
        - error: Error details if something goes wrong
    """
    # Validate count parameter
    if count < 1 or count > 25:
        raise HTTPException(400, "Count must be between 1 and 25")

    client_key = get_client_key(request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=500)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    # Create state tracker for suggestions
    state_tracker = StateTracker(category="suggestions")

    async def suggestions_process() -> dict[str, Any]:
        """Run the suggestion pipeline with state tracking."""
        try:
            await state_tracker.update_stage("START")
            await state_tracker.update(
                stage="START",
                message=f"Starting word suggestions for '{query}'...",
            )

            # Validate query
            await state_tracker.update_stage("QUERY_VALIDATION")
            await state_tracker.update(stage="QUERY_VALIDATION", message="Validating query...")

            connector = get_openai_connector()
            validation = await connector.validate_query(query)

            if not validation.is_valid:
                raise ValueError(f"Invalid query: {validation.reason}")

            await state_tracker.update(
                stage="QUERY_VALIDATION",
                progress=30,
                message="Query validated successfully",
            )

            # Generate words
            await state_tracker.update_stage("WORD_GENERATION")
            await state_tracker.update(
                stage="WORD_GENERATION",
                message="Generating word suggestions...",
            )

            result = await connector.suggest_words(query, count)

            await state_tracker.update(
                stage="WORD_GENERATION",
                progress=70,
                message=f"Generated {len(result.suggestions)} suggestions",
            )

            # Score and rank
            await state_tracker.update_stage("SCORING")
            await state_tracker.update(
                stage="SCORING",
                message="Scoring and ranking suggestions...",
            )

            # Complete successfully
            await state_tracker.update_complete(message="Suggestions generated successfully!")

            # Return result data as dictionary
            return result.model_dump()

        except Exception as e:
            await state_tracker.update_error(f"Failed to generate suggestions: {e!s}")
            raise

    # Use the generalized streaming system
    return await create_streaming_response(
        state_tracker=state_tracker,
        process_func=suggestions_process,
        include_stage_definitions=True,
        include_completion_data=True,
    )


# Synthesize Endpoint


@router.post("/synthesize")
@handle_ai_errors
async def synthesize_entry_components(
    request: SynthesizeRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> ResourceResponse:
    """Regenerate specific components of an existing synthesized dictionary entry."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=1000)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    # Validate components if provided
    if request.components:
        valid_components = {comp.value for comp in SynthesisComponent}
        invalid_components = set(request.components) - valid_components
        if invalid_components:
            raise HTTPException(
                400,
                f"Invalid components: {invalid_components}. Valid components: {sorted(valid_components)}",
            )
        components = {SynthesisComponent(comp) for comp in request.components}
    else:
        components = None

    # Get synthesizer and regenerate components
    synthesizer = get_definition_synthesizer()
    entry = await synthesizer.regenerate_entry_components(
        entry_id=request.entry_id,
        components=components,
    )

    if not entry:
        raise HTTPException(404, "Synthesized dictionary entry not found")

    return ResourceResponse(
        data=entry.model_dump(mode="json"),
        metadata={
            "regenerated_components": list(components) if components else "default",
            "version": entry.version,
        },
        links={
            "self": "/ai/synthesize",
            "entry": f"/lookup/{entry.word_id}",
        },
    )
