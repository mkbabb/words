"""WordList words management endpoints."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ....models import Word
from ....wordlist.constants import MasteryLevel
from ...core import ListResponse, ResourceResponse
from ...repositories import WordAddRequest, WordListRepository
from .utils import search_words_in_wordlist

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


class WordListWordQueryParams(BaseModel):
    """Query parameters for listing words in a wordlist."""

    # Filters
    mastery_level: MasteryLevel | None = Field(None, description="Filter by mastery level")
    min_views: int | None = Field(None, ge=0, description="Minimum view count")
    max_views: int | None = Field(None, ge=0, description="Maximum view count")
    reviewed: bool | None = Field(None, description="Filter reviewed/unreviewed")

    # Sorting
    sort_by: str = Field(
        "added_at", description="Sort field (added_at, last_viewed, mastery_level)"
    )
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    # Pagination
    offset: int = Field(0, ge=0, description="Skip first N results")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


@router.get("/{wordlist_id}/words", response_model=ListResponse[dict[str, Any]])
async def list_words(
    wordlist_id: PydanticObjectId,
    params: WordListWordQueryParams = Depends(),
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

    Returns:
        Paginated list of words with metadata.
    """
    # Get wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Filter words
    filtered_words = []
    for word in wordlist.words:
        # Apply filters
        if params.mastery_level and word.mastery_level != params.mastery_level:
            continue
        if params.min_views is not None and word.review_data.repetitions < params.min_views:
            continue
        if params.max_views is not None and word.review_data.repetitions > params.max_views:
            continue
        if params.reviewed is not None:
            is_reviewed = word.review_data.last_review_date is not None
            if params.reviewed != is_reviewed:
                continue

        filtered_words.append(word)

    # Sort words
    sort_key = {
        "added_at": lambda w: w.added_date or "",
        "last_viewed": lambda w: w.last_visited or "",
        "mastery_level": lambda w: w.mastery_level.value,
        "view_count": lambda w: w.review_data.repetitions,
    }.get(params.sort_by, lambda w: w.added_date or "")

    filtered_words.sort(key=sort_key, reverse=(params.sort_order == "desc"))

    # Paginate
    total = len(filtered_words)
    start = params.offset
    end = start + params.limit
    paginated_words = filtered_words[start:end]

    # Fetch Word documents for the paginated items (word_ids are now ObjectIds)
    word_ids = [w.word_id for w in paginated_words if w.word_id]

    words = await Word.find({"_id": {"$in": word_ids}}).to_list()

    # Create a map of word_id to word text
    word_text_map = {str(word.id): word.text for word in words}

    # Convert to response format
    items = []
    for word_item in paginated_words:
        items.append(
            {
                "word": word_text_map.get(str(word_item.word_id), ""),  # Only include word text
                "frequency": word_item.frequency,
                "selected_definition_ids": [str(id) for id in word_item.selected_definition_ids],
                "mastery_level": word_item.mastery_level,
                "temperature": word_item.temperature,
                "review_data": word_item.review_data.model_dump()
                if word_item.review_data
                else None,
                "last_visited": word_item.last_visited.isoformat()
                if word_item.last_visited
                else None,
                "added_date": word_item.added_date.isoformat() if word_item.added_date else None,
                "notes": word_item.notes,
                "tags": word_item.tags,
            }
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
