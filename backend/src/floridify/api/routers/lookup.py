"""Lookup endpoints for word definitions."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...api.services.loaders import SynthesizedDictionaryEntryLoader
from ...caching import cached_api_call_with_dedup
from ...caching.unified import get_unified
from ...core.lookup_pipeline import lookup_word_pipeline
from ...core.state_tracker import Stages, StateTracker
from ...core.streaming import create_streaming_response
from ...models.definition import DictionaryProvider, Language
from ...storage.mongodb import get_synthesized_entry
from ...utils.logging import get_logger
from ...utils.sanitization import validate_word_input

logger = get_logger(__name__)
router = APIRouter()


# Use the centralized loader service instead of duplicating logic
# The PronunciationLoader is imported from services.loaders above


# Models specific to lookup endpoints
class DictionaryEntryResponse(BaseModel):
    """Complete dictionary entry response with all resolved data."""

    # Entry metadata
    word: str = Field(..., description="The word that was looked up")
    id: str | None = Field(None, description="ID of the synthesized dictionary entry")
    last_updated: datetime = Field(..., description="When this entry was last updated")
    model_info: dict[str, Any] | None = Field(
        None, description="AI model information (null for non-AI entries)"
    )

    # Pronunciation
    pronunciation: dict[str, Any] | None = Field(None, description="Pronunciation information")

    # Etymology
    etymology: dict[str, Any] | None = Field(None, description="Etymology information")

    # Images attached to the entry
    images: list[dict[str, Any]] = Field(
        default_factory=list, description="Images attached to the synthesized entry"
    )

    # Definitions with all resolved data
    definitions: list[dict[str, Any]] = Field(
        default_factory=list, description="Word definitions with all resolved data"
    )


class LookupParams(BaseModel):
    """Parameters for word lookup endpoint."""

    force_refresh: bool = Field(default=False, description="Force refresh of cached data")
    providers: list[DictionaryProvider] = Field(
        default=[DictionaryProvider.WIKTIONARY],
        description="Dictionary providers to use",
    )
    languages: list[Language] = Field(default=[Language.ENGLISH], description="Languages to query")
    no_ai: bool = Field(default=False, description="Skip AI synthesis")


def parse_lookup_params(
    force_refresh: bool = Query(default=False, description="Force refresh of cached data"),
    providers: list[str] = Query(default=["wiktionary"], description="Dictionary providers"),
    languages: list[str] = Query(default=["en"], description="Languages to query"),
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

    # Convert string languages to enum
    language_enums = []
    for language_str in languages:
        try:
            language_enums.append(Language(language_str.lower()))
        except ValueError:
            # Skip invalid languages
            logger.warning(f"Invalid language: {language_str}")

    if not language_enums:
        language_enums = [Language.ENGLISH]

    return LookupParams(
        force_refresh=force_refresh,
        providers=provider_enums,
        languages=language_enums,
        no_ai=no_ai,
    )


@cached_api_call_with_dedup(
    ttl_hours=1.0,
    key_prefix="api_lookup",
)
async def _cached_lookup(word: str, params: LookupParams) -> DictionaryEntryResponse | None:
    """Cached word lookup implementation."""
    logger.info(f"Looking up word: {word}")

    # Use existing lookup pipeline without state tracking for cached version
    entry = await lookup_word_pipeline(
        word=word,
        providers=params.providers,
        languages=params.languages,
        force_refresh=params.force_refresh,
        no_ai=params.no_ai,
        state_tracker=None,  # No state tracking for cached lookups
    )

    if not entry:
        return None

    # Use the centralized loader to convert to LookupResponse
    try:
        response_dict = await SynthesizedDictionaryEntryLoader.load_as_lookup_response(
            entry=entry,
        )

        return DictionaryEntryResponse(**response_dict)
    except Exception as e:
        logger.error(f"Error creating LookupResponse: {e}")
        raise


@router.get("/lookup/{word}", response_model=DictionaryEntryResponse)
async def lookup_word(
    word: str,
    params: LookupParams = Depends(parse_lookup_params),
) -> DictionaryEntryResponse:
    """Comprehensive word definition lookup with AI-enhanced synthesis.

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
    # Sanitize and validate word input
    try:
        word = validate_word_input(word)
    except ValueError as e:
        raise HTTPException(400, str(e))

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


