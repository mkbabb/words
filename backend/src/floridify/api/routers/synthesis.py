"""Synthesis API - AI-powered content generation and enhancement."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from floridify.ai import get_openai_connector
from floridify.ai.synthesis_functions import enhance_synthesized_entry
from floridify.ai.synthesizer import DefinitionSynthesizer
from floridify.api.core import ErrorResponse, ResourceResponse, handle_api_errors
# from floridify.core.provider_fetcher import ProviderDataFetcher  # TODO: Module not found
from floridify.core.state_tracker import StateTracker
from floridify.models.models import (
    Definition,
    DictionaryProvider,
    Language,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
)

router = APIRouter(prefix="/synthesis", tags=["synthesis"])


class SynthesisRequest(BaseModel):
    """Request for synthesizing a dictionary entry."""
    
    word: str = Field(..., min_length=1, max_length=100)
    language: Language = Field(Language.ENGLISH)
    providers: list[DictionaryProvider] = Field(
        default_factory=lambda: list(DictionaryProvider),
        description="Dictionary providers to use"
    )
    force_refresh: bool = Field(False, description="Force refresh provider data")
    components: set[str] | None = Field(
        None,
        description="Specific components to generate (default: all)"
    )


class EnhancementRequest(BaseModel):
    """Request for enhancing an existing entry."""
    
    components: set[str] = Field(
        ...,
        description="Components to enhance",
        example=["etymology", "facts", "pronunciation"]
    )
    force: bool = Field(False, description="Force regeneration")


class ComponentStatus(BaseModel):
    """Status of a synthesized entry's components."""
    
    word_components: dict[str, bool] = Field(
        ...,
        description="Word-level component availability"
    )
    definition_components: dict[str, dict[str, bool]] = Field(
        ...,
        description="Definition-level component availability by definition ID"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )


@router.post("", response_model=ResourceResponse, status_code=201)
@handle_api_errors
async def synthesize_entry(
    request: SynthesisRequest,
    background_tasks: BackgroundTasks,
) -> ResourceResponse:
    """
    Synthesize a new dictionary entry from multiple providers.
    
    This endpoint:
    1. Fetches data from specified dictionary providers
    2. Clusters definitions by meaning
    3. Synthesizes comprehensive definitions
    4. Generates requested AI components
    5. Returns the complete synthesized entry
    """
    # Check if word exists
    existing_word = await Word.find_one({
        "text": request.word,
        "language": request.language
    })
    
    if existing_word:
        # Check for existing synthesized entry
        existing_entry = await SynthesizedDictionaryEntry.find_one({
            "word_id": str(existing_word.id)
        })
        
        if existing_entry and not request.force_refresh:
            return ResourceResponse(
                data=existing_entry.model_dump(),
                metadata={
                    "cached": True,
                    "version": existing_entry.version,
                },
                links={
                    "self": f"/synthesis/{existing_entry.id}",
                    "word": f"/words/{existing_entry.word_id}",
                    "enhance": f"/synthesis/{existing_entry.id}/enhance",
                }
            )
    
    # Initialize components
    ai = await get_openai_connector()
    # fetcher = ProviderDataFetcher()  # TODO: Module not found
    synthesizer = DefinitionSynthesizer(ai)
    tracker = StateTracker()
    
    # Fetch provider data
    tracker.update_state("fetching", "Fetching provider data")
    # provider_data_list = await fetcher.fetch_all_providers(
    #     request.word,
    #     providers=request.providers,
    #     force_refresh=request.force_refresh,
    # )
    provider_data_list = []  # TODO: Implement provider fetching
    
    if not provider_data_list:
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="No data found",
                details=[{
                    "field": "word",
                    "message": f"No data found for '{request.word}'",
                    "code": "no_provider_data"
                }]
            ).model_dump()
        )
    
    # Synthesize entry
    tracker.update_state("synthesizing", "Synthesizing definitions")
    entry = await synthesizer.synthesize_entry(
        word=request.word,
        providers_data=provider_data_list,
        force_refresh=request.force_refresh,
        state_tracker=tracker,
        components=request.components,
    )
    
    # Schedule background enhancement if needed
    if request.components is None:
        # Full enhancement requested
        background_tasks.add_task(
            enhance_synthesized_entry,
            str(entry.id),
            ai,
            force=False
        )
    
    return ResourceResponse(
        data=entry.model_dump(),
        metadata={
            "version": entry.version,
            "provider_count": len(provider_data_list),
            "definition_count": len(entry.definition_ids),
        },
        links={
            "self": f"/synthesis/{entry.id}",
            "word": f"/words/{entry.word_id}",
            "enhance": f"/synthesis/{entry.id}/enhance",
            "status": f"/synthesis/{entry.id}/status",
        }
    )


