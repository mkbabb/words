"""Definitions API - Comprehensive CRUD and component operations."""

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from ....ai import get_openai_connector
from ....ai.constants import SynthesisComponent
from ....ai.synthesis_functions import (
    assess_collocations,
    assess_definition_cefr,
    assess_definition_domain,
    assess_definition_frequency,
    assess_grammar_patterns,
    assess_regional_variants,
    classify_definition_register,
    enhance_definitions_parallel,
    generate_examples,
    synthesize_antonyms,
    synthesize_synonyms,
    usage_note_generation,
)
from ....models import Definition, Word
from ...core import (
    ErrorDetail,
    ErrorResponse,
    FieldSelection,
    ListResponse,
    PaginationParams,
    ResourceResponse,
    SortParams,
    check_etag,
    get_etag,
    get_fields,
    get_pagination,
    get_sort,
)
from ...repositories import (
    DefinitionCreate,
    DefinitionFilter,
    DefinitionRepository,
    DefinitionUpdate,
)

router = APIRouter()


def get_definition_repo() -> DefinitionRepository:
    """Dependency to get definition repository."""
    return DefinitionRepository()


class DefinitionQueryParams(BaseModel):
    """Query parameters for listing definitions."""

    word_id: str | None = Field(None, description="Filter by word ID")
    part_of_speech: str | None = Field(None, description="Filter by part of speech")
    language_register: str | None = Field(
        None,
        description="Filter by register (formal/informal/neutral/slang/technical)",
    )
    domain: str | None = Field(None, description="Filter by domain")
    cefr_level: str | None = Field(None, description="Filter by CEFR level")
    frequency_band: int | None = Field(None, ge=1, le=5, description="Filter by frequency band")
    has_examples: bool | None = Field(None, description="Filter by example presence")


class ComponentRegenerationRequest(BaseModel):
    """Request for regenerating definition components."""

    components: set[str] = Field(description="Components to regenerate")
    force: bool = Field(False, description="Force regeneration even if data exists")


class BatchComponentUpdate(BaseModel):
    """Batch update request for definition components."""

    definition_ids: list[str] = Field(..., description="Definition IDs to update")
    components: set[str] = Field(..., description="Components to update")
    force: bool = Field(False, description="Force regeneration")
    parallel: bool = Field(True, description="Process in parallel")


class DefinitionImageUpdate(BaseModel):
    """Request to update definition images."""

    image_path: str = Field(..., description="Path to the image file")
    alt_text: str | None = Field(None, description="Alternative text for accessibility")
    action: str = Field(default="add", description="Action: add or remove")


