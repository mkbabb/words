"""Lookup endpoints for word definitions."""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...api.services.loaders import DictionaryEntryLoader
from ...caching import cached_api_call_with_dedup
from ...caching.core import get_global_cache
from ...caching.models import CacheNamespace
from ...core.lookup_pipeline import _ensure_primary_audio, lookup_word_pipeline
from ...core.state_tracker import Stages, StateTracker
from ...core.streaming import create_streaming_response
from ...models.dictionary import (
    Definition as DefModel,
    DictionaryEntry as DictEntry,
    DictionaryProvider,
    Word as WordModel,
)
from ...models.richness import compute_entry_richness
from ...models.parameters import LookupParams
from ...models.user import UserRole
from ...storage.mongodb import get_best_existing_entry
from ...utils.logging import get_logger
from ...utils.sanitization import validate_word_input
from ..core import AdminDep, OptionalUserRoleDep

logger = get_logger(__name__)
router = APIRouter()

# Deduplicates concurrent background synthesis requests
_background_synthesis_in_flight: set[str] = set()


async def _background_synthesize(word: str, params: LookupParams) -> None:
    """Fire-and-forget AI synthesis using existing provider data in the DB."""
    if word in _background_synthesis_in_flight:
        return
    _background_synthesis_in_flight.add(word)
    try:
        await lookup_word_pipeline(
            word=word,
            providers=params.providers,
            languages=params.languages,
            no_ai=False,
            skip_search=True,
            state_tracker=None,
        )
        logger.info(f"Background synthesis complete for '{word}'")
    except Exception as e:
        logger.warning(f"Background synthesis failed for '{word}': {e}")
    finally:
        _background_synthesis_in_flight.discard(word)


# Models specific to lookup endpoints
class DictionaryEntryResponse(BaseModel):
    """Complete dictionary entry response with all resolved data."""

    # Entry metadata
    word: str = Field(..., description="The word that was looked up")
    languages: list[str] = Field(..., description="Language precedence list (primary first)")
    id: str | None = Field(None, description="ID of the synthesized dictionary entry")
    last_updated: datetime = Field(..., description="When this entry was last updated")
    model_info: dict[str, Any] | None = Field(
        None,
        description="AI model information (null for non-AI entries)",
    )

    # Version provenance
    version: str | None = Field(None, description="Current version string (e.g. 1.0.3)")
    version_count: int | None = Field(None, description="Total number of versions in history")

    # Pronunciation
    pronunciation: dict[str, Any] | None = Field(None, description="Pronunciation information")

    # Etymology
    etymology: dict[str, Any] | None = Field(None, description="Etymology information")

    # Images attached to the entry
    images: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Images attached to the synthesized entry",
    )

    # Richness score (0.0–1.0)
    richness_score: float | None = Field(None, description="Entry richness score (0.0–1.0)")

    # Definitions with all resolved data
    definitions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Word definitions with all resolved data",
    )


def parse_lookup_params(
    force_refresh: bool = Query(default=False, description="Force refresh of cached data"),
    providers: list[str] = Query(default=["wiktionary"], description="Dictionary providers"),
    languages: list[str] = Query(default=["en"], description="Languages to query"),
    no_ai: bool = Query(default=False, description="Skip AI synthesis"),
) -> LookupParams:
    """Parse and validate lookup parameters using shared model."""
    # Use the shared model's validators to parse the parameters
    return LookupParams(
        force_refresh=force_refresh,
        providers=providers,  # validators handle conversion
        languages=languages,  # validators handle conversion
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
        skip_search=True,
        state_tracker=None,  # No state tracking for cached lookups
    )

    if not entry:
        return None

    # Use the centralized loader to convert to LookupResponse
    try:
        response_dict = await DictionaryEntryLoader.load_as_lookup_response(
            entry=entry,
        )

        return DictionaryEntryResponse(**response_dict)
    except Exception as e:
        logger.error(f"Error creating LookupResponse: {e}")
        raise


