"""WordLists API - Comprehensive CRUD operations for word lists."""

from datetime import datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from pydantic import BaseModel, Field
from typing import Literal

from ...wordlist.models import MasteryLevel, WordList
from ...wordlist.parser import parse_file, generate_name
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


class WordListQueryParams(BaseModel):
    """Query parameters for listing wordlists."""
    
    # Pagination
    offset: int = Field(0, ge=0, description="Skip first N results")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    
    # Sorting
    sort_by: str | None = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort direction")
    
    # Field selection
    include: str | None = Field(None, description="Comma-separated fields to include")
    exclude: str | None = Field(None, description="Comma-separated fields to exclude")
    expand: str | None = Field(None, description="Comma-separated relations to expand")
    
    # Filters
    name: str | None = Field(None, description="Exact name match")
    name_pattern: str | None = Field(None, description="Partial name match")
    owner_id: str | None = Field(None, description="Filter by owner ID")
    is_public: bool | None = Field(None, description="Filter by public visibility")
    has_tag: str | None = Field(None, description="Filter by tag presence")
    mastery_level: MasteryLevel | None = Field(None, description="Filter by mastery level")
    min_words: int | None = Field(None, ge=0, description="Minimum word count")
    max_words: int | None = Field(None, ge=0, description="Maximum word count")
    created_after: datetime | None = Field(None, description="Created after date")
    created_before: datetime | None = Field(None, description="Created before date")
    accessed_after: datetime | None = Field(None, description="Accessed after date")

    def to_pagination(self) -> PaginationParams:
        """Convert to pagination params."""
        return PaginationParams(offset=self.offset, limit=self.limit)
    
    def to_sort(self) -> SortParams:
        """Convert to sort params."""
        return SortParams(sort_by=self.sort_by, sort_order=self.sort_order)
    
    def to_fields(self) -> FieldSelection:
        """Convert to field selection."""
        return FieldSelection(
            include=set(self.include.split(",")) if self.include else None,
            exclude=set(self.exclude.split(",")) if self.exclude else None,
            expand=set(self.expand.split(",")) if self.expand else None,
        )
    
    def to_filter(self) -> WordListFilter:
        """Convert to filter params."""
        return WordListFilter(
            name=self.name,
            name_pattern=self.name_pattern,
            owner_id=self.owner_id,
            is_public=self.is_public,
            has_tag=self.has_tag,
            mastery_level=self.mastery_level,
            min_words=self.min_words,
            max_words=self.max_words,
            created_after=self.created_after,
            created_before=self.created_before,
            accessed_after=self.accessed_after,
        )