@router.get("", response_model=ListResponse[Definition])
async def list_definitions(
    repo: DefinitionRepository = Depends(get_definition_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    params: DefinitionQueryParams = Depends(),
) -> ListResponse[Definition]:
    """List definitions with advanced filtering.

    Query Parameters:
        - word_id: Filter by word
        - part_of_speech: Filter by POS
        - language_register: formal/informal/neutral/slang/technical
        - domain: Subject area
        - cefr_level: A1-C2
        - frequency_band: 1-5
        - has_examples: Boolean filter
        - Pagination: offset, limit, sort_by, sort_order

    Returns:
        Paginated definition list.

    """
    # Build filter
    filter_params = DefinitionFilter(
        word_id=params.word_id,
        part_of_speech=params.part_of_speech,
        language_register=params.language_register,
        domain=params.domain,
        cefr_level=params.cefr_level,
        frequency_band=params.frequency_band,
        has_examples=params.has_examples,
    )

    # Get data
    definitions, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )

    # Apply field selection and expansions using unified method
    items = await repo.get_expanded(
        definitions=definitions,
        expand=fields.expand,
    )

    # Apply field selection if needed
    if fields.include or fields.exclude:
        items = [fields.apply_to_dict(item) for item in items]

    # Build response
    return ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_definition(
    data: DefinitionCreate,
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> ResourceResponse:
    """Create definition entry.

    Body:
        Complete definition data including text, POS, metadata.

    Returns:
        Created definition with resource links.

    """
    definition = await repo.create(data)

    return ResourceResponse(
        data=definition.model_dump(mode="json"),
        links={
            "self": f"/definitions/{definition.id}",
            "word": f"/words/{definition.word_id}",
            "regenerate": f"/definitions/{definition.id}/regenerate",
        },
    )


@router.get("/{definition_id}", response_model=ResourceResponse)
async def get_definition(
    definition_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: DefinitionRepository = Depends(get_definition_repo),
    fields: FieldSelection = Depends(get_fields),
) -> Response | ResourceResponse:
    """Retrieve definition with optional expansions.

    Query Parameters:
        - expand: 'examples' to include example data, 'images' to include image data
        - Field selection: include, exclude parameters

    Returns:
        Definition with completeness score and ETag.

    """
    # Get definition with optional expansions using unified method
    definition_data = await repo.get_expanded(
        definition_id=definition_id,
        expand=fields.expand,
    )

    # Apply field selection
    definition_data = fields.apply_to_dict(definition_data)

    # Build response
    response_data = ResourceResponse(
        data=definition_data,
        metadata={
            "version": definition_data.get("version", 1),
            "last_modified": definition_data.get("updated_at"),
            "has_examples": bool(definition_data.get("example_ids")),
            "has_images": bool(definition_data.get("image_ids")),
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
async def update_definition(
    definition_id: PydanticObjectId,
    data: DefinitionUpdate,
    version: int | None = Query(None, description="Version for optimistic locking"),
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> ResourceResponse:
    """Update definition with version control.

    Query Parameters:
        - version: For optimistic locking

    Body:
        Partial update fields.

    Errors:
        409: Version conflict
    """
    definition = await repo.update(definition_id, data, version)

    return ResourceResponse(
        data=definition.model_dump(mode="json"),
        metadata={
            "version": definition.version,
            "updated_at": definition.updated_at.isoformat() if definition.updated_at else None,
        },
    )


@router.delete("/{definition_id}", status_code=204, response_model=None)
async def delete_definition(
    definition_id: PydanticObjectId,
    cascade: bool = Query(False, description="Delete related examples"),
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> None:
    """Delete definition.

    Query Parameters:
        - cascade: Delete related examples
    """
    await repo.delete(definition_id, cascade=cascade)


@router.patch("/{definition_id}", response_model=ResourceResponse)
async def update_definition_partial(
    definition_id: PydanticObjectId,
    update: DefinitionUpdate,
    repo: DefinitionRepository = Depends(get_definition_repo),
    if_match: str | None = Depends(check_etag),
) -> ResourceResponse:
    """Partially update definition fields.

    This endpoint replaces the specific bind_image_to_definition endpoint
    with a more generic update that can handle any field updates including images.
    """
    # Convert if_match header to version for optimistic locking
    version = int(if_match) if if_match else None
    definition = await repo.update(definition_id, update, version=version)

    return ResourceResponse(
        data=definition.model_dump(mode="json"),
        metadata={
            "version": definition.version,
            "etag": get_etag(definition),
        },
        links={
            "self": f"/definitions/{definition_id}",
            "word": f"/words/{definition.word_id}",
        },
    )


@router.post("/{definition_id}/regenerate", response_model=ResourceResponse)
async def regenerate_components(
    definition_id: PydanticObjectId,
    request: ComponentRegenerationRequest,
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> ResourceResponse:
    """AI-regenerate definition components.

    Body:
        - components: Set of components to regenerate
          Options: synonyms, antonyms, examples, cefr_level,
          frequency_band, register, domain, grammar_patterns,
          collocations, usage_notes, regional_variants
        - force: Regenerate even if data exists

    Returns:
        Updated definition with regenerated components.

    Errors:
        400: Invalid component names
        404: Definition or word not found

    """
    # Get definition
    definition = await repo.get(definition_id)

    # Type assertion for mypy - repo.get raises HTTPException if not found
    assert definition is not None

    # Get AI connector
    ai = get_openai_connector()

    # Map component names to functions
    component_functions: dict[str, Callable[..., Any]] = {
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
                    ),
                ],
            ).model_dump(),
        )

    # Get word for context

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
                    ),
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

            # Generate examples using AI connector
            examples_response = await ai.generate_examples(
                word=word.text,
                part_of_speech=definition.part_of_speech,
                definition=definition.text,
                count=3,
            )
            # Save examples using repository method
            assert definition.id is not None  # Definition from database should have ID
            example_docs = await repo.batch_add_examples(
                definition.id,
                examples_response.example_sentences,
                example_type="generated",
            )
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
                # Update definition field with AI result
                definition_data = {component: result}
                from ....api.core.protocols import TypedFieldUpdater

                TypedFieldUpdater.update_fields(definition, definition_data)

            updates[component] = result

    # Save definition
    definition.version += 1
    await definition.save()

    return ResourceResponse(
        data=definition.model_dump(mode="json"),
        metadata={
            "regenerated_components": list(request.components),
            "version": definition.version,
            "updated_at": definition.updated_at,
        },
    )


@router.post("/batch/regenerate", response_model=dict[str, Any])
async def batch_regenerate_components(
    request: BatchComponentUpdate,
    repo: DefinitionRepository = Depends(get_definition_repo),
) -> dict[str, Any]:
    """Batch AI-regenerate components.

    Body:
        - definition_ids: List of definition IDs (max 100)
        - components: Components to regenerate
        - force: Force regeneration
        - parallel: Process in parallel

    Returns:
        Processing summary and results by word.

    """
    # Get definitions
    definition_oids: list[PydanticObjectId | str] = [
        PydanticObjectId(id_str) if isinstance(id_str, str) else id_str
        for id_str in request.definition_ids
    ]
    definitions = await repo.get_many(definition_oids)

    if len(definitions) != len(request.definition_ids):
        raise HTTPException(404, "Some definitions not found")

    # Get AI connector
    ai = get_openai_connector()

    # Group definitions by word

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
        # Convert string components to SynthesisComponent enum
        synthesis_components = (
            {SynthesisComponent(comp) for comp in request.components}
            if request.components
            else None
        )

        await enhance_definitions_parallel(
            word_definitions,
            word,
            ai,
            components=synthesis_components,
            force_refresh=request.force,
        )
        # enhance_definitions_parallel modifies definitions in place
        all_results[str(word_id)] = {"processed": len(word_definitions)}

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
        "image_ids",
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
