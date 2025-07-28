"""WordLists API - Comprehensive CRUD operations for word lists."""

from datetime import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ...list.models import MasteryLevel, WordList
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
)
from ..repositories import (
    WordListCreate,
    WordListFilter,
    WordListRepository,
    WordListUpdate,
    WordAddRequest,
    WordReviewRequest,
    StudySessionRequest,
)

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


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


@router.get("", response_model=ListResponse[WordList])
async def list_wordlists(
    repo: WordListRepository = Depends(get_wordlist_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    fields: FieldSelection = Depends(get_fields),
    # Filter parameters
    name: str | None = Query(None),
    name_pattern: str | None = Query(None),
    owner_id: str | None = Query(None),
    is_public: bool | None = Query(None),
    has_tag: str | None = Query(None),
    mastery_level: MasteryLevel | None = Query(None),
    min_words: int | None = Query(None, ge=0),
    max_words: int | None = Query(None, ge=0),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    accessed_after: datetime | None = Query(None),
) -> ListResponse[WordList]:
    """Retrieve paginated word list collection with filtering and sorting.
    
    Query Parameters:
        - offset: Skip first N results (default: 0)
        - limit: Maximum results to return (default: 20, max: 100)
        - sort_by: Field to sort by (e.g., 'name', 'created_at', 'last_accessed')
        - sort_order: Sort direction ('asc' or 'desc')
        - name: Exact name match filter
        - name_pattern: Partial name match filter
        - owner_id: Filter by owner user ID
        - is_public: Filter by public visibility
        - has_tag: Filter by tag presence
        - mastery_level: Filter lists with words at mastery level
        - min_words/max_words: Filter by word count range
        - created_after/before: Date range filters
        - accessed_after: Recently accessed filter
    
    Returns:
        Paginated list with items, total count, offset, and limit.
    
    Example:
        GET /api/v1/wordlists?is_public=true&limit=10&sort_by=last_accessed&sort_order=desc
    """
    # Build filter
    filter_params = WordListFilter(
        name=name,
        name_pattern=name_pattern,
        owner_id=owner_id,
        is_public=is_public,
        has_tag=has_tag,
        mastery_level=mastery_level,
        min_words=min_words,
        max_words=max_words,
        created_after=created_after,
        created_before=created_before,
        accessed_after=accessed_after,
    )

    # Get data
    wordlists, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )

    # Apply field selection
    items = []
    for wordlist in wordlists:
        item = wordlist.model_dump()
        item = fields.apply_to_dict(item)
        items.append(item)

    return ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_wordlist(
    data: WordListCreate,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Create new word list.
    
    Body:
        - name: List name (required)
        - description: List description (optional)
        - words: Initial words to add (optional)
        - tags: Categorization tags (optional)
        - is_public: Public visibility (default: false)
        - owner_id: Owner user ID (optional)
    
    Returns:
        Created word list with learning metadata and links.
    
    Errors:
        409: Word list with same content hash already exists
        422: Invalid input data
    """
    # Create word list
    wordlist = await repo.create(data)

    return ResourceResponse(
        data=wordlist.model_dump(),
        links={
            "self": f"/wordlists/{wordlist.id}",
            "words": f"/wordlists/{wordlist.id}/words",
            "statistics": f"/wordlists/{wordlist.id}/statistics",
            "due": f"/wordlists/{wordlist.id}/due",
        },
    )


@router.get("/{wordlist_id}", response_model=ResourceResponse)
async def get_wordlist(
    wordlist_id: PydanticObjectId,
    request: Request,
    response: Response,
    repo: WordListRepository = Depends(get_wordlist_repo),
    fields: FieldSelection = Depends(get_fields),
) -> Response | ResourceResponse:
    """Retrieve word list details by ID.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Query Parameters:
        - include: Comma-separated fields to include
        - exclude: Comma-separated fields to exclude
        - expand: Comma-separated relations to expand (e.g., 'statistics')
    
    Returns:
        Word list data with learning metadata and resource links.
        
    Headers:
        - ETag: Entity tag for caching
        - Returns 304 if If-None-Match matches current ETag
    """
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    if wordlist is None:
        raise HTTPException(404, "WordList not found")
    
    # Mark as accessed
    wordlist.mark_accessed()
    await wordlist.save()
    
    wordlist_data = wordlist.model_dump()

    # Apply field selection
    wordlist_data = fields.apply_to_dict(wordlist_data)

    # Handle expansions
    if fields.expand:
        if "statistics" in fields.expand:
            stats = await repo.get_statistics(wordlist_id)
            wordlist_data["statistics"] = stats

    # Build response
    response_data = ResourceResponse(
        data=wordlist_data,
        metadata={
            "last_modified": wordlist_data.get("updated_at"),
            "hash_id": wordlist_data.get("hash_id"),
        },
        links={
            "self": f"/wordlists/{wordlist_id}",
            "words": f"/wordlists/{wordlist_id}/words",
            "statistics": f"/wordlists/{wordlist_id}/statistics",
            "due": f"/wordlists/{wordlist_id}/due",
            "review": f"/wordlists/{wordlist_id}/review",
            "study": f"/wordlists/{wordlist_id}/study",
        },
    )

    # Set ETag
    etag = get_etag(response_data.model_dump())
    response.headers["ETag"] = etag

    # Check if Not Modified
    if check_etag(request, etag):
        return Response(status_code=304)

    return response_data


@router.put("/{wordlist_id}", response_model=ResourceResponse)
async def update_wordlist(
    wordlist_id: PydanticObjectId,
    data: WordListUpdate,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Update word list metadata.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Body:
        Partial update fields (only provided fields are updated)
    
    Returns:
        Updated word list with new metadata.
    
    Errors:
        404: Word list not found
    """
    wordlist = await repo.update(wordlist_id, data)

    return ResourceResponse(
        data=wordlist.model_dump(),
        metadata={
            "updated_at": wordlist.updated_at,
            "hash_id": wordlist.hash_id,
        },
    )


@router.delete("/{wordlist_id}", status_code=204, response_model=None)
async def delete_wordlist(
    wordlist_id: PydanticObjectId,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Delete word list.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Returns:
        204 No Content on success
    
    Errors:
        404: Word list not found
    """
    await repo.delete(wordlist_id, cascade=False)


@router.post("/{wordlist_id}/words", response_model=ResourceResponse)
async def add_words_to_list(
    wordlist_id: PydanticObjectId,
    data: WordAddRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Add words to an existing word list.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Body:
        - words: List of words to add
    
    Returns:
        Updated word list with new words added.
    
    Errors:
        404: Word list not found
    """
    wordlist = await repo.add_words(wordlist_id, data.words)

    return ResourceResponse(
        data=wordlist.model_dump(),
        metadata={
            "words_added": len(data.words),
            "total_unique_words": wordlist.unique_words,
        },
    )


@router.delete("/{wordlist_id}/words/{word}", status_code=204, response_model=None)
async def remove_word_from_list(
    wordlist_id: PydanticObjectId,
    word: str,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Remove a word from a word list.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
        - word: Word text to remove
    
    Returns:
        204 No Content on success
    
    Errors:
        404: Word list not found
    """
    await repo.remove_word(wordlist_id, word)


@router.post("/{wordlist_id}/review", response_model=ResourceResponse)
async def review_word(
    wordlist_id: PydanticObjectId,
    data: WordReviewRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Process a word review session using spaced repetition.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Body:
        - word: Word being reviewed
        - quality: Review quality score (0-5, where 3+ is passing)
    
    Returns:
        Updated word list with review data processed.
    
    Errors:
        404: Word list not found
        422: Invalid quality score
    """
    wordlist = await repo.review_word(wordlist_id, data.word, data.quality)

    return ResourceResponse(
        data=wordlist.model_dump(),
        metadata={
            "word_reviewed": data.word,
            "quality_score": data.quality,
            "total_reviews": wordlist.learning_stats.total_reviews,
        },
    )


@router.post("/{wordlist_id}/visit/{word}", response_model=ResourceResponse)
async def mark_word_visited(
    wordlist_id: PydanticObjectId,
    word: str,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Mark a word as visited/viewed.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
        - word: Word text that was visited
    
    Returns:
        Updated word list with visit recorded.
    
    Errors:
        404: Word list not found
    """
    wordlist = await repo.mark_word_visited(wordlist_id, word)

    return ResourceResponse(
        data=wordlist.model_dump(),
        metadata={
            "word_visited": word,
            "timestamp": wordlist.updated_at,
        },
    )


@router.post("/{wordlist_id}/study", response_model=ResourceResponse)
async def record_study_session(
    wordlist_id: PydanticObjectId,
    data: StudySessionRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Record a study session.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Body:
        - duration_minutes: Study session duration in minutes
    
    Returns:
        Updated word list with study session recorded.
    
    Errors:
        404: Word list not found
    """
    wordlist = await repo.record_study_session(wordlist_id, data.duration_minutes)

    return ResourceResponse(
        data=wordlist.model_dump(),
        metadata={
            "session_duration": data.duration_minutes,
            "total_study_time": wordlist.learning_stats.study_time_minutes,
            "current_streak": wordlist.learning_stats.streak_days,
        },
    )


@router.get("/{wordlist_id}/due", response_model=ListResponse)
async def get_due_words(
    wordlist_id: PydanticObjectId,
    limit: int | None = Query(None, ge=1, le=100),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse:
    """Get words due for review.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Query Parameters:
        - limit: Maximum words to return (optional)
    
    Returns:
        List of words due for review, ordered by urgency.
    
    Errors:
        404: Word list not found
    """
    due_words = await repo.get_due_for_review(wordlist_id, limit)

    return ListResponse(
        items=[w.model_dump() for w in due_words],
        total=len(due_words),
        offset=0,
        limit=limit or len(due_words),
    )


@router.get("/{wordlist_id}/mastery/{level}", response_model=ListResponse)
async def get_words_by_mastery(
    wordlist_id: PydanticObjectId,
    level: MasteryLevel,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse:
    """Get words at a specific mastery level.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
        - level: Mastery level (bronze, silver, gold)
    
    Returns:
        List of words at the specified mastery level.
    
    Errors:
        404: Word list not found
    """
    words = await repo.get_by_mastery(wordlist_id, level)

    return ListResponse(
        items=[w.model_dump() for w in words],
        total=len(words),
        offset=0,
        limit=len(words),
    )


@router.get("/{wordlist_id}/statistics", response_model=ResourceResponse)
async def get_wordlist_statistics(
    wordlist_id: PydanticObjectId,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Get detailed learning statistics for a word list.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Returns:
        Comprehensive statistics including mastery distribution, 
        learning progress, and performance metrics.
    
    Errors:
        404: Word list not found
    """
    stats = await repo.get_statistics(wordlist_id)

    return ResourceResponse(
        data=stats,
        metadata={
            "generated_at": datetime.utcnow(),
        },
    )


@router.get("/search/{query}", response_model=ListResponse[WordList])
async def search_wordlists(
    query: str,
    limit: int = Query(10, ge=1, le=50),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[WordList]:
    """Search word lists by name pattern.
    
    Path Parameters:
        - query: Search query text
    
    Query Parameters:
        - limit: Maximum results (default: 10, max: 50)
    
    Returns:
        List of matching word lists with relevance ordering.
    
    Example:
        GET /api/v1/wordlists/search/vocabulary?limit=5
    """
    wordlists = await repo.search_by_name(query, limit)

    return ListResponse(
        items=[w.model_dump() for w in wordlists],
        total=len(wordlists),
        offset=0,
        limit=limit,
    )


@router.get("/popular", response_model=ListResponse[WordList])
async def get_popular_wordlists(
    limit: int = Query(10, ge=1, le=50),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[WordList]:
    """Get most popular/accessed public word lists.
    
    Query Parameters:
        - limit: Maximum results (default: 10, max: 50)
    
    Returns:
        List of popular word lists ordered by access frequency.
    """
    wordlists = await repo.get_popular(limit)

    return ListResponse(
        items=[w.model_dump() for w in wordlists],
        total=len(wordlists),
        offset=0,
        limit=limit,
    )