def parse_wordlist_query_params(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str | None = Query(None),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    include: str | None = Query(None),
    exclude: str | None = Query(None),
    expand: str | None = Query(None),
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
) -> WordListQueryParams:
    """Parse wordlist query parameters."""
    return WordListQueryParams(
        offset=offset,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        include=include,
        exclude=exclude,
        expand=expand,
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
    params: WordListQueryParams = Depends(parse_wordlist_query_params),
    repo: WordListRepository = Depends(get_wordlist_repo),
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
    # Get data using converted parameters
    wordlists, total = await repo.list(
        filter_dict=params.to_filter().to_query(),
        pagination=params.to_pagination(),
        sort=params.to_sort(),
    )

    # Apply field selection
    fields = params.to_fields()
    items = []
    for wordlist in wordlists:
        item = wordlist.model_dump()
        item = fields.apply_to_dict(item)
        items.append(item)

    return ListResponse(
        items=items,
        total=total,
        offset=params.offset,
        limit=params.limit,
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
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Retrieve word list metadata by ID (without words)."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    
    # Exclude words from metadata response for performance
    wordlist_data = wordlist.model_dump(mode="json", exclude={"words"})
    
    return ResourceResponse(
        data=wordlist_data,
        links={
            "self": f"/wordlists/{wordlist_id}",
            "words": f"/wordlists/{wordlist_id}/words",
            "statistics": f"/wordlists/{wordlist_id}/statistics",
        },
    )


class WordListFilterCriteria(BaseModel):
    """Filtering criteria for words within a wordlist."""
    
    filters: dict[str, Any] = Field(default_factory=dict, description="Filter criteria")
    sort: list[dict[str, str]] = Field(default_factory=list, description="Sort criteria")
    search: str = Field(default="", description="Search query for corpus-based fuzzy search")


def parse_word_filter_params(
    criteria: str = Query("{}", description="JSON object with filters, sort, and search criteria"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> tuple[WordListFilterCriteria, int, int]:
    """Parse word filtering and sorting parameters."""
    import json
    try:
        criteria_dict = json.loads(criteria) if criteria != "{}" else {}
        # Add debugging
        print(f"DEBUG: Parsed criteria_dict: {criteria_dict}")
        filter_criteria = WordListFilterCriteria(**criteria_dict)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        # Enhanced error handling with logging
        print(f"ERROR: Failed to parse criteria: {e}")
        print(f"Raw criteria: {criteria}")
        filter_criteria = WordListFilterCriteria()
    
    return filter_criteria, offset, limit




@router.get("/{wordlist_id}/words", response_model=ListResponse)
async def get_filtered_words(
    wordlist_id: PydanticObjectId,
    filter_data: tuple[WordListFilterCriteria, int, int] = Depends(parse_word_filter_params),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Get filtered, sorted, and paginated words from a wordlist with corpus search support.
    
    Supports:
    - Corpus-based fuzzy search for word matching
    - Multi-criteria filtering (mastery, temperature, due status)
    - Multi-criteria sorting with priority levels
    - Pagination
    
    Query Parameters:
        - criteria: JSON object with filters, sort, and search properties
        - offset: Starting position for pagination
        - limit: Number of words to return (max 200)
    
    Example:
        GET /wordlists/{id}/words?criteria={"filters":{"mastery_level":["bronze","silver"]},"sort":[{"field":"mastery","direction":"desc"}],"search":"example"}
    """
    criteria, offset, limit = filter_data
    
    # Get wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    if not wordlist:
        raise HTTPException(404, "WordList not found")
    
    # Start with all words
    words = list(wordlist.words)
    
    # Apply corpus search if search query is provided
    if criteria.search and criteria.search.strip():
        try:
            # Get search results from corpus
            search_results = await repo.search_wordlist_corpus(
                wordlist_id=wordlist_id,
                query=criteria.search.strip(),
                max_results=len(words),  # Get all matches
                min_score=0.3,  # Lower threshold for filtering
            )
            
            # Extract matching words from search results
            matching_words = set()
            for result in search_results.get('results', []):
                matching_words.add(result['word'].lower())
            
            # Filter words to only include search matches
            if matching_words:
                words = [w for w in words if w.text.lower() in matching_words]
            else:
                words = []  # No matches found
                
        except Exception as e:
            # If corpus search fails, fall back to simple text matching
            search_term = criteria.search.strip().lower()
            words = [w for w in words if search_term in w.text.lower()]
    
    # Apply filters
    if criteria.filters:
        # Mastery level filter
        if 'mastery_level' in criteria.filters:
            mastery_levels = criteria.filters['mastery_level']
            if isinstance(mastery_levels, list) and mastery_levels:
                words = [w for w in words if w.mastery_level in mastery_levels]
        
        # Temperature filter
        if 'temperature' in criteria.filters:
            temp_filter = criteria.filters['temperature']
            if temp_filter == 'hot':
                words = [w for w in words if w.temperature == 'hot']
        
        # Due for review filter
        if criteria.filters.get('due_for_review'):
            now = datetime.utcnow()
            words = [w for w in words if w.review_data.next_review_date <= now]
    
    # Define sort value function
    def get_sort_value(word, field: str):
        """Get sort value for a field."""
        field_map = {
            'mastery': 'mastery_level',
            'frequency': 'frequency', 
            'dateAdded': 'added_date',
            'lastVisited': 'last_visited',
            'nextReview': 'review_data.next_review_date',
            'text': 'text'
        }
        
        actual_field = field_map.get(field, field)
        
        if actual_field == 'mastery_level':
            # Convert to numeric for sorting
            level_order = {"default": 0, "bronze": 1, "silver": 2, "gold": 3}
            return level_order.get(word.mastery_level, 0)
        elif actual_field == 'text':
            return word.text.lower()
        elif actual_field == 'frequency':
            return word.frequency
        elif actual_field == 'added_date':
            return word.added_date
        elif actual_field == 'last_visited':
            return word.last_visited or datetime.min
        elif actual_field == 'review_data.next_review_date':
            return word.review_data.next_review_date
        else:
            return getattr(word, actual_field, None) or ""
    
    # Apply sorting
    if criteria.sort:
        # Sort by multiple criteria
        for sort_criterion in reversed(criteria.sort):  # Reverse to apply in priority order
            field = sort_criterion.get('field', 'text')
            direction = sort_criterion.get('direction', 'asc')
            reverse = direction == 'desc'
            
            words.sort(key=lambda w: get_sort_value(w, field), reverse=reverse)
    else:
        # Default sorting: mastery desc, frequency desc, lastVisited desc
        words.sort(key=lambda w: (
            -get_sort_value(w, 'mastery'),
            -get_sort_value(w, 'frequency'), 
            get_sort_value(w, 'lastVisited')
        ))
    
    # Apply pagination
    total = len(words)
    start = offset
    end = start + limit
    paginated_words = words[start:end]
    
    # Convert to dict format
    word_dicts = [word.model_dump() for word in paginated_words]
    
    return ListResponse(
        items=word_dicts,
        total=total,
        offset=offset,
        limit=limit,
        has_more=end < total
    )




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
) -> ListResponse[dict[str, Any]]:
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
) -> ListResponse[dict[str, Any]]:
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


@router.post("/{wordlist_id}/search", response_model=ResourceResponse)
async def search_wordlist(
    wordlist_id: PydanticObjectId,
    query: str = Query(..., min_length=1, description="Search query"),
    max_results: int = Query(20, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(0.6, ge=0.0, le=1.0, description="Minimum score"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Search within a wordlist using corpus functionality.
    
    Path Parameters:
        - wordlist_id: MongoDB ObjectId of word list
    
    Query Parameters:
        - query: Search query text
        - max_results: Maximum results to return
        - min_score: Minimum similarity score
    
    Returns:
        Search results with matching words and scores.
    
    Errors:
        404: Word list not found
        500: Search operation failed
    """
    try:
        results = await repo.search_wordlist_corpus(
            wordlist_id=wordlist_id,
            query=query,
            max_results=max_results,
            min_score=min_score,
        )
        
        return ResourceResponse(
            data=results,
            metadata={
                "query": query,
                "wordlist_id": str(wordlist_id),
                "search_performed_at": datetime.utcnow(),
            },
        )
        
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


@router.post("/upload", response_model=ResourceResponse, status_code=201)
async def upload_wordlist(
    file: UploadFile = File(..., description="Word list file to upload"),
    name: str | None = Query(None, description="Optional custom name for the wordlist"),
    description: str = Query("", description="Optional description"),
    tags: str = Query("", description="Comma-separated tags"),
    is_public: bool = Query(False, description="Make wordlist public"),
    owner_id: str | None = Query(None, description="Owner user ID"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Upload and parse a word list file.
    
    Form Parameters:
        - file: Word list file (supports various formats: numbered, CSV, plain text)
        - name: Optional custom name (auto-generated if not provided)
        - description: Optional description
        - tags: Comma-separated tags
        - is_public: Make wordlist public (default: false)
        - owner_id: Owner user ID (optional)
    
    Returns:
        Created word list with parsing metadata.
    
    Errors:
        400: Invalid file format or parsing error
        413: File too large
        422: Invalid input data
    """
    # Validate file
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    # Read file content
    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(413, "File too large (max 10MB)")
        
        # Create temporary file for parser
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)
        
        try:
            # Parse the file
            parsed = parse_file(tmp_path)
            
            if not parsed.words:
                raise HTTPException(400, "No words found in file")
            
            # Generate name if not provided
            wordlist_name = name if name else generate_name(parsed.words)
            
            # Parse tags
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
            
            # Create wordlist
            create_data = WordListCreate(
                name=wordlist_name,
                description=description or f"Uploaded from {file.filename}",
                words=parsed.words,
                tags=tag_list,
                is_public=is_public,
                owner_id=owner_id,
            )
            
            wordlist = await repo.create(create_data)
            
            return ResourceResponse(
                data=wordlist.model_dump(),
                metadata={
                    "upload_info": {
                        "filename": file.filename,
                        "file_size": len(content),
                        "parsing_metadata": parsed.metadata,
                    }
                },
                links={
                    "self": f"/wordlists/{wordlist.id}",
                    "words": f"/wordlists/{wordlist.id}/words",
                    "statistics": f"/wordlists/{wordlist.id}/statistics",
                },
            )
            
        finally:
            # Clean up temporary file
            tmp_path.unlink(missing_ok=True)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")