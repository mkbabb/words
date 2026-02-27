"""WordList search endpoints - dedicated search functionality."""

from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from ....corpus.manager import get_tree_corpus_manager
from ...core import ListResponse
from ...repositories import WordListRepository
from .utils import search_wordlist_names, search_words_in_wordlist
from .words import (
    WordListSearchQueryParams,
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
    search_response = await search_words_in_wordlist(
        wordlist_id=wordlist_id,
        query=params.query,
        repo=repo,
        max_results=params.max_results,
        min_score=params.min_score,
    )

    if not search_response.results:
        return ListResponse(items=[], total=0, offset=0, limit=params.limit)

    # Extract items and total from search response
    # Serialize SearchResult objects to dicts for the response model
    all_items = [
        r.model_dump(mode="json") if hasattr(r, "model_dump") else r
        for r in search_response.results
    ]
    items = all_items[params.offset : params.offset + params.limit]
    total = len(all_items)

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
        _repo=repo,
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


async def invalidate_wordlist_corpus(wordlist_id: PydanticObjectId) -> None:
    """Invalidate wordlist corpus when wordlist is modified."""
    corpus_name = f"wordlist_{wordlist_id}"
    corpus_manager = get_tree_corpus_manager()
    await corpus_manager.invalidate_corpus(corpus_name)


async def get_corpus_stats() -> dict[str, Any]:
    """Get corpus statistics for monitoring."""
    corpus_manager = get_tree_corpus_manager()
    return await corpus_manager.get_stats()
