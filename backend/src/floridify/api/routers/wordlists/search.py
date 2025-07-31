"""WordList search endpoints - dedicated search functionality."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from ....models import Word
from ...core import ListResponse
from ...repositories import WordListRepository
from .utils import search_wordlist_names, search_words_in_wordlist
from .words import (
    WordListSearchQueryParams,
    apply_wordlist_filters_and_sort,
    convert_wordlist_items_to_response,
    passes_wordlist_filters,
)

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


@router.post("/{wordlist_id}/search", response_model=ListResponse[dict[str, Any]])
async def search_wordlist_words(
    wordlist_id: PydanticObjectId,
    params: WordListSearchQueryParams = Depends(),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Search for words within a specific wordlist with full filtering and sorting.

    This is functionally identical to the list endpoint, but with an additional
    search-based filter applied first to restrict the filtering/sorting space.

    Query Parameters:
        - query: Search query string
        - max_results: Maximum search results before filtering
        - min_score: Minimum fuzzy match score
        - All standard wordlist filters and sorting options
        - Standard pagination parameters
    """
    # Get the wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Step 1: Apply search filter to restrict the wordlist items
    search_results = await search_words_in_wordlist(
        wordlist_id=wordlist_id,
        query=params.query,
        repo=repo,
        max_results=params.max_results,
        min_score=params.min_score,
    )

    if not search_results:
        return ListResponse(items=[], total=0, offset=0, limit=params.limit)

    # Step 2: Filter wordlist to only items that match the search
    matched_word_texts = {result["word"] for result in search_results}
    words = await Word.find({"text": {"$in": list(matched_word_texts)}}).to_list()
    word_id_to_item = {word_item.word_id: word_item for word_item in wordlist.words}
    
    # Get search-filtered wordlist items
    search_filtered_items = []
    for word in words:
        if word.id and word.id in word_id_to_item:
            search_filtered_items.append(word_id_to_item[word.id])

    if not search_filtered_items:
        return ListResponse(items=[], total=0, offset=0, limit=params.limit)

    # Step 3: Handle relevance sorting as special case, then use shared logic for everything else
    if params.sort_by == "relevance":
        # For relevance, we need to sort by search scores first, then apply other filters
        word_scores = {result["word"]: result["score"] for result in search_results}
        word_id_to_text = {word.id: word.text for word in words if word.id}
        
        # Sort by relevance score (highest first) to preserve search ranking
        search_filtered_items.sort(
            key=lambda item: word_scores.get(word_id_to_text.get(item.word_id, ""), 0),
            reverse=True
        )
        
        # Apply shared filtering logic to maintain relevance order
        filtered_items = [item for item in search_filtered_items if passes_wordlist_filters(item, params)]
    else:
        # For non-relevance sorting, use the shared filter and sort function
        filtered_items = apply_wordlist_filters_and_sort(search_filtered_items, params)

    # Step 4: Convert to response format and paginate using shared helper
    items, total = await convert_wordlist_items_to_response(
        filtered_items,
        paginated=True,
        offset=params.offset,
        limit=params.limit
    )

    return ListResponse(
        items=items,
        total=total,
        offset=params.offset,
        limit=params.limit,
    )


@router.get("/search/{query}", response_model=ListResponse[dict[str, Any]])
async def search_wordlists(
    query: str,
    limit: int = 10,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Search wordlists by name using fuzzy search with TTL corpus caching.

    Path Parameters:
        - query: Search query

    Query Parameters:
        - limit: Maximum results

    Returns:
        Matching wordlists with search scores.
    """
    # Use corpus-based fuzzy search (no TTL expiration)
    search_results = await search_wordlist_names(
        query=query,
        repo=repo,
        max_results=limit,
        min_score=0.3,  # Allow broader matches for name search
    )

    # Convert to expected format
    wordlists = [result["wordlist"] for result in search_results]
    
    return ListResponse(
        items=wordlists,
        total=len(wordlists),
        offset=0,
        limit=limit,
    )