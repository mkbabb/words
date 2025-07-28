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

from ...caching import cached_api_call_with_dedup
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...core.state_tracker import Stages, lookup_state_tracker
from ...models import AudioMedia, Definition, Example, ImageMedia, Pronunciation, ProviderData, Word
from ...utils.logging import get_logger
from ...utils.sanitization import validate_word_input
from .common import PipelineMetrics

logger = get_logger(__name__)
router = APIRouter()


async def load_pronunciation_with_audio(pronunciation_id: str) -> dict[str, Any] | None:
    """Load pronunciation with audio file information."""
    if not pronunciation_id:
        return None

    pronunciation = await Pronunciation.get(pronunciation_id)
    if not pronunciation:
        return None

    # Convert to dict and add audio files
    pron_dict = pronunciation.model_dump(exclude={"id"})

    # Load audio files if any
    if pronunciation.audio_file_ids:
        audio_files = []
        for audio_id in pronunciation.audio_file_ids:
            audio = await AudioMedia.get(audio_id)
            if audio:
                audio_dict = audio.model_dump(exclude={"id"})
                # Convert file path to API URL
                if audio_dict.get("url", "").startswith("/"):
                    # Local file path - convert to API URL
                    audio_dict["url"] = f"/api/v1/audio/files/{audio_id}"
                audio_files.append(audio_dict)
        pron_dict["audio_files"] = audio_files
    else:
        pron_dict["audio_files"] = []

    return pron_dict


# Models specific to lookup endpoints
class DefinitionResponse(BaseModel):
    """Definition with resolved references for API response."""

    # Core fields
    created_at: datetime
    updated_at: datetime
    version: int
    part_of_speech: str
    text: str
    meaning_cluster: dict[str, Any] | None = None
    sense_number: str | None = None

    # Resolved references (not IDs)
    word_forms: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []  # Resolved Example objects
    images: list[dict[str, Any]] = []  # Resolved ImageMedia objects

    # Direct fields
    synonyms: list[str] = []
    antonyms: list[str] = []
    language_register: str | None = None
    domain: str | None = None
    region: str | None = None
    usage_notes: list[dict[str, Any]] = []
    grammar_patterns: list[dict[str, Any]] = []
    collocations: list[dict[str, Any]] = []
    transitivity: str | None = None
    cefr_level: str | None = None
    frequency_band: int | None = None

    # Provider info (resolved, not IDs)
    providers_data: list[dict[str, Any]] = []  # All provider data sources


class LookupParams(BaseModel):
    """Parameters for word lookup endpoint."""

    force_refresh: bool = Field(
        default=False, description="Force refresh of cached data"
    )
    providers: list[DictionaryProvider] = Field(
        default=[DictionaryProvider.WIKTIONARY],
        description="Dictionary providers to use",
    )
    languages: list[Language] = Field(
        default=[Language.ENGLISH], description="Languages to query"
    )
    no_ai: bool = Field(default=False, description="Skip AI synthesis")


class LookupResponse(BaseModel):
    """Response for word lookup."""

    word: str = Field(..., description="The word that was looked up")
    pronunciation: dict[str, Any] | None = Field(
        None, description="Pronunciation information"
    )
    definitions: list[DefinitionResponse] = Field(
        default_factory=list, description="Word definitions with resolved examples"
    )
    etymology: dict[str, Any] | None = Field(
        None, description="Etymology information"
    )
    last_updated: datetime = Field(..., description="When this entry was last updated")
    pipeline_metrics: PipelineMetrics | None = Field(
        None, description="Pipeline execution metrics (optional)"
    )
    model_info: dict[str, Any] | None = Field(
        None, description="AI model information (null for non-AI entries)"
    )
    synth_entry_id: str | None = Field(
        None, description="ID of the synthesized dictionary entry"
    )
    images: list[dict[str, Any]] = Field(
        default_factory=list, description="Images attached to the synthesized entry"
    )


