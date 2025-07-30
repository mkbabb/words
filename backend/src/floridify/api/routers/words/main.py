"""Words API - Comprehensive CRUD operations."""

from datetime import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from ....constants import Language
from ....models import Word
from ...core import (
    ErrorDetail,
    ErrorResponse,
    FieldSelection,
    ListResponse,
    PaginationParams,
    ResourceResponse,
    ResponseBuilder,
    SortParams,
    check_etag,
    get_etag,
    get_fields,
    get_pagination,
    get_sort,
)
from ...repositories import (
    DefinitionRepository,
    WordCreate,
    WordFilter,
    WordRepository,
    WordUpdate,
)

router = APIRouter()


def get_word_repo() -> WordRepository:
    """Dependency to get word repository."""
    return WordRepository()


class WordQueryParams(BaseModel):
    """Query parameters for listing words."""
    
    text: str | None = Field(None, description="Exact text match")
    text_pattern: str | None = Field(None, description="Partial text match")
    language: Language | None = Field(None, description="Language filter")
    offensive_flag: bool | None = Field(None, description="Offensive content filter")
    created_after: datetime | None = Field(None, description="Created after date")
    created_before: datetime | None = Field(None, description="Created before date")


@router.get("", response_model=ListResponse[Word])
async def list_words(
    repo: WordRepository = Depends(get_word_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    params: WordQueryParams = Depends(),
) -> ListResponse[Word]:
    """Retrieve paginated word list with filtering and sorting.
    
    Query Parameters:
        - offset: Skip first N results (default: 0)
        - limit: Maximum results to return (default: 20, max: 100)
        - sort_by: Field to sort by (e.g., 'text', 'created_at')
        - sort_order: Sort direction ('asc' or 'desc')
        - text: Exact text match filter
        - text_pattern: Partial text match filter
        - language: Language code filter (e.g., 'en', 'es')
        - offensive_flag: Filter by offensive content flag
        - created_after/before: Date range filters
    
    Returns:
        Paginated list with items, total count, offset, and limit.
    
    Example:
        GET /api/v1/words?language=en&limit=10&sort_by=text
    """
    # Build filter
    filter_params = WordFilter(
        text=params.text,
        text_pattern=params.text_pattern,
        language=params.language,
        offensive_flag=params.offensive_flag,
        created_after=params.created_after,
        created_before=params.created_before,
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

    # Build response using ResponseBuilder
    return ResponseBuilder.build_list_response(
        items=words,  # Pass the original documents, not the dicts
        total=total,
        pagination=pagination,
        resource_type="word",
    )


@router.post("", response_model=ResourceResponse, status_code=201)

async def create_word(
    data: WordCreate,
    repo: WordRepository = Depends(get_word_repo),
) -> ResourceResponse:
    """Create new word entry.
    
    Body:
        - text: Word text (required)
        - normalized: Normalized form (required)
        - language: Language code (required)
        - offensive_flag: Mark as offensive (optional)
        - first_known_use: Historical first use (optional)
    
    Returns:
        Created word with links to related resources.
    
    Errors:
        409: Word already exists in specified language
        422: Invalid input data
    """
    # Check if word already exists
    existing = await repo.find_by_text(data.text, data.language)
    if existing:
        raise HTTPException(
            409,
            detail=ErrorResponse(
                error="Word already exists",
                details=[
                    ErrorDetail(
                        field="text",
                        message=f"Word '{data.text}' already exists in {data.language}",
                        code="duplicate_word",
                    )
                ],
            ).model_dump(),
        )

    # Create word
    word = await repo.create(data)

    return ResponseBuilder.build_resource_response(
        data=word,
        resource_type="word",
        version=word.version,
        updated_at=word.updated_at,
        additional_links={
            "definitions": f"/words/{word.id}/definitions",
        },
    )


@router.get("/{word_id}", response_model=ResourceResponse)

async def get_word(
    word_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: WordRepository = Depends(get_word_repo),
    fields: FieldSelection = Depends(get_fields),
) -> Response | ResourceResponse:
    """Retrieve word details by ID.
    
    Path Parameters:
        - word_id: MongoDB ObjectId of word
    
    Query Parameters:
        - include: Comma-separated fields to include
        - exclude: Comma-separated fields to exclude
        - expand: Comma-separated relations to expand (e.g., 'definitions')
    
    Returns:
        Word data with metadata and resource links.
        
    Headers:
        - ETag: Entity tag for caching
        - Returns 304 if If-None-Match matches current ETag
    """
    # Get word with counts
    word_data = await repo.get_with_counts(word_id)

    # Apply field selection
    word_data = fields.apply_to_dict(word_data)

    # Handle expansions
    if fields.expand:
        if "definitions" in fields.expand:
            def_repo = DefinitionRepository()
            definitions = await def_repo.find_by_word(str(word_id))
            word_data["definitions"] = [d.model_dump() for d in definitions]

    # Build response
    response_data = ResponseBuilder.build_resource_response(
        data=word_data,
        resource_type="word",
        resource_id=str(word_id),
        version=word_data.get("version", 1),
        updated_at=word_data.get("updated_at"),
        additional_links={
            "definitions": f"/words/{word_id}/definitions",
            "facts": f"/words/{word_id}/facts",
            "pronunciation": f"/words/{word_id}/pronunciation",
        },
    )

    # Apply ETag and check for Not Modified
    if ResponseBuilder.apply_etag(response, response_data.model_dump(), request):
        return Response(status_code=304)

    return response_data


@router.put("/{word_id}", response_model=ResourceResponse)

async def update_word(
    word_id: PydanticObjectId,
    data: WordUpdate,
    version: int | None = Query(None, description="Version for optimistic locking"),
    repo: WordRepository = Depends(get_word_repo),
) -> ResourceResponse:
    """Update word with optimistic concurrency control.
    
    Path Parameters:
        - word_id: MongoDB ObjectId of word
    
    Query Parameters:
        - version: Current version for optimistic locking (optional)
    
    Body:
        Partial update fields (only provided fields are updated)
    
    Returns:
        Updated word with new version number.
    
    Errors:
        409: Version conflict (concurrent modification)
        404: Word not found
    """
    word = await repo.update(word_id, data, version)

    return ResponseBuilder.build_resource_response(
        data=word,
        resource_type="word",
        version=word.version,
        updated_at=word.updated_at,
    )


@router.delete("/{word_id}", status_code=204, response_model=None)

async def delete_word(
    word_id: PydanticObjectId,
    cascade: bool = Query(False, description="Delete related documents"),
    repo: WordRepository = Depends(get_word_repo),
) -> None:
    """Delete word and optionally cascade to related documents.
    
    Path Parameters:
        - word_id: MongoDB ObjectId of word
    
    Query Parameters:
        - cascade: Delete related definitions, examples, facts (default: false)
    
    Returns:
        204 No Content on success
    
    Errors:
        404: Word not found
    """
    await repo.delete(word_id, cascade=cascade)


