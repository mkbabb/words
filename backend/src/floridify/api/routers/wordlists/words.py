"""WordList words management endpoints."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ....models import Word
from ....text import normalize_word
from ....wordlist.constants import Temperature
from ...core import ListResponse, ResourceResponse
from ...repositories import WordAddRequest, WordListRepository
from .utils import search_words_in_wordlist


class WordListQueryParams(BaseModel):
    """Common query parameters for wordlist operations."""

    # Filters
    mastery_levels: list[str] | None = Field(
        None, description="Filter by mastery levels (bronze, silver, gold)"
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
        "desc", description="Sort order (asc|desc). Can be comma-separated to match sort_by fields"
    )

    # Pagination
    offset: int = Field(0, ge=0, description="Skip first N results")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


class WordListSearchQueryParams(WordListQueryParams):
    """Query parameters for searching within a wordlist."""

    # Search-specific parameters
    query: str = Field(..., description="Search query")
    max_results: int = Field(
        100, ge=1, le=500, description="Maximum search results before filtering"
    )
    min_score: float = Field(0.4, ge=0.0, le=1.0, description="Minimum match score")

    # Override default sort to use relevance for search
    sort_by: str = Field(
        "relevance", description="Sort field (relevance, added_at, last_viewed, mastery_level)"
    )


def passes_wordlist_filters(word_item: Any, params: WordListQueryParams) -> bool:
    """Check if a wordlist item passes the filter criteria.

    Args:
        word_item: WordListItem to check
        params: Query parameters with filter criteria

    Returns:
        True if item passes all filters, False otherwise
    """
    # Apply mastery levels filter
    if params.mastery_levels:
        if word_item.mastery_level not in params.mastery_levels:
            return False

    # Apply hot_only filter
    if params.hot_only and word_item.temperature != Temperature.HOT:
        return False

    # Apply due_only filter
    if params.due_only:
        # Item is due if it has a next_review date that's in the past
        if not word_item.review_data.next_review_date:
            return False
        if word_item.review_data.next_review_date > datetime.now(UTC):
            return False

    # Apply view count filters
    if params.min_views is not None and word_item.review_data.repetitions < params.min_views:
        return False
    if params.max_views is not None and word_item.review_data.repetitions > params.max_views:
        return False

    # Apply reviewed filter
    if params.reviewed is not None:
        is_reviewed = word_item.review_data.last_review_date is not None
        if params.reviewed != is_reviewed:
            return False

    return True


async def apply_wordlist_filters_and_sort(
    wordlist_items: list[Any], params: WordListQueryParams
) -> list[Any]:
    """Apply filters and sorting to wordlist items.

    Args:
        wordlist_items: List of wordlist items to filter
        params: Query parameters with filter and sort criteria

    Returns:
        Filtered and sorted list of wordlist items
    """
    # Apply filters using shared logic
    filtered_items = [item for item in wordlist_items if passes_wordlist_filters(item, params)]

    # Sort items - handle multiple sort criteria
    sort_fields = [f.strip() for f in params.sort_by.split(",")]
    sort_orders = [o.strip() for o in params.sort_order.split(",")]

    # Pad sort_orders if not enough values provided
    while len(sort_orders) < len(sort_fields):
        sort_orders.append(sort_orders[-1] if sort_orders else "desc")

    # Define sort key functions
    sort_key_map = {
        "added_at": lambda w: w.added_date or "",
        "last_visited": lambda w: w.last_visited or "",
        "mastery_level": lambda w: w.mastery_level,
        "view_count": lambda w: w.review_data.repetitions,
        "frequency": lambda w: w.frequency,  # Match frontend field name
        "next_review": lambda w: w.review_data.next_review_date or "",  # Match frontend field name
        "word": lambda w: "",  # Will be filled in after fetching word text
    }

    # If sorting by word, we need to fetch word texts first
    if "word" in sort_fields:
        word_ids = [w.word_id for w in filtered_items if w.word_id]
        words = await Word.find({"_id": {"$in": word_ids}}).to_list()
        # Create map with normalized text for proper sorting of diacritics and phrases
        word_normalized_map = {str(word.id): normalize_word(word.text) for word in words}

        # Update the word sort key to use normalized text
        sort_key_map["word"] = lambda w: word_normalized_map.get(str(w.word_id), "")

    # Sort using multiple keys with proper handling of desc order
    for field, order in reversed(list(zip(sort_fields, sort_orders))):
        # Get the sort key function
        key_func = sort_key_map.get(field, lambda w: w.added_date or "")
        # Sort by this field
        filtered_items.sort(key=key_func, reverse=(order == "desc"))

    return filtered_items


async def convert_wordlist_items_to_response(
    wordlist_items: list[Any], paginated: bool = True, offset: int = 0, limit: int = 20
) -> tuple[list[dict[str, Any]], int]:
    """Convert wordlist items to API response format.

    Args:
        wordlist_items: List of wordlist items to convert
        paginated: Whether to apply pagination
        offset: Pagination offset
        limit: Pagination limit

    Returns:
        Tuple of (response_items, total_count)
    """
    total = len(wordlist_items)

    # Apply pagination if requested
    if paginated:
        items_to_convert = wordlist_items[offset : offset + limit]
    else:
        items_to_convert = wordlist_items

    # Fetch Word documents for the items
    word_ids = [w.word_id for w in items_to_convert if w.word_id]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(word.id): word.text for word in words}

    # Convert to response format
    response_items = []
    for word_item in items_to_convert:
        word_text = word_text_map.get(str(word_item.word_id), "")
        if not word_text:
            continue

        item_data = {
            "word": word_text,
            "frequency": word_item.frequency,
            "selected_definition_ids": [str(id) for id in word_item.selected_definition_ids],
            "mastery_level": word_item.mastery_level.value,
            "temperature": word_item.temperature.value,
            "review_data": word_item.review_data.model_dump() if word_item.review_data else None,
            "last_visited": word_item.last_visited.isoformat() if word_item.last_visited else None,
            "added_date": word_item.added_date.isoformat() if word_item.added_date else None,
            "notes": word_item.notes,
            "tags": word_item.tags,
        }
        response_items.append(item_data)

    return response_items, total


router = APIRouter()


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
        filtered_words, paginated=True, offset=params.offset, limit=params.limit
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


@router.delete("/{wordlist_id}/words/{word}", status_code=204, response_model=None)
async def remove_word(
    wordlist_id: PydanticObjectId,
    word: str,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Remove a word from the wordlist.

    Errors:
        404: Word not in list
    """
    # Find the word document by text
    word_doc = await Word.find_one({"text": word})
    if not word_doc:
        raise HTTPException(status_code=404, detail="Word not found")

    assert word_doc.id is not None  # Word from database should have ID
    await repo.remove_word(wordlist_id, word_doc.id)


@router.get("/{wordlist_id}/words/search", response_model=ListResponse[dict[str, Any]])
async def search_words_in_list(
    wordlist_id: PydanticObjectId,
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Search for words within the wordlist using fuzzy search with TTL corpus caching.

    Query Parameters:
        - query: Search query
        - limit: Maximum results

    Returns:
        Matching words from the list with search scores.
    """
    # Use TTL corpus-based fuzzy search
    search_results = await search_words_in_wordlist(
        wordlist_id=wordlist_id,
        query=query,
        repo=repo,
        # No TTL expiration - corpus persists until invalidated
        max_results=limit,
        min_score=0.4,  # Slightly stricter for word matching
    )

    return ListResponse(
        items=search_results,
        total=len(search_results),
        offset=0,
        limit=len(search_results),
    )
