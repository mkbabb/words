"""WordList words management endpoints."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ....models import Word
from ....wordlist.models import WordListItem
from ...core import ListResponse, ResourceResponse
from ...repositories import WordAddRequest, WordListRepository

router = APIRouter()


class WordListQueryParams(BaseModel):
    """Common query parameters for wordlist operations."""

    # Filters
    mastery_levels: list[str] | None = Field(
        None,
        description="Filter by mastery levels (bronze, silver, gold)",
    )
    hot_only: bool | None = Field(None, description="Show only hot items")
    due_only: bool | None = Field(None, description="Show only items due for review")
    min_views: int | None = Field(None, ge=0, description="Minimum view count")
    max_views: int | None = Field(None, ge=0, description="Maximum view count")
    reviewed: bool | None = Field(None, description="Filter reviewed/unreviewed")

    # Sorting
    sort_by: str = Field(
        "added_at",
        description="Sort field (word, added_at, last_visited, mastery_level, frequency, next_review). Can be comma-separated for multiple criteria",
    )
    sort_order: str = Field(
        "desc",
        description="Sort order (asc|desc). Can be comma-separated to match sort_by fields",
    )

    # Pagination
    offset: int = Field(0, ge=0, description="Skip first N results")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


def _normalize_items(items: list[Any]) -> list[WordListItem]:
    """Normalize all items to WordListItem instances."""
    normalized = []
    for item in items:
        if isinstance(item, WordListItem):
            normalized.append(item)
        elif isinstance(item, dict):
            normalized.append(WordListItem(**item))
        else:
            normalized.append(WordListItem(**item.model_dump()))
    return normalized


async def apply_wordlist_filters_and_sort(
    words: list[Any],
    params: WordListQueryParams,
) -> list[WordListItem]:
    """Apply filtering and sorting to wordlist items.

    Normalizes all items to WordListItem before filtering/sorting.
    """
    filtered = _normalize_items(words)

    if params.mastery_levels:
        filtered = [w for w in filtered if str(w.mastery_level) in params.mastery_levels]
    if params.hot_only:
        filtered = [w for w in filtered if w.temperature == "hot"]
    if params.due_only:
        filtered = [w for w in filtered if w.is_due_for_review()]
    if params.min_views is not None:
        filtered = [w for w in filtered if w.frequency >= params.min_views]
    if params.max_views is not None:
        filtered = [w for w in filtered if w.frequency <= params.max_views]
    if params.reviewed is not None:
        filtered = [w for w in filtered if (w.last_visited is not None) == params.reviewed]

    # Apply sorting
    sort_fields = params.sort_by.split(",")
    sort_orders = params.sort_order.split(",")

    # Ensure we have matching sort orders for each field
    while len(sort_orders) < len(sort_fields):
        sort_orders.append(sort_orders[-1] if sort_orders else "asc")

    # Sort by multiple fields
    for field, order in reversed(list(zip(sort_fields, sort_orders, strict=False))):
        reverse = order.lower() == "desc"
        filtered = sorted(
            filtered, key=lambda x: getattr(x, field.strip(), "") or "", reverse=reverse
        )

    return filtered


async def convert_wordlist_items_to_response(
    items: list[Any],
    paginated: bool = True,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Convert wordlist items to response format with optional pagination."""
    total = len(items)

    if paginated:
        items = items[offset : offset + limit]

    # Convert WordListItem models to dicts for JSON serialization
    normalized = _normalize_items(items)
    result = [item.model_dump(mode="json") for item in normalized]

    return result, total


class WordListSearchQueryParams(WordListQueryParams):
    """Query parameters for searching within a wordlist."""

    # Search-specific parameters
    query: str = Field(..., description="Search query")
    max_results: int = Field(
        100,
        ge=1,
        le=500,
        description="Maximum search results before filtering",
    )
    min_score: float = Field(0.4, ge=0.0, le=1.0, description="Minimum match score")
    semantic: bool | None = Field(
        None,
        description="Enable semantic search. If not set, automatically enabled "
        "for wordlists with more than 100 words.",
    )

    # Override default sort to use relevance for search
    sort_by: str = Field(
        "relevance",
        description="Sort field (relevance, added_at, last_viewed, mastery_level)",
    )


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