@router.get("/lookup/{word}", response_model=DictionaryEntryResponse)
async def lookup_word(
    word: str,
    user_role: OptionalUserRoleDep,
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

    # Premium gating: free users can only get AI synthesis if it's already cached
    is_premium = user_role in (UserRole.PREMIUM, UserRole.ADMIN) if user_role else False
    if not is_premium and not params.no_ai:
        # Reuse get_best_existing_entry — if synthesis exists we're good,
        # otherwise force no_ai for free users
        existing_entry, is_synthesis = await get_best_existing_entry(word)
        if not is_synthesis:
            params = LookupParams(
                force_refresh=params.force_refresh,
                providers=params.providers,
                languages=params.languages,
                no_ai=True,
            )

    start_time = time.perf_counter()

    try:
        if params.force_refresh:
            entry = await lookup_word_pipeline(
                word=word,
                providers=params.providers,
                languages=params.languages,
                force_refresh=True,
                no_ai=params.no_ai,
                state_tracker=None,
            )
            if not entry:
                raise HTTPException(
                    status_code=404,
                    detail=f"No definition found for word: {word}",
                )
            response_dict = await DictionaryEntryLoader.load_as_lookup_response(entry=entry)
            result = DictionaryEntryResponse(**response_dict)
        else:
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
        raise HTTPException(status_code=500, detail=f"Internal error during lookup: {e!s}")


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
    word: str,
    params: LookupParams,
    state_tracker: StateTracker,
) -> DictionaryEntryResponse | None:
    """Perform lookup with state tracking and unified caching."""
    try:
        # Sanitize and validate word input
        word = validate_word_input(word)

        if not params.force_refresh:
            cache = await get_global_cache()
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
            cached_result = cast(
                "DictionaryEntryResponse | None",
                await cache.get(CacheNamespace.API, cache_key),
            )
            if cached_result is not None:
                logger.info(f"🎯 Memory cache hit for '{word}'")
                await _report_cached_progress(
                    state_tracker,
                    word,
                    "cache",
                    len(cached_result.definitions),
                )
                return cached_result

            # Check MongoDB for ANY existing entry (synthesis preferred, then provider)
            existing, is_synthesis = await get_best_existing_entry(word)
            if existing:
                source_label = "synthesis cache" if is_synthesis else f"{existing.provider} DB"
                logger.info(f"📋 DB hit for '{word}' ({source_label})")
                # Ensure audio exists for primary language (fire-and-forget)
                asyncio.ensure_future(_ensure_primary_audio(existing))
                response_dict = await DictionaryEntryLoader.load_as_lookup_response(
                    entry=existing,
                )
                result = DictionaryEntryResponse(**response_dict)

                # Store in memory cache for next time
                await cache.set(
                    CacheNamespace.API,
                    cache_key,
                    result,
                    ttl_override=timedelta(hours=1.0),
                )

                await _report_cached_progress(
                    state_tracker,
                    word,
                    source_label,
                    len(result.definitions),
                )

                # Non-synthesis entry + AI allowed → background synthesis upgrade
                if not is_synthesis and not params.no_ai:
                    asyncio.ensure_future(_background_synthesize(word, params))

                return result

        # No cache hit - run full pipeline with real progress tracking
        logger.info(f"Cache miss - running full lookup pipeline for '{word}'")

        await state_tracker.update_stage(Stages.START)
        await state_tracker.update(stage=Stages.START, message=f"Starting lookup for '{word}'...")

        # Execute the actual lookup pipeline with state tracking
        # skip_search=True: the API endpoint already resolved the word
        entry = await lookup_word_pipeline(
            word=word,
            providers=params.providers,
            languages=params.languages,
            force_refresh=params.force_refresh,
            no_ai=params.no_ai,
            skip_search=True,
            state_tracker=state_tracker,
        )

        if not entry:
            await state_tracker.update_complete(message="Word not found")
            return None

        # Load the entry using the centralized loader
        await state_tracker.update(
            stage=Stages.COMPLETE,
            progress=90,
            message="Loading definition details...",
        )

        # Use the centralized loader to convert to LookupResponse
        response_dict = await DictionaryEntryLoader.load_as_lookup_response(entry=entry)
        result = DictionaryEntryResponse(**response_dict)

        # Mark as complete with result data
        await state_tracker.update_complete(message=f"Found {len(result.definitions)} definitions")

        return result

    except Exception as e:
        await state_tracker.update_error(f"Lookup failed: {e!s}")
        raise


