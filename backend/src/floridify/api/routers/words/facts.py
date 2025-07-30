"""Facts API - CRUD operations and generation for word facts."""

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from ....ai import get_openai_connector
from ....ai.synthesis_functions import generate_facts
from ....models import Definition, Fact, Word
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
from ...middleware.rate_limiting import ai_limiter, get_client_key
from ...repositories.fact_repository import (
    FactCreate,
    FactFilter,
    FactRepository,
    FactUpdate,
)

router = APIRouter(prefix="/facts", tags=["facts"])

# Allowed fact categories
ALLOWED_CATEGORIES = {"etymology", "cultural", "linguistic", "historical", "usage", "technical"}


def get_fact_repo() -> FactRepository:
    """Dependency to get fact repository."""
    return FactRepository()


class FactQueryParams(BaseModel):
    """Query parameters for listing facts."""

    word_id: str | None = Field(None, description="Filter by word ID")
    category: str | None = Field(None, description="Filter by category")
    has_source: bool | None = Field(None, description="Filter by source presence")
    confidence_score_min: float | None = Field(
        None, ge=0, le=1, description="Minimum confidence score"
    )


class FactGenerationRequest(BaseModel):
    """Request for generating facts about a word."""

    count: int = Field(5, ge=1, le=10, description="Number of facts to generate")
    categories: list[str] | None = Field(
        default=None,
        description="Specific categories to focus on",
        examples=[["etymology", "cultural", "linguistic", "historical"]],
    )
    context_words: list[str] | None = Field(None, description="Related words for context")


@router.get("", response_model=ListResponse[Fact])
async def list_facts(
    repo: FactRepository = Depends(get_fact_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    params: FactQueryParams = Depends(),
) -> ListResponse[Fact]:
    """List facts with filtering and pagination."""
    # Validate category if provided
    if params.category and params.category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            400, f"Invalid category. Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    # Build filter
    filter_params = FactFilter(
        word_id=params.word_id,
        category=params.category,
        has_source=params.has_source,
        confidence_score_min=params.confidence_score_min,
    )

    # Get data
    facts, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )

    # Apply field selection
    items = []
    for fact in facts:
        item = fact.model_dump()
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
async def create_fact(
    data: FactCreate,
    repo: FactRepository = Depends(get_fact_repo),
) -> ResourceResponse:
    """Create a new fact."""
    fact = await repo.create(data)

    return ResourceResponse(
        data=fact.model_dump(),
        links={
            "self": f"/facts/{fact.id}",
            "word": f"/words/{fact.word_id}",
        },
    )


@router.get("/{fact_id}", response_model=ResourceResponse)
async def get_fact(
    fact_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: FactRepository = Depends(get_fact_repo),
    fields: FieldSelection = Depends(get_fields),
) -> Response | ResourceResponse:
    """Get a single fact by ID."""
    fact = await repo.get(fact_id, raise_on_missing=True)
    assert fact is not None
    fact_dict = fact.model_dump()

    # Apply field selection
    fact_dict = fields.apply_to_dict(fact_dict)

    # Build response
    response_data = ResourceResponse(
        data=fact_dict,
        metadata={
            "version": fact_dict.get("version", 1),
            "confidence_score": fact_dict.get("confidence_score"),
            "category": fact_dict.get("category"),
        },
        links={
            "self": f"/facts/{fact_id}",
            "word": f"/words/{fact.word_id}",
        },
    )

    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag

    # Check if Not Modified
    if check_etag(request, etag):
        return Response(status_code=304)

    return response_data


@router.put("/{fact_id}", response_model=ResourceResponse)
async def update_fact(
    fact_id: PydanticObjectId,
    data: FactUpdate,
    repo: FactRepository = Depends(get_fact_repo),
) -> ResourceResponse:
    """Update a fact."""
    fact = await repo.update(fact_id, data)

    return ResourceResponse(
        data=fact.model_dump(),
        metadata={
            "version": fact.version,
            "updated_at": fact.updated_at,
        },
    )


@router.delete("/{fact_id}", status_code=204, response_model=None)
async def delete_fact(
    fact_id: PydanticObjectId,
    repo: FactRepository = Depends(get_fact_repo),
) -> None:
    """Delete a fact."""
    await repo.delete(fact_id)


@router.post("/word/{word_id}/generate", response_model=list[ResourceResponse])
async def generate_facts_for_word(
    word_id: str,
    fact_request: FactGenerationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    repo: FactRepository = Depends(get_fact_repo),
) -> list[ResourceResponse]:
    """Generate interesting facts about a word."""
    # Check AI rate limit (estimate ~1500 tokens per fact)
    client_key = get_client_key(request)
    allowed, headers = await ai_limiter.check_request_allowed(
        client_key, estimated_tokens=1500 * fact_request.count
    )

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="AI rate limit exceeded",
            headers=headers,
        )

    # Get word
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(404, "Word not found")

    # Get AI connector
    ai = get_openai_connector()

    # Get definitions for the word
    definitions = await Definition.find(Definition.word_id == str(word.id)).to_list()

    # Generate facts
    facts = await generate_facts(
        word,
        definitions,
        ai,
        count=fact_request.count,
    )

    # Create fact documents
    responses = []
    for fact_obj in facts:
        # Save the fact (it already has proper fields)
        await fact_obj.create()

        responses.append(
            ResourceResponse(
                data=fact_obj.model_dump(),
                links={
                    "self": f"/facts/{fact_obj.id}",
                    "word": f"/words/{fact_obj.word_id}",
                },
            )
        )

    return responses


@router.get("/categories/{category}", response_model=ListResponse[Fact])
async def get_facts_by_category(
    category: str,
    limit: int = Query(50, ge=1, le=200),
    repo: FactRepository = Depends(get_fact_repo),
) -> ListResponse[Fact]:
    """Get facts by category across all words."""
    # Validate category against allowed list
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            400, f"Invalid category. Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    facts = await repo.find_by_category(category, limit)

    return ListResponse(
        items=[f.model_dump() for f in facts],
        total=len(facts),
        offset=0,
        limit=limit,
    )