async def _report_cached_progress(
    state_tracker: StateTracker,
    word: str,
    source: str,
    definitions_count: int,
) -> None:
    """Report progress for cached results."""
    await state_tracker.update_stage(Stages.START)
    await state_tracker.update(stage=Stages.START, message=f"Starting lookup for '{word}'...")
    await state_tracker.update_stage(Stages.SEARCH_START)
    await state_tracker.update(stage=Stages.SEARCH_START, message=f"Loading from {source}...")
    await state_tracker.update_stage(Stages.SEARCH_COMPLETE)
    await state_tracker.update_stage(Stages.COMPLETE)
    await state_tracker.update_complete(message=f"Found {definitions_count} definitions ({source})")


async def _lookup_with_tracking(
    word: str, params: LookupParams, state_tracker: StateTracker
) -> DictionaryEntryResponse | None:
    """Perform lookup with state tracking and unified caching."""
    try:
        # Sanitize and validate word input
        word = validate_word_input(word)

        if not params.force_refresh:
            cache = await get_unified()
            key_parts = (
                "api_lookup",
                word,
                params.languages,
                params.force_refresh,
                tuple(params.providers),
                params.no_ai,
            )
            cache_key = hashlib.sha256(str(key_parts).encode()).hexdigest()

            # Check memory cache
            cached_result: DictionaryEntryResponse | None = await cache.get("api", cache_key)
            if cached_result is not None:
                logger.info(f"🎯 Memory cache hit for '{word}'")
                await _report_cached_progress(
                    state_tracker, word, "cache", len(cached_result.definitions)
                )
                return cached_result

            # Check MongoDB cache
            existing = await get_synthesized_entry(word)
            if existing:
                logger.info(f"📋 DB cache hit for '{word}'")
                response_dict = await SynthesizedDictionaryEntryLoader.load_as_lookup_response(
                    entry=existing
                )
                result = DictionaryEntryResponse(**response_dict)

                # Store in memory cache for next time
                await cache.set("api", cache_key, result, ttl=timedelta(hours=1.0))

                await _report_cached_progress(
                    state_tracker, word, "database cache", len(result.definitions)
                )
                return result

        # No cache hit - run full pipeline with real progress tracking
        logger.info(f"Cache miss - running full lookup pipeline for '{word}'")

        await state_tracker.update_stage(Stages.START)
        await state_tracker.update(stage=Stages.START, message=f"Starting lookup for '{word}'...")

        # Execute the actual lookup pipeline with state tracking
        entry = await lookup_word_pipeline(
            word=word,
            providers=params.providers,
            languages=params.languages,
            force_refresh=params.force_refresh,
            no_ai=params.no_ai,
            state_tracker=state_tracker,
        )

        if not entry:
            await state_tracker.update_complete(message="Word not found")
            return None

        # Load the entry using the centralized loader
        await state_tracker.update(
            stage=Stages.COMPLETE, progress=90, message="Loading definition details..."
        )

        # Use the centralized loader to convert to LookupResponse
        response_dict = await SynthesizedDictionaryEntryLoader.load_as_lookup_response(entry=entry)
        result = DictionaryEntryResponse(**response_dict)

        # Mark as complete with result data
        await state_tracker.update_complete(message=f"Found {len(result.definitions)} definitions")

        return result

    except Exception as e:
        await state_tracker.update_error(f"Lookup failed: {str(e)}")
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
    - **config**: Stage definitions for progress visualization
    - **progress**: Pipeline stage updates with progress percentage and timing metrics
    - **complete**: Final result with full word entry data
    - **error**: Error message if lookup fails

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
    logger.info(f"Starting streaming lookup for word: {word}")

    # Create state tracker for lookup process
    state_tracker = StateTracker(category="lookup")

    async def lookup_process() -> DictionaryEntryResponse | None:
        """Perform the lookup process while updating state tracker."""
        return await _lookup_with_tracking(word, params, state_tracker)

    # Use the generalized streaming system
    return await create_streaming_response(
        state_tracker=state_tracker,
        process_func=lookup_process,
        include_stage_definitions=True,
        include_completion_data=True,
    )