@router.get("/{entry_id}", response_model=ResourceResponse)
@handle_api_errors
async def get_synthesized_entry(
    entry_id: PydanticObjectId,
    expand: str | None = Query(None, description="Expand related resources"),
) -> ResourceResponse:
    """Get a synthesized dictionary entry."""
    entry = await SynthesizedDictionaryEntry.get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    
    entry_dict = entry.model_dump()
    
    # Handle expansions
    if expand:
        expand_set = set(expand.split(","))
        
        if "word" in expand_set:
            word = await Word.get(entry.word_id)
            entry_dict["word"] = word.model_dump() if word else None
        
        if "definitions" in expand_set:
            definitions = await Definition.find(
                {"_id": {"$in": entry.definition_ids}}
            ).to_list()
            entry_dict["definitions"] = [d.model_dump() for d in definitions]
        
        if "pronunciation" in expand_set and entry.pronunciation_id:
            from floridify.models.models import Pronunciation
            pronunciation = await Pronunciation.get(entry.pronunciation_id)
            entry_dict["pronunciation"] = pronunciation.model_dump() if pronunciation else None
        
        if "facts" in expand_set and entry.fact_ids:
            from floridify.models.models import Fact
            facts = await Fact.find(
                {"_id": {"$in": entry.fact_ids}}
            ).to_list()
            entry_dict["facts"] = [f.model_dump() for f in facts]
    
    # Update access metadata
    entry.accessed_at = datetime.utcnow()
    entry.access_count += 1
    await entry.save()
    
    return ResourceResponse(
        data=entry_dict,
        metadata={
            "version": entry.version,
            "access_count": entry.access_count,
            "last_accessed": entry.accessed_at,
        },
        links={
            "self": f"/synthesis/{entry.id}",
            "word": f"/words/{entry.word_id}",
            "enhance": f"/synthesis/{entry.id}/enhance",
            "status": f"/synthesis/{entry.id}/status",
        }
    )


@router.post("/{entry_id}/enhance", response_model=ResourceResponse)
@handle_api_errors
async def enhance_entry(
    entry_id: PydanticObjectId,
    request: EnhancementRequest,
    background_tasks: BackgroundTasks,
) -> ResourceResponse:
    """
    Enhance specific components of a synthesized entry.
    
    Available components:
    - Word-level: etymology, pronunciation, facts
    - Definition-level: synonyms, antonyms, examples, cefr_level, etc.
    """
    entry = await SynthesizedDictionaryEntry.get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    
    # Get AI connector
    ai = await get_openai_connector()
    
    # Schedule enhancement
    background_tasks.add_task(
        enhance_synthesized_entry,
        str(entry.id),
        ai,
        components=request.components,
        force=request.force,
    )
    
    return ResourceResponse(
        data={"status": "enhancement_scheduled"},
        metadata={
            "entry_id": str(entry.id),
            "components": list(request.components),
            "force": request.force,
        },
        links={
            "self": f"/synthesis/{entry.id}",
            "status": f"/synthesis/{entry.id}/status",
        }
    )


