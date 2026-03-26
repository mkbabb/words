"""WordList search endpoints - dedicated search functionality."""

import asyncio
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Query

from ....corpus.crud import get_stats as _get_corpus_crud_stats
from ....corpus.manager import get_tree_corpus_manager
from ....wordlist.models import WordList
from ...core import ListResponse, OptionalUserDep
from ...repositories import WordListRepository
from .utils import (
    enrich_search_results_with_wordlist_data,
    post_filter_search_results,
    search_wordlist_names,
    search_words_in_wordlist,
)
from .words import (
    WordListSearchQueryParams,
)

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


def _sort_search_items(
    items: list[dict[str, Any]],
    sort_by: str,
    sort_order: str,
) -> list[dict[str, Any]]:
    """Apply deterministic server-side sort to enriched search results."""
    if not items:
        return items

    field = (sort_by or "relevance").strip().lower()
    reverse = (sort_order or "desc").strip().lower() == "desc"

    if field == "relevance":
        return sorted(items, key=lambda item: item.get("score", 0), reverse=reverse)
    if field == "frequency":
        return sorted(items, key=lambda item: item.get("frequency", 0), reverse=reverse)
    if field in {"word", "text"}:
        return sorted(items, key=lambda item: str(item.get("word", "")).lower(), reverse=reverse)
    if field in {"added_at", "added_date"}:
        return sorted(items, key=lambda item: item.get("added_date") or "", reverse=reverse)
    if field in {"last_visited", "last_viewed"}:
        return sorted(items, key=lambda item: item.get("last_visited") or "", reverse=reverse)
    if field == "mastery_level":
        rank = {"default": 0, "bronze": 1, "silver": 2, "gold": 3}
        return sorted(
            items,
            key=lambda item: rank.get(str(item.get("mastery_level", "default")), 0),
            reverse=reverse,
        )
    if field == "next_review":
        return sorted(
            items,
            key=lambda item: (item.get("review_data") or {}).get("next_review_date") or "",
            reverse=reverse,
        )

    return items


@router.post("/search-all", response_model=ListResponse[dict[str, Any]])
async def search_all_wordlists(
    query: str = Query(..., min_length=1),
    max_results: int = Query(default=50, ge=1, le=200),
    min_score: float = Query(default=0.4, ge=0.0, le=1.0),
    mode: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    user_id: OptionalUserDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Search words across ALL user wordlists. Results include wordlist_id/name."""
    # Fetch all wordlists for the user (or all if no auth)
    wl_filter: dict[str, Any] = {}
    if user_id:
        wl_filter["owner_id"] = user_id
    wordlists = await WordList.find(wl_filter).to_list()

    if not wordlists:
        return ListResponse(items=[], total=0, offset=offset, limit=limit)

    # Search across all wordlists concurrently (capped)
    sem = asyncio.Semaphore(10)

    async def _search_one(wl: WordList) -> list[dict[str, Any]]:
        async with sem:
            response = await search_words_in_wordlist(
                wordlist_id=wl.id,
                query=query,
                max_results=max_results,
                min_score=min_score,
                mode=mode,
                repo=repo,
                collect_all_matches=True,
            )
            if not response.results:
                return []
            enriched = await enrich_search_results_with_wordlist_data(
                response.results, wl.id
            )
            # Tag each result with wordlist info
            for item in enriched:
                item["wordlist_id"] = str(wl.id)
                item["wordlist_name"] = wl.name
            return enriched

    all_results_nested = await asyncio.gather(*[_search_one(wl) for wl in wordlists])

    # Flatten, sort by score desc, paginate
    merged: list[dict[str, Any]] = []
    for batch in all_results_nested:
        merged.extend(batch)
    merged.sort(key=lambda r: r.get("score", 0), reverse=True)

    total = len(merged)
    items = merged[offset : offset + limit]

    return ListResponse(items=items, total=total, offset=offset, limit=limit)


@router.post("/{wordlist_id}/search", response_model=ListResponse[dict[str, Any]])
async def search_wordlist_words(
    wordlist_id: PydanticObjectId,
    params: WordListSearchQueryParams = Depends(),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """Search for words within a specific wordlist with full filtering and sorting.

    Query Parameters:
        - query: Search query string
        - max_results: Maximum search results before filtering
        - min_score: Minimum fuzzy match score
        - All standard wordlist filters and sorting options
        - Standard pagination parameters
    """
    # Get the wordlist
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)

    # Step 1: Apply search filter with multi-method match collection
    search_response = await search_words_in_wordlist(
        wordlist_id=wordlist_id,
        query=params.query,
        repo=repo,
        max_results=params.max_results,
        min_score=params.min_score,
        mode=params.mode,
        collect_all_matches=True,
    )

    if not search_response.results:
        return ListResponse(items=[], total=0, offset=0, limit=params.limit)

    # Preserve search metadata for the frontend while still returning list-shaped results.
    search_metadata = {
        "corpus_name": f"wordlist_{wordlist_id}",
        "mode": search_response.mode,
        "sort_by": params.sort_by,
        "sort_order": params.sort_order,
    }
    for result in search_response.results:
        result.metadata = {**(result.metadata or {}), **search_metadata}

    # Enrich with wordlist item data (mastery, temperature, review_data, etc.)
    all_items = await enrich_search_results_with_wordlist_data(
        search_response.results, wordlist_id
    )

    # Apply post-search filters (mastery, temperature, due status)
    all_items = await post_filter_search_results(
        results=all_items,
        wordlist_id=wordlist_id,
        mastery_levels=params.mastery_levels,
        hot_only=params.hot_only,
        due_only=params.due_only,
    )
    all_items = _sort_search_items(all_items, params.sort_by, params.sort_order)

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
    """Invalidate wordlist corpus and search instance cache when wordlist is modified."""
    corpus_name = f"wordlist_{wordlist_id}"
    corpus_manager = get_tree_corpus_manager()
    await corpus_manager.invalidate_corpus(corpus_name)

    # Evict cached Search instances for this corpus
    from ....search.cache import invalidate_by_corpus

    invalidate_by_corpus(corpus_name)


async def get_corpus_stats() -> dict[str, Any]:
    """Get corpus statistics for monitoring."""
    return await _get_corpus_crud_stats()