def parse_lookup_params(
    force_refresh: bool = Query(
        default=False, description="Force refresh of cached data"
    ),
    providers: list[str] = Query(
        default=["wiktionary"], description="Dictionary providers"
    ),
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
    key_func=lambda word, params: (
        "api_lookup",
        word,
        params.force_refresh,
        tuple(params.providers),
        params.no_ai,
    ),
    max_wait_time=60.0,  # Wait up to 60 seconds for AI synthesis
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

    # Load definitions from IDs and create DefinitionResponse objects
    definitions = []
    if entry.definition_ids:
        # Load all provider data for this entry
        all_providers_data = []
        if entry.source_provider_data_ids:
            for provider_id in entry.source_provider_data_ids:
                provider_data = await ProviderData.get(provider_id)
                if provider_data:
                    all_providers_data.append(provider_data)

        for def_id in entry.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                # Load examples
                examples = []
                if definition.example_ids:
                    for example_id in definition.example_ids:
                        example = await Example.get(example_id)
                        if example:
                            example_dict = example.model_dump(mode='json')
                            examples.append(example_dict)
                
                # Load images
                images = []
                if definition.image_ids:
                    for image_id in definition.image_ids:
                        image = await ImageMedia.get(image_id)
                        if image:
                            image_dict = image.model_dump(mode='json', exclude={'data'})
                            images.append(image_dict)

                # Create DefinitionResponse
                def_response = DefinitionResponse(
                    created_at=definition.created_at,
                    updated_at=definition.updated_at,
                    version=definition.version,
                    part_of_speech=definition.part_of_speech,
                    text=definition.text,
                    meaning_cluster=(
                        definition.meaning_cluster.model_dump()
                        if definition.meaning_cluster
                        else None
                    ),
                    sense_number=definition.sense_number,
                    word_forms=[wf.model_dump() for wf in definition.word_forms],
                    examples=examples,
                    images=images,
                    synonyms=definition.synonyms,
                    antonyms=definition.antonyms,
                    language_register=definition.language_register,
                    domain=definition.domain,
                    region=definition.region,
                    usage_notes=[un.model_dump() for un in definition.usage_notes],
                    grammar_patterns=[
                        gp.model_dump() for gp in definition.grammar_patterns
                    ],
                    collocations=[c.model_dump() for c in definition.collocations],
                    transitivity=definition.transitivity,
                    cefr_level=definition.cefr_level,
                    frequency_band=definition.frequency_band,
                    providers_data=[
                        pd.model_dump(exclude={"id"}) for pd in all_providers_data
                    ],  # Convert to dict
                )

                definitions.append(def_response)

    # Load pronunciation with audio files
    pronunciation = None
    if entry.pronunciation_id is not None:
        pronunciation = await load_pronunciation_with_audio(entry.pronunciation_id)

    # Load word
    word_obj = await Word.get(entry.word_id)
    word_text = word_obj.text if word_obj else "unknown"
    
    # Load images for the synth entry itself
    synth_images = []
    if entry.image_ids:
        for image_id in entry.image_ids:
            image = await ImageMedia.get(image_id)
            if image:
                image_dict = image.model_dump(mode='json', exclude={'data'})
                synth_images.append(image_dict)

    return LookupResponse(
        word=word_text,
        pronunciation=pronunciation,
        definitions=definitions,
        etymology=entry.etymology.model_dump() if entry.etymology else None,
        last_updated=entry.updated_at,  # Use updated_at from BaseMetadata
        pipeline_metrics=None,
        model_info=entry.model_info.model_dump() if entry.model_info else None,
        synth_entry_id=str(entry.id),
        images=synth_images,  # Images attached to synth entry
    )


@router.get("/lookup/{word}", response_model=LookupResponse)
async def lookup_word(
    word: str,
    params: LookupParams = Depends(parse_lookup_params),
) -> LookupResponse:
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
            raise HTTPException(
                status_code=404, detail=f"No definition found for word: {word}"
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
            status_code=500, detail=f"Internal error during lookup: {str(e)}"
        )


async def generate_lookup_events(
    word: str,
    params: LookupParams,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for lookup pipeline progress."""
    # Sanitize and validate word input
    try:
        word = validate_word_input(word)
    except ValueError as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    # Reset the state tracker
    lookup_state_tracker.reset()

    # Start the lookup in a background task
    lookup_task = asyncio.create_task(_lookup_with_tracking(word, params))

    try:
        # Subscribe to state updates
        async with lookup_state_tracker.subscribe() as queue:
            while True:
                state = await asyncio.wait_for(queue.get(), timeout=30.0)

                if state.is_complete:
                    while not queue.empty():
                        try:
                            pending_state = queue.get_nowait()
                            if (
                                not pending_state.is_complete
                                and not pending_state.error
                            ):
                                yield f"event: progress\ndata: {json.dumps(pending_state.model_dump_optimized())}\n\n"
                        except asyncio.QueueEmpty:
                            break
                    # Emit the final complete event
                    yield f"event: complete\ndata: {json.dumps(jsonable_encoder(state))}\n\n"
                    break
                elif state.error:
                    yield f'event: error\ndata: {{"error": "{state.error}"}}\n\n'
                    break
                else:
                    # Always emit the progress event with optimized payload
                    yield f"event: progress\ndata: {json.dumps(state.model_dump_optimized())}\n\n"

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


async def _lookup_with_tracking(
    word: str, params: LookupParams
) -> LookupResponse | None:
    """Perform lookup with state tracking."""

    await lookup_state_tracker.update_stage(Stages.START)

    # Execute the actual lookup pipeline with state tracking
    logger.info(f"Looking up word: {word} with state tracking")

    entry = await lookup_word_pipeline(
        word=word,
        providers=params.providers,
        languages=params.languages,
        force_refresh=params.force_refresh,
        no_ai=params.no_ai,
        state_tracker=lookup_state_tracker,
    )

    if not entry:
        await lookup_state_tracker.update_complete(message="Word not found")
        return None

    # Load definitions from IDs and create DefinitionResponse objects
    definitions = []
    if entry.definition_ids:
        # Load all provider data for this entry
        all_providers_data = []
        if entry.source_provider_data_ids:
            for provider_id in entry.source_provider_data_ids:
                provider_data = await ProviderData.get(provider_id)
                if provider_data:
                    all_providers_data.append(provider_data)

        for def_id in entry.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                # Load examples
                examples = []
                if definition.example_ids:
                    for example_id in definition.example_ids:
                        example = await Example.get(example_id)
                        if example:
                            example_dict = example.model_dump(mode='json')
                            examples.append(example_dict)
                
                # Load images
                images = []
                if definition.image_ids:
                    for image_id in definition.image_ids:
                        image = await ImageMedia.get(image_id)
                        if image:
                            image_dict = image.model_dump(mode='json', exclude={'data'})
                            images.append(image_dict)

                # Create DefinitionResponse
                def_response = DefinitionResponse(
                    created_at=definition.created_at,
                    updated_at=definition.updated_at,
                    version=definition.version,
                    part_of_speech=definition.part_of_speech,
                    text=definition.text,
                    meaning_cluster=(
                        definition.meaning_cluster.model_dump()
                        if definition.meaning_cluster
                        else None
                    ),
                    sense_number=definition.sense_number,
                    word_forms=[wf.model_dump() for wf in definition.word_forms],
                    examples=examples,
                    images=images,
                    synonyms=definition.synonyms,
                    antonyms=definition.antonyms,
                    language_register=definition.language_register,
                    domain=definition.domain,
                    region=definition.region,
                    usage_notes=[un.model_dump() for un in definition.usage_notes],
                    grammar_patterns=[
                        gp.model_dump() for gp in definition.grammar_patterns
                    ],
                    collocations=[c.model_dump() for c in definition.collocations],
                    transitivity=definition.transitivity,
                    cefr_level=definition.cefr_level,
                    frequency_band=definition.frequency_band,
                    providers_data=[
                        pd.model_dump(exclude={"id"}) for pd in all_providers_data
                    ],  # Convert to dict
                )

                definitions.append(def_response)

    # Load pronunciation with audio files
    pronunciation = None
    if entry.pronunciation_id:
        pronunciation = await load_pronunciation_with_audio(entry.pronunciation_id)

    # Load word
    word_obj = await Word.get(entry.word_id)
    word_text = word_obj.text if word_obj else "unknown"

    # Load images for the synth entry
    synth_images = []
    if entry.image_ids:
        for image_id in entry.image_ids:
            image = await ImageMedia.get(image_id)
            if image:
                image_dict = image.model_dump(mode='json', exclude={'data'})
                synth_images.append(image_dict)

    # Convert to response model
    result = LookupResponse(
        word=word_text,
        pronunciation=pronunciation,
        definitions=definitions,
        etymology=entry.etymology.model_dump() if entry.etymology else None,
        last_updated=entry.updated_at,  # Use updated_at from BaseMetadata
        pipeline_metrics=None,
        model_info=entry.model_info.model_dump() if entry.model_info else None,
        synth_entry_id=str(entry.id),
        images=synth_images,  # Include images
    )

    # Mark as complete with result data
    await lookup_state_tracker.update(
        stage=Stages.COMPLETE,
        progress=100,
        message=f"Found {len(result.definitions)} definitions",
        is_complete=True,
        details={"result": jsonable_encoder(result)},
    )

    return result


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

    return StreamingResponse(
        generate_lookup_events(word, params),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