@router.get("/{wordlist_id}/words", response_model=ListResponse[dict[str, Any]])
async def list_words(
    wordlist_id: PydanticObjectId,
    params: WordListQueryParams = Depends(),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """List words in a wordlist with filtering and sorting.

    Query Parameters:
        - mastery_level: Filter by mastery level
        - min/max_views: View count range
        - reviewed: Filter by review status
        - sort_by: Field to sort by
        - sort_order: Sort direction
        - Standard pagination params

    Query Parameters:
        - mastery_levels: Filter by mastery levels (can specify multiple)
        - hot_only: Show only hot items
        - due_only: Show only items due for review
        - min/max_views: View count range
        - reviewed: Filter by review status
        - sort_by: Field(s) to sort by (comma-separated for multiple)
        - sort_order: Sort direction(s) (comma-separated to match sort_by)
        - Standard pagination params

    Returns:
        Paginated list of words with metadata.

    """
    # Get wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Apply shared filtering and sorting logic
    filtered_words = await apply_wordlist_filters_and_sort(wordlist.words, params)

    # Convert to response format with pagination
    items, total = await convert_wordlist_items_to_response(
        filtered_words,
        paginated=True,
        offset=params.offset,
        limit=params.limit,
    )

    return ListResponse(
        items=items,
        total=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.post("/{wordlist_id}/words", response_model=ResourceResponse)
async def add_word(
    wordlist_id: PydanticObjectId,
    request: WordAddRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Add a word to the wordlist.

    Body:
        - word: Word to add
        - notes: Optional notes

    Returns:
        Updated wordlist metadata.

    Errors:
        409: Word already in list

    """
    updated_list = await repo.add_word(wordlist_id, request)

    return ResourceResponse(
        data={
            "id": str(updated_list.id),
            "word_count": len(updated_list.words),
            "added_words": request.words,
        },
        metadata={
            "version": updated_list.version,
        },
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "words": f"/wordlists/{wordlist_id}/words",
        },
    )


class WordUpdateRequest(BaseModel):
    """Request body for updating a word's metadata in a wordlist."""

    notes: str | None = Field(None, description="User notes about the word")
    tags: list[str] | None = Field(None, description="User-defined tags")


@router.patch("/{wordlist_id}/words/{word}", response_model=ResourceResponse)
async def update_word(
    wordlist_id: PydanticObjectId,
    word: str,
    request: WordUpdateRequest,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Update a word's metadata (notes, tags) in a wordlist.

    Errors:
        404: Wordlist or word not found
    """
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Find the word document by text
    word_doc = await Word.find_one({"text": word})
    if not word_doc:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not found")

    # Find the WordListItem in the wordlist
    target_item = None
    for item in wordlist.words:
        if item.word_id == word_doc.id:
            target_item = item
            break

    if target_item is None:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not in wordlist")

    # Apply updates
    if request.notes is not None:
        target_item.notes = request.notes
    if request.tags is not None:
        target_item.tags = request.tags

    # Save wordlist
    await wordlist.save()

    return ResourceResponse(
        data=target_item.model_dump(mode="json"),
        metadata={"version": wordlist.version},
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
            "words": f"/wordlists/{wordlist_id}/words",
        },
    )


@router.delete("/{wordlist_id}/words/{word}", status_code=204, response_model=None)
async def remove_word(
    wordlist_id: PydanticObjectId,
    word: str,
    version: int | None = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Remove a word from the wordlist.

    Query Parameters:
        - version: Expected wordlist version for optimistic locking (optional).
          If provided, returns 409 Conflict when the wordlist has been
          concurrently modified.

    Errors:
        404: Word not in list
        409: Version mismatch (optimistic locking)
    """
    # Find the word document by text
    word_doc = await Word.find_one({"text": word})
    if not word_doc:
        raise HTTPException(status_code=404, detail="Word not found")

    assert word_doc.id is not None  # Word from database should have ID
    await repo.remove_word(wordlist_id, word_doc.id, version=version)
