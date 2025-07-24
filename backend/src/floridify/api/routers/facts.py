"""Facts API - CRUD operations and generation for word facts."""

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from floridify.ai.connector import get_openai_connector
from floridify.ai.synthesis_functions import generate_facts
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
from floridify.api.repositories.fact_repository import (
    FactCreate,
    FactFilter,
    FactRepository,
    FactUpdate,
)
from floridify.models.models import Fact, Word

router = APIRouter(prefix="/facts", tags=["facts"])


def get_fact_repo() -> FactRepository:
    """Dependency to get fact repository."""
    return FactRepository()


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


class FactGenerationRequest(BaseModel):
    """Request for generating facts about a word."""
    
    count: int = Field(5, ge=1, le=10, description="Number of facts to generate")
    categories: list[str] | None = Field(
        None,
        description="Specific categories to focus on",
        example=["etymology", "cultural", "linguistic", "historical"]
    )
    context_words: list[str] | None = Field(
        None,
        description="Related words for context"
    )


@router.get("", response_model=ListResponse[Fact])
@handle_api_errors
async def list_facts(
    request: Request,
    response: Response,
    repo: FactRepository = Depends(get_fact_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    # Filter parameters
    word_id: str | None = Query(None),
    category: str | None = Query(None),
    has_source: bool | None = Query(None),
    confidence_score_min: float | None = Query(None, ge=0, le=1),
) -> ListResponse[Fact]:
    """List facts with filtering and pagination."""
    # Build filter
    filter_params = FactFilter(
        word_id=word_id,
        category=category,
        has_source=has_source,
        confidence_score_min=confidence_score_min,
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
        fact_dict = fact.model_dump()
        fact_dict = fields.apply_to_dict(fact_dict)
        items.append(fact_dict)
    
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
        }
    )


@router.get("/{fact_id}", response_model=ResourceResponse)
@handle_api_errors
async def get_fact(
    fact_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: FactRepository = Depends(get_fact_repo),
    fields: FieldSelection = Depends(get_fields),
) -> ResourceResponse:
    """Get a single fact by ID."""
    fact = await repo.get(fact_id)
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
        }
    )
    
    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag
    
    # Check if Not Modified
    if check_etag(request, etag):
        return Response(status_code=304)
    
    return response_data


@router.put("/{fact_id}", response_model=ResourceResponse)
@handle_api_errors
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
        }
    )


@router.delete("/{fact_id}", status_code=204)
@handle_api_errors
async def delete_fact(
    fact_id: PydanticObjectId,
    repo: FactRepository = Depends(get_fact_repo),
) -> None:
    """Delete a fact."""
    await repo.delete(fact_id)


@router.post("/word/{word_id}/generate", response_model=list[ResourceResponse])
@handle_api_errors
async def generate_facts_for_word(
    word_id: str,
    request: FactGenerationRequest,
    background_tasks: BackgroundTasks,
    repo: FactRepository = Depends(get_fact_repo),
) -> list[ResourceResponse]:
    """Generate interesting facts about a word."""
    # Get word
    word = await Word.get(word_id)
    if not word:
        raise HTTPException(404, "Word not found")
    
    # Get AI connector
    ai = await get_openai_connector()
    
    # Generate facts
    fact_data_list = await generate_facts(
        word,
        ai,
        count=request.count,
        context_words=request.context_words,
    )
    
    # Create fact documents
    responses = []
    for fact_data in fact_data_list:
        # Extract category if present in the fact text
        category = None
        if "etymology" in fact_data["text"].lower():
            category = "etymology"
        elif "cultur" in fact_data["text"].lower():
            category = "cultural"
        elif "histor" in fact_data["text"].lower():
            category = "historical"
        elif "linguistic" in fact_data["text"].lower():
            category = "linguistic"
        
        fact = Fact(
            word_id=str(word.id),
            text=fact_data["text"],
            category=category,
            confidence_score=fact_data.get("confidence_score", 0.8),
        )
        await fact.create()
        
        responses.append(ResourceResponse(
            data=fact.model_dump(),
            links={
                "self": f"/facts/{fact.id}",
                "word": f"/words/{fact.word_id}",
            }
        ))
    
    return responses


@router.get("/categories/{category}", response_model=ListResponse[Fact])
@handle_api_errors
async def get_facts_by_category(
    category: str,
    limit: int = Query(50, ge=1, le=200),
    repo: FactRepository = Depends(get_fact_repo),
) -> ListResponse[Fact]:
    """Get facts by category across all words."""
    facts = await repo.find_by_category(category, limit)
    
    return ListResponse(
        items=[f.model_dump() for f in facts],
        total=len(facts),
        offset=0,
        limit=limit,
    )