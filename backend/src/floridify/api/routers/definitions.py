"""Definitions API - Comprehensive CRUD and component operations."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from floridify.ai.connector import get_openai_connector
from floridify.ai.synthesis_functions import (
    assess_definition_cefr,
    assess_definition_frequency,
    classify_definition_register,
    detect_regional_variants,
    enhance_definitions_parallel,
    extract_grammar_patterns,
    generate_usage_notes,
    identify_collocations,
    identify_definition_domain,
    synthesize_antonyms,
    synthesize_examples,
    synthesize_synonyms,
)
from floridify.api.core import (
    ErrorResponse,
    FieldSelection,
    ListResponse,
    PaginationParams,
    ResourceResponse,
    SortParams,
    check_etag,
    get_etag,
    handle_api_errors,
)
from floridify.api.repositories import (
    DefinitionCreate,
    DefinitionFilter,
    DefinitionRepository,
    DefinitionUpdate,
)
from floridify.models.models import Definition

router = APIRouter()


def get_definition_repo() -> DefinitionRepository:
    """Dependency to get definition repository."""
    return DefinitionRepository()


def get_pagination(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
) -> PaginationParams:
    """Get pagination parameters from query."""
    return PaginationParams(offset=offset, limit=limit)


def get_sort(
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc", pattern="^(asc|desc)$")
) -> SortParams:
    """Get sort parameters from query."""
    return SortParams(sort_by=sort_by, sort_order=sort_order)


def get_fields(
    include: str | None = Query(None),
    exclude: str | None = Query(None),
    expand: str | None = Query(None)
) -> FieldSelection:
    """Get field selection from query."""
    return FieldSelection(
        include=set(include.split(",")) if include else None,
        exclude=set(exclude.split(",")) if exclude else None,
        expand=set(expand.split(",")) if expand else None,
    )


class ComponentRegenerationRequest(BaseModel):
    """Request for regenerating definition components."""
    
    components: set[str] = Field(
        ...,
        description="Components to regenerate",
        example=["synonyms", "examples", "grammar_patterns"]
    )
    force: bool = Field(False, description="Force regeneration even if data exists")


class BatchComponentUpdate(BaseModel):
    """Batch update request for definition components."""
    
    definition_ids: list[str] = Field(..., description="Definition IDs to update")
    components: set[str] = Field(..., description="Components to update")
    force: bool = Field(False, description="Force regeneration")
    parallel: bool = Field(True, description="Process in parallel")


@router.get("", response_model=ListResponse[Definition])
@handle_api_errors
async def list_definitions(
    request: Request,
    response: Response,
    repo: DefinitionRepository = Depends(get_definition_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    # Filter parameters
    word_id: str | None = Query(None),
    part_of_speech: str | None = Query(None),
    language_register: str | None = Query(None),
    domain: str | None = Query(None),
    cefr_level: str | None = Query(None),
    frequency_band: int | None = Query(None, ge=1, le=5),
    has_examples: bool | None = Query(None),
) -> ListResponse[Definition]:
    """
    List definitions with filtering, sorting, and pagination.
    
    Field selection:
    - include: Comma-separated fields to include
    - exclude: Comma-separated fields to exclude  
    - expand: Comma-separated related resources to expand (e.g., "examples")
    """
    # Build filter
    filter_params = DefinitionFilter(
        word_id=word_id,
        part_of_speech=part_of_speech,
        language_register=language_register,
        domain=domain,
        cefr_level=cefr_level,
        frequency_band=frequency_band,
        has_examples=has_examples,
    )
    
    # Get data
    definitions, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )
    
    # Apply field selection and expansions
    items = []
    for definition in definitions:
        if fields.expand and "examples" in fields.expand:
            def_dict = await repo.get_with_examples(definition.id)
        else:
            def_dict = definition.model_dump()
        
        def_dict = fields.apply_to_dict(def_dict)
        items.append(def_dict)
    
    # Build response
    response_data = ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    
    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag
    
    # Check if Not Modified
    if check_etag(request, etag):
        response.status_code = 304
        return Response(status_code=304)
    
    return response_data


@router.post("", response_model=ResourceResponse, status_code=201)
@handle_api_errors
async def create_definition(
    data: DefinitionCreate,
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> ResourceResponse:
    """Create a new definition."""
    definition = await repo.create(data)
    
    return ResourceResponse(
        data=definition.model_dump(),
        links={
            "self": f"/definitions/{definition.id}",
            "word": f"/words/{definition.word_id}",
            "regenerate": f"/definitions/{definition.id}/regenerate",
        }
    )


@router.get("/{definition_id}", response_model=ResourceResponse)
@handle_api_errors
async def get_definition(
    definition_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: DefinitionRepository = Depends(get_definition_repo),
    fields: FieldSelection = Depends(get_fields),
) -> ResourceResponse:
    """Get a single definition by ID."""
    # Get definition with optional expansions
    if fields.expand and "examples" in fields.expand:
        definition_data = await repo.get_with_examples(definition_id)
    else:
        definition = await repo.get(definition_id)
        definition_data = definition.model_dump()
    
    # Apply field selection
    definition_data = fields.apply_to_dict(definition_data)
    
    # Build response
    response_data = ResourceResponse(
        data=definition_data,
        metadata={
            "version": definition_data.get("version", 1),
            "last_modified": definition_data.get("updated_at"),
            "has_examples": bool(definition_data.get("example_ids")),
            "completeness": _calculate_completeness(definition_data),
        },
        links={
            "self": f"/definitions/{definition_id}",
            "word": f"/words/{definition_data['word_id']}",
            "regenerate": f"/definitions/{definition_id}/regenerate",
        }
    )
    
    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag
    
    # Check if Not Modified
    if check_etag(request, etag):
        return Response(status_code=304)
    
    return response_data


@router.put("/{definition_id}", response_model=ResourceResponse)
@handle_api_errors
async def update_definition(
    definition_id: PydanticObjectId,
    data: DefinitionUpdate,
    version: int | None = Query(None, description="Version for optimistic locking"),
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> ResourceResponse:
    """Update a definition with optional optimistic locking."""
    definition = await repo.update(definition_id, data, version)
    
    return ResourceResponse(
        data=definition.model_dump(),
        metadata={
            "version": definition.version,
            "updated_at": definition.updated_at,
        }
    )


@router.delete("/{definition_id}", status_code=204)
@handle_api_errors
async def delete_definition(
    definition_id: PydanticObjectId,
    cascade: bool = Query(False, description="Delete related examples"),
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> None:
    """Delete a definition, optionally with cascade."""
    await repo.delete(definition_id, cascade=cascade)


@router.post("/{definition_id}/regenerate", response_model=ResourceResponse)
@handle_api_errors
async def regenerate_components(
    definition_id: PydanticObjectId,
    request: ComponentRegenerationRequest,
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> ResourceResponse:
    """
    Regenerate specific components of a definition.
    
    Available components:
    - synonyms: Generate synonyms
    - antonyms: Generate antonyms
    - examples: Generate example sentences
    - cefr_level: Assess CEFR difficulty level
    - frequency_band: Assess frequency band
    - register: Classify language register
    - domain: Identify subject domain
    - grammar_patterns: Extract grammar patterns
    - collocations: Identify collocations
    - usage_notes: Generate usage notes
    - regional_variants: Detect regional variants
    """
    # Get definition
    definition = await repo.get(definition_id)
    
    # Get AI connector
    ai = await get_openai_connector()
    
    # Map component names to functions
    component_functions = {
        "synonyms": synthesize_synonyms,
        "antonyms": synthesize_antonyms,
        "examples": synthesize_examples,
        "cefr_level": assess_definition_cefr,
        "frequency_band": assess_definition_frequency,
        "register": classify_definition_register,
        "domain": identify_definition_domain,
        "grammar_patterns": extract_grammar_patterns,
        "collocations": identify_collocations,
        "usage_notes": generate_usage_notes,
        "regional_variants": detect_regional_variants,
    }
    
    # Validate components
    invalid_components = request.components - set(component_functions.keys())
    if invalid_components:
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid components",
                details=[{
                    "field": "components",
                    "message": f"Invalid components: {invalid_components}",
                    "code": "invalid_components"
                }]
            ).model_dump()
        )
    
    # Get word for context
    from floridify.models.models import Word
    word = await Word.get(definition.word_id)
    
    # Update components
    updates = {}
    for component in request.components:
        if component == "examples":
            # Special handling for examples
            from floridify.models.models import Example
            examples = await synthesize_examples(
                definition, word.text, ai, count=3
            )
            # Save examples
            example_docs = []
            for ex_data in examples:
                example = Example(
                    word_id=definition.word_id,
                    definition_id=str(definition.id),
                    **ex_data
                )
                await example.create()
                example_docs.append(example)
            definition.example_ids = [str(ex.id) for ex in example_docs]
            updates["examples"] = [ex.model_dump() for ex in example_docs]
        else:
            # Generate component
            func = component_functions[component]
            result = await func(definition, word.text, ai)
            
            # Map to definition fields
            if component == "cefr_level":
                definition.cefr_level = result
            elif component == "frequency_band":
                definition.frequency_band = result
            elif component == "register":
                definition.language_register = result
            elif component == "domain":
                definition.domain = result
            elif component == "regional_variants":
                definition.region = result
            else:
                setattr(definition, component, result)
            
            updates[component] = result
    
    # Save definition
    definition.version += 1
    await definition.save()
    
    return ResourceResponse(
        data=definition.model_dump(),
        metadata={
            "regenerated_components": list(request.components),
            "version": definition.version,
            "updated_at": definition.updated_at,
        }
    )


@router.post("/batch/regenerate", response_model=dict[str, Any])
@handle_api_errors
async def batch_regenerate_components(
    request: BatchComponentUpdate,
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> dict[str, Any]:
    """Regenerate components for multiple definitions."""
    # Get definitions
    definition_ids = [PydanticObjectId(id) for id in request.definition_ids]
    definitions = await repo.get_many(definition_ids)
    
    if len(definitions) != len(request.definition_ids):
        raise HTTPException(404, "Some definitions not found")
    
    # Get AI connector
    ai = await get_openai_connector()
    
    # Process definitions
    results = await enhance_definitions_parallel(
        definitions,
        ai,
        components=request.components,
        force_refresh=request.force,
    )
    
    # Save all definitions
    for definition in definitions:
        definition.version += 1
        await definition.save()
    
    return {
        "processed": len(definitions),
        "components": list(request.components),
        "results": results,
    }


def _calculate_completeness(definition_data: dict[str, Any]) -> float:
    """Calculate completeness score for a definition."""
    fields = [
        "text", "part_of_speech", "word_forms", "example_ids",
        "synonyms", "antonyms", "cefr_level", "frequency_band",
        "language_register", "domain", "grammar_patterns",
        "collocations", "usage_notes"
    ]
    
    filled = sum(1 for field in fields if definition_data.get(field))
    return filled / len(fields)