@router.get("/lookup/{word}/stream")
async def lookup_word_stream(
    word: str,
    user_role: OptionalUserRoleDep,
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

    # Premium gating: free users can only get AI synthesis if it's already cached
    is_premium = user_role in (UserRole.PREMIUM, UserRole.ADMIN) if user_role else False
    if not is_premium and not params.no_ai:
        existing_entry, is_synthesis = await get_best_existing_entry(word)
        if not is_synthesis:
            params = LookupParams(
                force_refresh=params.force_refresh,
                providers=params.providers,
                languages=params.languages,
                no_ai=True,
            )

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


@router.post("/lookup/{word}/re-synthesize", response_model=DictionaryEntryResponse)
async def re_synthesize_word(
    word: str,
    _admin: AdminDep,
) -> DictionaryEntryResponse:
    """Re-synthesize a word entry (admin only).

    Triggers the full lookup pipeline with force_refresh=True,
    which re-fetches provider data and runs AI synthesis from scratch.
    Increments the version in L3 cache.
    """
    try:
        word = validate_word_input(word)
    except ValueError as e:
        raise HTTPException(400, str(e))

    logger.info(f"Admin re-synthesis requested for: {word}")

    params = LookupParams(
        force_refresh=True,
        providers=["wiktionary"],
        languages=["en"],
        no_ai=False,
    )

    try:
        entry = await lookup_word_pipeline(
            word=word,
            providers=params.providers,
            languages=params.languages,
            force_refresh=True,
            no_ai=False,
            state_tracker=None,
        )

        if not entry:
            raise HTTPException(404, f"No definition found for word: {word}")

        response_dict = await DictionaryEntryLoader.load_as_lookup_response(entry=entry)
        return DictionaryEntryResponse(**response_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Re-synthesis failed for {word}: {e}")
        raise HTTPException(500, f"Re-synthesis failed: {e!s}")


class SourceVersionSpec(BaseModel):
    """Specifies a provider and version to synthesize from."""

    provider: str
    version: str


class SynthesizeFromRequest(BaseModel):
    """Request body for synthesize-from-versions."""

    sources: list[SourceVersionSpec]
    auto_increment: bool = True


@router.post("/lookup/{word}/synthesize-from", response_model=DictionaryEntryResponse)
async def synthesize_from_versions(
    word: str,
    request: SynthesizeFromRequest,
    _admin: AdminDep,
) -> DictionaryEntryResponse:
    """Re-synthesize a word from specific provider versions (admin only).

    Retrieves historical provider data at specified versions and runs
    AI synthesis from those specific snapshots.
    """
    from ...ai.synthesizer import get_definition_synthesizer
    from ...caching.manager import get_version_manager
    from ...caching.models import ResourceType
    from ...models.base import Language

    try:
        word = validate_word_input(word)
    except ValueError as e:
        raise HTTPException(400, str(e))

    manager = get_version_manager()
    provider_entries: list[DictEntry] = []

    for source in request.sources:
        resource_id = f"{word}:{source.provider}"
        result = await manager.get_by_version(
            resource_id, ResourceType.DICTIONARY, source.version, use_cache=False
        )
        if result is None:
            raise HTTPException(
                404,
                f"Version {source.version} not found for {word}:{source.provider}",
            )

        content = result.content_inline
        if not content:
            raise HTTPException(
                422,
                f"Version {source.version} of {word}:{source.provider} has no content",
            )

        # Reconstruct DictionaryEntry from versioned content
        # Remove MongoDB _id to avoid conflicts during synthesis
        content.pop("_id", None)
        entry = DictEntry(**content)
        provider_entries.append(entry)

    if not provider_entries:
        raise HTTPException(400, "No valid provider sources specified")

    # Run synthesis from the specific provider versions
    synthesizer = get_definition_synthesizer()
    synthesized = await synthesizer.synthesize_entry(
        word=word,
        providers_data=provider_entries,
        languages=[Language.ENGLISH],
        force_refresh=True,
    )

    if not synthesized:
        raise HTTPException(500, f"Synthesis from versions failed for: {word}")

    response_dict = await DictionaryEntryLoader.load_as_lookup_response(entry=synthesized)
    return DictionaryEntryResponse(**response_dict)


@router.get("/lookup/{word}/providers")
async def get_word_providers(word: str) -> list[dict[str, Any]]:
    """Get all provider entries for a word (public endpoint).

    Returns raw provider data grouped by provider, including AI synthesis
    as one of the providers if available.
    """
    try:
        word = validate_word_input(word)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Find the word
    word_doc = await WordModel.find_one(WordModel.text == word)
    if not word_doc:
        raise HTTPException(404, f"Word '{word}' not found")

    # Find all provider entries
    entries = await DictEntry.find(DictEntry.word_id == word_doc.id).to_list()
    if not entries:
        raise HTTPException(404, f"No provider data found for '{word}'")

    result = []
    for entry in entries:
        provider_str = (
            entry.provider.value
            if isinstance(entry.provider, DictionaryProvider)
            else str(entry.provider)
        )
        provider_data: dict[str, Any] = {
            "provider": provider_str,
            "id": str(entry.id),
            "etymology": entry.etymology.model_dump() if entry.etymology else None,
            "model_info": entry.model_info.model_dump() if entry.model_info else None,
            "fetched_at": entry.created_at.isoformat() if entry.created_at else None,
        }

        # Load definitions
        defs: list[DefModel] = []
        if entry.definition_ids:
            defs = await DefModel.find({"_id": {"$in": entry.definition_ids}}).to_list()

        provider_data["definitions"] = [
            {
                "id": str(d.id),
                "part_of_speech": d.part_of_speech,
                "text": d.text,
                "synonyms": d.synonyms[:10] if d.synonyms else [],
                "antonyms": d.antonyms[:10] if d.antonyms else [],
                "examples": [],
            }
            for d in defs
        ]
        provider_data["definition_count"] = len(defs)
        provider_data["richness_score"] = compute_entry_richness(entry, defs)

        result.append(provider_data)

    return result