@router.get("/{entry_id}/status", response_model=ComponentStatus)
@handle_api_errors
async def get_entry_status(
    entry_id: PydanticObjectId,
) -> ComponentStatus:
    """Get the status of all components in a synthesized entry."""
    entry = await SynthesizedDictionaryEntry.get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    
    # Check word-level components
    word_components = {
        "etymology": entry.etymology is not None,
        "pronunciation": entry.pronunciation_id is not None,
        "facts": bool(entry.fact_ids),
    }
    
    # Check definition-level components
    definitions = await Definition.find(
        {"_id": {"$in": entry.definition_ids}}
    ).to_list()
    
    definition_components = {}
    for definition in definitions:
        def_id = str(definition.id)
        definition_components[def_id] = {
            "synonyms": bool(definition.synonyms),
            "antonyms": bool(definition.antonyms),
            "examples": bool(definition.example_ids),
            "word_forms": bool(definition.word_forms),
            "grammar_patterns": bool(definition.grammar_patterns),
            "collocations": bool(definition.collocations),
            "usage_notes": bool(definition.usage_notes),
            "cefr_level": definition.cefr_level is not None,
            "frequency_band": definition.frequency_band is not None,
            "register": definition.language_register is not None,
            "domain": definition.domain is not None,
            "region": definition.region is not None,
        }
    
    return ComponentStatus(
        word_components=word_components,
        definition_components=definition_components,
        metadata={
            "entry_version": entry.version,
            "last_updated": entry.updated_at,
            "model_info": entry.model_info.model_dump() if entry.model_info else None,
        }
    )


@router.post("/refresh-providers/{word}", response_model=ResourceResponse)
@handle_api_errors
async def refresh_provider_data(
    word: str,
    providers: list[DictionaryProvider] = Query(
        default_factory=lambda: list(DictionaryProvider)
    ),
    language: Language = Query(Language.ENGLISH),
    cascade_synthesis: bool = Query(
        True,
        description="Automatically re-synthesize after refresh"
    ),
) -> ResourceResponse:
    """
    Refresh provider data for a word and optionally re-synthesize.
    
    This will:
    1. Fetch fresh data from all specified providers
    2. Update existing provider data records
    3. Optionally trigger re-synthesis of the dictionary entry
    """
    # Check if word exists
    existing_word = await Word.find_one({
        "text": word,
        "language": language
    })
    
    if not existing_word:
        raise HTTPException(404, "Word not found")
    
    # Fetch fresh provider data
    # fetcher = ProviderDataFetcher()  # TODO: Module not found
    # provider_data_list = await fetcher.fetch_all_providers(
    #     word,
    #     providers=providers,
    #     force_refresh=True,
    # )
    provider_data_list = []  # TODO: Implement provider fetching
    
    # Update provider data records
    for provider_data in provider_data_list:
        existing = await ProviderData.find_one({
            "word_id": existing_word.id,
            "provider": provider_data.provider,
        })
        
        if existing:
            # Update existing record
            existing.data = provider_data.data
            existing.version += 1
            await existing.save()
        else:
            # Create new record
            provider_data.word_id = str(existing_word.id)
            await provider_data.create()
    
    result = {
        "word_id": str(existing_word.id),
        "providers_updated": len(provider_data_list),
        "cascade_synthesis": cascade_synthesis,
    }
    
    # Optionally cascade to synthesis
    if cascade_synthesis:
        existing_entry = await SynthesizedDictionaryEntry.find_one({
            "word_id": str(existing_word.id)
        })
        
        if existing_entry:
            # Re-synthesize with updated data
            ai = await get_openai_connector()
            synthesizer = DefinitionSynthesizer(ai)
            
            new_entry = await synthesizer.synthesize_entry(
                word=word,
                providers_data=provider_data_list,
                force_refresh=True,
            )
            
            result["synthesis_updated"] = True
            result["synthesis_id"] = str(new_entry.id)
    
    return ResourceResponse(
        data=result,
        metadata={
            "timestamp": datetime.utcnow(),
        },
        links={
            "word": f"/words/{existing_word.id}",
            "synthesis": f"/synthesis/{result.get('synthesis_id')}" if result.get('synthesis_id') else None,
        }
    )