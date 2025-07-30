"""Examples API - CRUD operations for example sentences."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ....ai import get_openai_connector
from ....ai.synthesis_functions import generate_examples
from ....models import Definition, Example, Word
from ...core import (
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
from ...repositories.example_repository import (
    ExampleCreate,
    ExampleFilter,
    ExampleRepository,
    ExampleUpdate,
)

router = APIRouter(prefix="/examples", tags=["examples"])


def get_example_repo() -> ExampleRepository:
    """Dependency to get example repository."""
    return ExampleRepository()


class ExampleQueryParams(BaseModel):
    """Query parameters for listing examples."""

    word_id: str | None = Field(None, description="Filter by word ID")
    definition_id: str | None = Field(None, description="Filter by definition ID")
    is_ai_generated: bool | None = Field(None, description="Filter by AI generation status")
    can_regenerate: bool | None = Field(None, description="Filter by regeneration capability")
    has_literature_source: bool | None = Field(
        None, description="Filter by literature source presence"
    )
    quality_score_min: float | None = Field(None, ge=0, le=1, description="Minimum quality score")


class ExampleGenerationRequest(BaseModel):
    """Request for generating new examples."""

    count: int = Field(3, ge=1, le=10, description="Number of examples to generate")
    style: str | None = Field(None, description="Style of examples (formal, casual, technical)")
    context: str | None = Field(None, description="Additional context for generation")


class BatchExampleUpdate(BaseModel):
    """Batch update request for examples."""

    example_ids: list[str] = Field(..., description="Example IDs to update")
    quality_scores: dict[str, float] | None = Field(None, description="Quality scores by ID")
    mark_regeneratable: bool | None = Field(None, description="Mark as regeneratable")


@router.get("", response_model=ListResponse[Example])
async def list_examples(
    repo: ExampleRepository = Depends(get_example_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    params: ExampleQueryParams = Depends(),
) -> ListResponse[Example]:
    """List examples with filtering and pagination."""
    # Build filter
    filter_params = ExampleFilter(
        word_id=params.word_id,
        definition_id=params.definition_id,
        is_ai_generated=params.is_ai_generated,
        can_regenerate=params.can_regenerate,
        has_literature_source=params.has_literature_source,
        quality_score_min=params.quality_score_min,
    )

    # Get data
    examples, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )

    # Apply field selection
    items = []
    for example in examples:
        item = example.model_dump()
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
async def create_example(
    data: ExampleCreate,
    repo: ExampleRepository = Depends(get_example_repo),
) -> ResourceResponse:
    """Create a new example."""
    example = await repo.create(data)

    return ResourceResponse(
        data=example.model_dump(),
        links={
            "self": f"/examples/{example.id}",
            "word": f"/words/{example.word_id}",
            "definition": f"/definitions/{example.definition_id}",
        },
    )


@router.get("/{example_id}", response_model=ResourceResponse)
async def get_example(
    example_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: ExampleRepository = Depends(get_example_repo),
    fields: FieldSelection = Depends(get_fields),
) -> Response | ResourceResponse:
    """Get a single example by ID."""
    example = await repo.get(example_id, raise_on_missing=True)
    assert example is not None
    example_dict = example.model_dump()

    # Apply field selection
    example_dict = fields.apply_to_dict(example_dict)

    # Build response
    response_data = ResourceResponse(
        data=example_dict,
        metadata={
            "version": example_dict.get("version", 1),
            "quality_score": example_dict.get("quality_score"),
            "can_regenerate": example_dict.get("can_regenerate", True),
        },
        links={
            "self": f"/examples/{example_id}",
            "word": f"/words/{example.word_id}",
            "definition": f"/definitions/{example.definition_id}",
        },
    )

    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag

    # Check if Not Modified
    if check_etag(request, etag):
        return Response(status_code=304)

    return response_data


@router.put("/{example_id}", response_model=ResourceResponse)
async def update_example(
    example_id: PydanticObjectId,
    data: ExampleUpdate,
    repo: ExampleRepository = Depends(get_example_repo),
) -> ResourceResponse:
    """Update an example."""
    example = await repo.update(example_id, data)

    return ResourceResponse(
        data=example.model_dump(),
        metadata={
            "version": example.version,
            "updated_at": example.updated_at,
        },
    )


@router.delete("/{example_id}", status_code=204, response_model=None)
async def delete_example(
    example_id: PydanticObjectId,
    repo: ExampleRepository = Depends(get_example_repo),
) -> None:
    """Delete an example."""
    await repo.delete(example_id)


@router.post("/definition/{definition_id}/generate", response_model=list[ResourceResponse])
async def generate_examples_for_definition(
    definition_id: str,
    request: ExampleGenerationRequest,
    repo: ExampleRepository = Depends(get_example_repo),
) -> list[ResourceResponse]:
    """Generate new examples for a definition."""
    # Get definition and word
    definition = await Definition.get(definition_id)
    if not definition:
        raise HTTPException(404, "Definition not found")

    word = await Word.get(definition.word_id)
    if not word:
        raise HTTPException(404, "Word not found")

    # Get AI connector
    ai = get_openai_connector()

    # Generate examples
    example_texts = await generate_examples(
        word.text,
        definition,
        ai,
        count=request.count,
    )

    # Create example documents
    responses = []
    created_examples = []
    for example_text in example_texts:
        assert definition.id is not None  # Definition from database should have ID
        example = Example(
            word_id=definition.word_id,
            definition_id=definition.id,
            text=example_text,
            type="generated",  # AI-generated example
            quality_score=0.8,  # Default quality score for AI-generated examples
        )
        await example.create()
        created_examples.append(example)

        responses.append(
            ResourceResponse(
                data=example.model_dump(),
                links={
                    "self": f"/examples/{example.id}",
                    "word": f"/words/{example.word_id}",
                    "definition": f"/definitions/{example.definition_id}",
                },
            )
        )

    # Update definition with new example IDs
    definition.example_ids.extend([ex.id for ex in created_examples if ex.id is not None])
    await definition.save()

    return responses


@router.post("/batch/update", response_model=dict[str, Any])
async def batch_update_examples(
    request: BatchExampleUpdate,
    repo: ExampleRepository = Depends(get_example_repo),
) -> dict[str, Any]:
    """Batch update examples."""
    updated = 0

    # Update quality scores if provided
    if request.quality_scores:
        scores = [(PydanticObjectId(id), score) for id, score in request.quality_scores.items()]
        updated = await repo.update_quality_scores(scores)

    # Update regeneratable flag if provided
    if request.mark_regeneratable is not None:
        for example_id in request.example_ids:
            example = await repo.get(PydanticObjectId(example_id), raise_on_missing=False)
            if example:
                example.can_regenerate = request.mark_regeneratable
                await example.save()
                updated += 1

    return {
        "updated": updated,
        "total": len(request.example_ids),
    }
