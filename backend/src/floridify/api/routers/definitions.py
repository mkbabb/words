"""Definitions API - Comprehensive CRUD and component operations."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from ...ai import get_openai_connector
from ...ai.synthesis_functions import (
    assess_definition_cefr,
    assess_definition_frequency,
    assess_definition_domain,
    assess_grammar_patterns,
    assess_collocations,
    assess_regional_variants,
    classify_definition_register,
    enhance_definitions_parallel,
    usage_note_generation,
    synthesize_antonyms,
    generate_examples,
    synthesize_synonyms,
)
from ...models import Definition, Word
from ..core import (
    ErrorDetail,
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
from ..repositories import (
    DefinitionCreate,
    DefinitionFilter,
    DefinitionRepository,
    DefinitionUpdate,
)

router = APIRouter()


def get_definition_repo() -> DefinitionRepository:
    """Dependency to get definition repository."""
    return DefinitionRepository()


def get_pagination(
    offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)
) -> PaginationParams:
    """Get pagination parameters from query."""
    return PaginationParams(offset=offset, limit=limit)


def get_sort(
    sort_by: str | None = Query(None), sort_order: str = Query("asc", pattern="^(asc|desc)$")
) -> SortParams:
    """Get sort parameters from query."""
    return SortParams(sort_by=sort_by, sort_order=sort_order)


def get_fields(
    include: str | None = Query(None),
    exclude: str | None = Query(None),
    expand: str | None = Query(None),
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
        description="Components to regenerate"
    )
    force: bool = Field(False, description="Force regeneration even if data exists")


class BatchComponentUpdate(BaseModel):
    """Batch update request for definition components."""

    definition_ids: list[str] = Field(..., description="Definition IDs to update")
    components: set[str] = Field(..., description="Components to update")
    force: bool = Field(False, description="Force regeneration")
    parallel: bool = Field(True, description="Process in parallel")


@router.get("", response_model=ListResponse[Definition])
async def list_definitions(
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
        item = definition.model_dump()
        if fields.include or fields.exclude:
            # Apply field filtering if needed
            pass
        items.append(item)

    # Build response
    return ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


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
        },
    )


@router.get("/{definition_id}", response_model=ResourceResponse)
@handle_api_errors
async def get_definition(
    definition_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: DefinitionRepository = Depends(get_definition_repo),
    fields: FieldSelection = Depends(get_fields),
) -> Response | ResourceResponse:
    """Get a single definition by ID."""
    # Get definition with optional expansions
    if fields.expand and "examples" in fields.expand:
        definition_data = await repo.get_with_examples(definition_id)
    else:
        definition = await repo.get(definition_id, raise_on_missing=True)
        assert definition is not None
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
        },
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
        },
    )


@router.delete("/{definition_id}", status_code=204, response_model=None)
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

    # Type assertion for mypy - repo.get raises HTTPException if not found
    assert definition is not None

    # Get AI connector
    ai = get_openai_connector()

    # Map component names to functions
    component_functions = {
        "synonyms": synthesize_synonyms,
        "antonyms": synthesize_antonyms,
        "examples": generate_examples,
        "cefr_level": assess_definition_cefr,
        "frequency_band": assess_definition_frequency,
        "register": classify_definition_register,
        "domain": assess_definition_domain,
        "grammar_patterns": assess_grammar_patterns,
        "collocations": assess_collocations,
        "usage_notes": usage_note_generation,
        "regional_variants": assess_regional_variants,
    }

    # Validate components
    invalid_components = request.components - set(component_functions.keys())
    if invalid_components:
        raise HTTPException(
            400,
            detail=ErrorResponse(
                error="Invalid components",
                details=[
                    ErrorDetail(
                        field="components",
                        message=f"Invalid components: {invalid_components}",
                        code="invalid_components",
                    )
                ],
            ).model_dump(),
        )

    # Get word for context
    from ...models import Word

    word = await Word.get(definition.word_id)
    if not word:
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="Word not found",
                details=[
                    ErrorDetail(
                        field="word_id",
                        message=f"Word with ID {definition.word_id} not found",
                        code="word_not_found",
                    )
                ],
            ).model_dump(),
        )

    # Type assertion for mypy
    assert word is not None

    # Update components
    updates = {}
    for component in request.components:
        if component == "examples":
            # Special handling for examples
            from ...models import Example

            # Generate examples using AI connector
            examples_response = await ai.generate_examples(
                word=word.text,
                part_of_speech=definition.part_of_speech,
                definition=definition.text,
                count=3
            )
            # Save examples
            example_docs = []
            for example_text in examples_response.example_sentences:
                example = Example(
                    definition_id=str(definition.id),
                    text=example_text,
                    type="generated"
                )
                await example.save()
                example_docs.append(example)
            definition.example_ids = [str(ex.id) for ex in example_docs]
            updates["examples"] = [ex.model_dump() for ex in example_docs]
        else:
            # Generate component
            func = component_functions[component]
            
            # Call with appropriate parameters based on function type
            if component in ["synonyms", "antonyms"]:
                result = await func(word.text, definition, ai, force_refresh=request.force)
            else:
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
        },
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
    ai = get_openai_connector()

    # Group definitions by word
    from collections import defaultdict

    definitions_by_word = defaultdict(list)
    for definition in definitions:
        definitions_by_word[definition.word_id].append(definition)

    # Process each word's definitions
    all_results: dict[str, Any] = {}
    for word_id, word_definitions in definitions_by_word.items():
        # Get the word
        word = await Word.get(word_id)
        if not word:
            continue

        # Process definitions for this word
        results = await enhance_definitions_parallel(
            word_definitions,
            word,
            ai,
            components=request.components,
            force_refresh=request.force,
        )
        all_results[word_id] = results

    # Save all definitions
    for definition in definitions:
        definition.version += 1
        await definition.save()

    return {
        "processed": len(definitions),
        "components": list(request.components),
        "results": all_results,
    }


def _calculate_completeness(definition_data: dict[str, Any]) -> float:
    """Calculate completeness score for a definition."""
    fields = [
        "text",
        "part_of_speech",
        "word_forms",
        "example_ids",
        "synonyms",
        "antonyms",
        "cefr_level",
        "frequency_band",
        "language_register",
        "domain",
        "grammar_patterns",
        "collocations",
        "usage_notes",
    ]

    filled = sum(1 for field in fields if definition_data.get(field))
    return filled / len(fields)
