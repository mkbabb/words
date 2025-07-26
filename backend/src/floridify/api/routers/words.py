"""Words API - Comprehensive CRUD operations."""

from datetime import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ...constants import Language
from ...models import Word
from ..core import (
    ErrorResponse,
    FieldSelection,
    ListResponse,
    PaginationParams,
    ResourceResponse,
    SortParams,
    cached_endpoint,
    check_etag,
    get_etag,
    handle_api_errors,
)
from ..repositories import (
    WordCreate,
    WordFilter,
    WordRepository,
    WordUpdate,
)

router = APIRouter()


def get_word_repo() -> WordRepository:
    """Dependency to get word repository."""
    return WordRepository()


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


@router.get("", response_model=ListResponse[Word])
async def list_words(
    repo: WordRepository = Depends(get_word_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    # Filter parameters
    text: str | None = Query(None),
    text_pattern: str | None = Query(None),
    language: Language | None = Query(None),
    offensive_flag: bool | None = Query(None),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
) -> ListResponse[Word]:
    """
    List words with filtering, sorting, and pagination.
    """
    # Build filter
    filter_params = WordFilter(
        text=text,
        text_pattern=text_pattern,
        language=language,
        offensive_flag=offensive_flag,
        created_after=created_after,
        created_before=created_before,
    )

    # Get data
    words, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )

    # Apply field selection and expansions
    items = []
    for word in words:
        item = word.model_dump()
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
async def create_word(
    data: WordCreate,
    repo: WordRepository = Depends(get_word_repo),
) -> ResourceResponse:
    """Create a new word."""
    # Check if word already exists
    existing = await repo.find_by_text(data.text, data.language)
    if existing:
        raise HTTPException(
            409,
            detail=ErrorResponse(
                error="Word already exists",
                details=[
                    {
                        "field": "text",
                        "message": f"Word '{data.text}' already exists in {data.language}",
                        "code": "duplicate_word",
                    }
                ],
            ).model_dump(),
        )

    # Create word
    word = await repo.create(data)

    return ResourceResponse(
        data=word.model_dump(),
        links={
            "self": f"/words/{word.id}",
            "definitions": f"/words/{word.id}/definitions",
        },
    )


@router.get("/{word_id}", response_model=ResourceResponse)
@handle_api_errors
async def get_word(
    word_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: WordRepository = Depends(get_word_repo),
    fields: FieldSelection = Depends(get_fields),
) -> ResourceResponse:
    """Get a single word by ID."""
    # Get word with counts
    word_data = await repo.get_with_counts(word_id)

    # Apply field selection
    word_data = fields.apply_to_dict(word_data)

    # Handle expansions
    if fields.expand:
        if "definitions" in fields.expand:
            from ..repositories import DefinitionRepository

            def_repo = DefinitionRepository()
            definitions = await def_repo.find_by_word(str(word_id))
            word_data["definitions"] = [d.model_dump() for d in definitions]

    # Build response
    response_data = ResourceResponse(
        data=word_data,
        metadata={
            "version": word_data.get("version", 1),
            "last_modified": word_data.get("updated_at"),
        },
        links={
            "self": f"/words/{word_id}",
            "definitions": f"/words/{word_id}/definitions",
            "facts": f"/words/{word_id}/facts",
            "pronunciation": f"/words/{word_id}/pronunciation",
        },
    )

    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag

    # Check if Not Modified
    if check_etag(request, etag):
        return Response(status_code=304)

    return response_data


@router.put("/{word_id}", response_model=ResourceResponse)
@handle_api_errors
async def update_word(
    word_id: PydanticObjectId,
    data: WordUpdate,
    version: int | None = Query(None, description="Version for optimistic locking"),
    repo: WordRepository = Depends(get_word_repo),
) -> ResourceResponse:
    """Update a word with optional optimistic locking."""
    word = await repo.update(word_id, data, version)

    return ResourceResponse(
        data=word.model_dump(),
        metadata={
            "version": word.version,
            "updated_at": word.updated_at,
        },
    )


@router.delete("/{word_id}", status_code=204, response_model=None)
@handle_api_errors
async def delete_word(
    word_id: PydanticObjectId,
    cascade: bool = Query(False, description="Delete related documents"),
    repo: WordRepository = Depends(get_word_repo),
) -> None:
    """Delete a word, optionally with cascade."""
    await repo.delete(word_id, cascade=cascade)


@router.get("/search/{query}", response_model=ListResponse[Word])
@handle_api_errors
async def search_words(
    query: str,
    language: Language | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    repo: WordRepository = Depends(get_word_repo),
) -> ListResponse[Word]:
    """Search words by text pattern."""
    words = await repo.search(query, language, limit)

    return ListResponse(
        items=[w.model_dump() for w in words],
        total=len(words),
        offset=0,
        limit=limit,
    )
