"""Definition management endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from ...ai.factory import get_openai_connector
from ...ai.models import (
    CEFRLevelResponse,
    CollocationResponse,
    ExampleGenerationResponse,
    GrammarPatternResponse,
    UsageNoteResponse,
)
from ...caching import cached_api_call
from ...storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter()


class DefinitionUpdate(BaseModel):
    """Partial update for a definition."""
    
    definition: str | None = None
    synonyms: list[str] | None = None
    antonyms: list[str] | None = None
    register: str | None = Field(None, pattern="^(formal|informal|neutral|slang|technical)$")
    domain: str | None = None
    region: str | None = None
    cefr_level: str | None = Field(None, pattern="^(A1|A2|B1|B2|C1|C2)$")
    frequency_band: int | None = Field(None, ge=1, le=5)


class ExampleRegenerationRequest(BaseModel):
    """Request to regenerate examples."""
    
    count: int = Field(default=2, ge=1, le=5)
    style: str = Field(default="modern", pattern="^(modern|formal|casual|technical)$")
    context: str | None = Field(None, max_length=500)


class CollocationRequest(BaseModel):
    """Request to generate collocations."""
    
    types: list[str] = Field(
        default=["adjective", "verb", "noun"],
        description="Types of collocations to generate"
    )


@router.patch("/{word}/definitions/{index}")
async def update_definition(
    word: str = Path(..., description="The word to update"),
    index: int = Path(..., ge=0, description="Definition index"),
    updates: DefinitionUpdate = ...,
) -> dict[str, Any]:
    """Update specific fields of a definition."""
    try:
        storage = get_storage()
        entry = await storage.get_synthesized_entry(word)
        
        if not entry:
            raise HTTPException(status_code=404, detail=f"Word '{word}' not found")
        
        if index >= len(entry.definitions):
            raise HTTPException(
                status_code=404, 
                detail=f"Definition index {index} out of range (0-{len(entry.definitions)-1})"
            )
        
        # Apply updates
        definition = entry.definitions[index]
        update_dict = updates.dict(exclude_unset=True)
        
        for field, value in update_dict.items():
            if hasattr(definition, field):
                setattr(definition, field, value)
        
        # Save updated entry
        await storage.save_synthesized_entry(entry, force_refresh=True)
        
        return {
            "status": "success",
            "updated_fields": list(update_dict.keys()),
            "definition": definition.dict()
        }
        
    except Exception as e:
        logger.error(f"Error updating definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{word}/definitions/{index}/examples/regenerate")
async def regenerate_examples(
    word: str = Path(..., description="The word"),
    index: int = Path(..., ge=0, description="Definition index"),
    request: ExampleRegenerationRequest = ExampleRegenerationRequest(),
) -> ExampleGenerationResponse:
    """Regenerate examples for a specific definition."""
    try:
        storage = get_storage()
        entry = await storage.get_synthesized_entry(word)
        
        if not entry:
            raise HTTPException(status_code=404, detail=f"Word '{word}' not found")
        
        if index >= len(entry.definitions):
            raise HTTPException(status_code=404, detail="Definition index out of range")
        
        connector = get_openai_connector()
        definition = entry.definitions[index]
        
        # Generate new examples
        response = await connector.examples(
            word=word,
            word_type=definition.word_type,
            definition=definition.definition,
            count=request.count,
            context=request.context
        )
        
        # Update definition with new examples
        definition.examples.generated.clear()
        for example_text in response.example_sentences:
            from ...models import GeneratedExample
            definition.examples.generated.append(
                GeneratedExample(sentence=example_text, regenerable=True)
            )
        
        await storage.save_synthesized_entry(entry, force_refresh=True)
        
        return response
        
    except Exception as e:
        logger.error(f"Error regenerating examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{word}/definitions/{index}/collocations")
@cached_api_call(ttl_hours=48)
async def generate_collocations(
    word: str = Path(..., description="The word"),
    index: int = Path(..., ge=0, description="Definition index"),
    request: CollocationRequest = CollocationRequest(),
) -> CollocationResponse:
    """Generate collocations for a definition."""
    connector = get_openai_connector()
    
    # Use template-based generation
    response = await connector._make_request(
        prompt=f"Generate common collocations for '{word}' focusing on {', '.join(request.types)} combinations.",
        response_model=CollocationResponse,
        temperature=0.7
    )
    
    return response


@router.post("/{word}/definitions/{index}/grammar-patterns")
@cached_api_call(ttl_hours=48)
async def generate_grammar_patterns(
    word: str = Path(..., description="The word"),
    index: int = Path(..., ge=0, description="Definition index"),
) -> GrammarPatternResponse:
    """Generate grammar patterns for a definition."""
    connector = get_openai_connector()
    
    response = await connector._make_request(
        prompt=f"Extract common grammar patterns for the word '{word}' including verb patterns, transitivity, and usage constructions.",
        response_model=GrammarPatternResponse,
        temperature=0.3
    )
    
    return response


@router.post("/{word}/definitions/{index}/cefr-level")
@cached_api_call(ttl_hours=72)
async def assess_cefr_level(
    word: str = Path(..., description="The word"),
    index: int = Path(..., ge=0, description="Definition index"),
) -> CEFRLevelResponse:
    """Assess CEFR level for a definition."""
    connector = get_openai_connector()
    
    response = await connector._make_request(
        prompt=f"Assess the CEFR level (A1-C2) for the word '{word}' based on complexity, frequency, and typical learner progression.",
        response_model=CEFRLevelResponse,
        temperature=0.3
    )
    
    return response


@router.post("/{word}/definitions/{index}/usage-notes")
@cached_api_call(ttl_hours=48)
async def generate_usage_notes(
    word: str = Path(..., description="The word"),
    index: int = Path(..., ge=0, description="Definition index"),
) -> UsageNoteResponse:
    """Generate usage notes and warnings."""
    connector = get_openai_connector()
    
    response = await connector._make_request(
        prompt=f"Generate usage notes for '{word}' including common errors, regional differences, and register guidance.",
        response_model=UsageNoteResponse,
        temperature=0.5
    )
    
    return response