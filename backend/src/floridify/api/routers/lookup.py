"""Lookup endpoints for word definitions."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...caching import cached_api_call_with_dedup
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...core.state_tracker import Stages, StateTracker
from ...core.streaming import create_streaming_response
from ...models import Definition, ImageMedia, Word
from ...utils.logging import get_logger
from ...utils.sanitization import validate_word_input
from ..services.loaders import DefinitionLoader, PronunciationLoader

logger = get_logger(__name__)
router = APIRouter()


# Use the centralized loader service instead of duplicating logic
# The PronunciationLoader is imported from services.loaders above


# Models specific to lookup endpoints
class DefinitionResponse(BaseModel):
    """Definition with resolved references for API response."""

    # Core fields
    id: str  # Definition ID for frontend editing
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

    force_refresh: bool = Field(default=False, description="Force refresh of cached data")
    providers: list[DictionaryProvider] = Field(
        default=[DictionaryProvider.WIKTIONARY],
        description="Dictionary providers to use",
    )
    languages: list[Language] = Field(default=[Language.ENGLISH], description="Languages to query")
    no_ai: bool = Field(default=False, description="Skip AI synthesis")


class LookupResponse(BaseModel):
    """Response for word lookup."""

    word: str = Field(..., description="The word that was looked up")
    pronunciation: dict[str, Any] | None = Field(None, description="Pronunciation information")
    definitions: list[DefinitionResponse] = Field(
        default_factory=list, description="Word definitions with resolved examples"
    )
    etymology: dict[str, Any] | None = Field(None, description="Etymology information")
    last_updated: datetime = Field(..., description="When this entry was last updated")
    model_info: dict[str, Any] | None = Field(
        None, description="AI model information (null for non-AI entries)"
    )
    synth_entry_id: str | None = Field(None, description="ID of the synthesized dictionary entry")
    images: list[dict[str, Any]] = Field(
        default_factory=list, description="Images attached to the synthesized entry"
    )


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

    # Load definitions using the centralized loader
    definitions = []
    if entry.definition_ids:
        # Load definitions with all relations
        for def_id in entry.definition_ids:
            definition = await Definition.get(def_id)
            if definition:
                # Use the loader to get fully resolved definition
                def_dict = await DefinitionLoader.load_with_relations(
                    definition=definition,
                    include_examples=True,
                    include_images=True,
                    include_provider_data=True,
                    provider_data_ids=[str(pid) for pid in entry.source_provider_data_ids] if entry.source_provider_data_ids else None,
                )

                # Create DefinitionResponse from the loaded data
                def_response = DefinitionResponse(**def_dict)
                definitions.append(def_response)

    # Load pronunciation with audio files using the service
    pronunciation = None
    if entry.pronunciation_id is not None:
        pronunciation = await PronunciationLoader.load_with_audio(str(entry.pronunciation_id) if entry.pronunciation_id else None)

    # Load word
    word_obj = await Word.get(entry.word_id)
    word_text = word_obj.text if word_obj else "unknown"

    # Load images for the synth entry itself
    synth_images = []
    if entry.image_ids:
        for image_id in entry.image_ids:
            image = await ImageMedia.get(image_id)
            if image:
                image_dict = image.model_dump(mode="json", exclude={"data"})
                synth_images.append(image_dict)

    try:
        response = LookupResponse(
            word=word_text,
            pronunciation=pronunciation,
            definitions=definitions,
            etymology=entry.etymology.model_dump(mode="json") if entry.etymology else None,
            last_updated=entry.updated_at,  # Use updated_at from BaseMetadata
            model_info=entry.model_info.model_dump(mode="json") if entry.model_info else None,
            synth_entry_id=str(entry.id),
            images=synth_images,  # Images attached to synth entry
        )
        return response
    except Exception as e:
        logger.error(f"Error creating LookupResponse: {e}")
        logger.error(f"word_text type: {type(word_text)}")
        logger.error(f"pronunciation type: {type(pronunciation)}")
        logger.error(f"pronunciation content: {pronunciation}")
        logger.error(f"definitions type: {type(definitions)}")
        logger.error(f"definitions count: {len(definitions) if definitions else 0}")
        if definitions and len(definitions) > 0:
            logger.error(f"First definition type: {type(definitions[0])}")
        raise


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


async def _lookup_with_tracking(
    word: str, params: LookupParams, state_tracker: StateTracker
) -> LookupResponse | None:
    """Perform lookup with state tracking using the generalized system."""
    try:
        # Sanitize and validate word input
        try:
            word = validate_word_input(word)
        except ValueError as e:
            raise ValueError(f"Invalid word input: {str(e)}")

        await state_tracker.update_stage(Stages.START)
        await state_tracker.update(stage=Stages.START, message=f"Starting lookup for '{word}'...")

        # Execute the actual lookup pipeline with state tracking
        logger.info(f"Looking up word: {word} with state tracking")

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

        # Load definitions using the centralized loader
        await state_tracker.update(
            stage=Stages.COMPLETE, progress=90, message="Loading definition details..."
        )

        definitions = []
        if entry.definition_ids:
            # Load definitions with all relations
            for def_id in entry.definition_ids:
                definition = await Definition.get(def_id)
                if definition:
                    # Use the loader to get fully resolved definition
                    def_dict = await DefinitionLoader.load_with_relations(
                        definition=definition,
                        include_examples=True,
                        include_images=True,
                        include_provider_data=True,
                        provider_data_ids=[str(pid) for pid in entry.source_provider_data_ids] if entry.source_provider_data_ids else None,
                    )

                    # Create DefinitionResponse from the loaded data
                    def_response = DefinitionResponse(**def_dict)
                    definitions.append(def_response)

        # Load pronunciation with audio files
        pronunciation = None
        if entry.pronunciation_id:
            pronunciation = await PronunciationLoader.load_with_audio(str(entry.pronunciation_id) if entry.pronunciation_id else None)

        # Load word
        word_obj = await Word.get(entry.word_id)
        word_text = word_obj.text if word_obj else "unknown"

        # Load images for the synth entry
        synth_images = []
        if entry.image_ids:
            for image_id in entry.image_ids:
                image = await ImageMedia.get(image_id)
                if image:
                    image_dict = image.model_dump(mode="json", exclude={"data"})
                    synth_images.append(image_dict)

        # Convert to response model
        result = LookupResponse(
            word=word_text,
            pronunciation=pronunciation,
            definitions=definitions,
            etymology=entry.etymology.model_dump(mode="json") if entry.etymology else None,
            last_updated=entry.updated_at,  # Use updated_at from BaseMetadata
            model_info=entry.model_info.model_dump(mode="json") if entry.model_info else None,
            synth_entry_id=str(entry.id),
            images=synth_images,  # Include images
        )

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

    async def lookup_process() -> LookupResponse | None:
        """Perform the lookup process while updating state tracker."""
        return await _lookup_with_tracking(word, params, state_tracker)

    # Use the generalized streaming system
    return await create_streaming_response(
        state_tracker=state_tracker,
        process_func=lookup_process,
        include_stage_definitions=True,
        include_completion_data=True,
    )
