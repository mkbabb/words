"""WordList words management endpoints."""

import base64
import json
from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ....models import Word
from ....wordlist.models import WordListItemDoc
from ...core import CurrentUserDep, ListResponse, OptionalUserRoleDep, ResourceResponse
from ...repositories import WordAddRequest, WordListRepository
from .main import verify_wordlist_ownership

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
    limit: int = Field(20, ge=1, le=200, description="Maximum results")


class WordListSearchQueryParams(WordListQueryParams):
    """Query parameters for searching within a wordlist."""

    query: str = Field(..., description="Search query")
    max_results: int = Field(
        100, ge=1, le=500, description="Maximum search results before filtering"
    )
    min_score: float = Field(0.4, ge=0.0, le=1.0, description="Minimum match score")
    mode: str | None = Field(
        None,
        description="Search mode: smart, exact, fuzzy, semantic. "
        "If not set, defaults to smart cascade.",
    )
    sort_by: str = Field(
        "relevance",
        description="Sort field (relevance, added_at, last_viewed, mastery_level)",
    )


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


def _decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode a base64-encoded JSON cursor."""
    try:
        decoded = base64.b64decode(cursor).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def _encode_cursor(data: dict[str, Any]) -> str:
    """Encode cursor data as base64 JSON."""
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")


@router.get("/{wordlist_id}/words", response_model=ListResponse[dict[str, Any]])
async def list_words(
    wordlist_id: PydanticObjectId,
    cursor: str | None = Query(None, description="Cursor for keyset pagination (base64 JSON)"),
    params: WordListQueryParams = Depends(),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[dict[str, Any]]:
    """List words in a wordlist with filtering and sorting.

    Supports both offset-based and cursor-based pagination.
    When `cursor` is provided, it takes precedence over `offset`.
    """
    # Verify wordlist exists
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)

    # Build MongoDB query
    query: dict[str, Any] = {"wordlist_id": wordlist_id}

    if params.mastery_levels:
        query["mastery_level"] = {"$in": params.mastery_levels}
    if params.hot_only:
        query["temperature"] = "hot"
    if params.min_views is not None:
        query.setdefault("frequency", {})["$gte"] = params.min_views
    if params.max_views is not None:
        query.setdefault("frequency", {})["$lte"] = params.max_views
    if params.reviewed is not None:
        if params.reviewed:
            query["last_visited"] = {"$ne": None}
        else:
            query["last_visited"] = None

    # Pre-filter due items in MongoDB to reduce the working set
    if params.due_only:
        query["review_data.next_review_date"] = {"$lte": datetime.now(UTC)}

    # Get total count for the filtered query
    total = await WordListItemDoc.find(query).count()

    # Build sort criteria
    sort_fields = params.sort_by.split(",")
    sort_orders = params.sort_order.split(",")
    while len(sort_orders) < len(sort_fields):
        sort_orders.append(sort_orders[-1] if sort_orders else "asc")

    sort_list = []
    mapped_sort_fields = []
    for field, order in zip(sort_fields, sort_orders, strict=False):
        field = field.strip()
        # Map field names
        if field == "added_at":
            field = "added_date"
        direction = -1 if order.strip().lower() == "desc" else 1
        sort_list.append((field, direction))
        mapped_sort_fields.append((field, direction))

    # Apply cursor-based pagination if cursor is provided
    if cursor:
        cursor_data = _decode_cursor(cursor)
        if cursor_data and mapped_sort_fields:
            # Build cursor condition using the primary sort field
            primary_field, primary_dir = mapped_sort_fields[0]
            cursor_value = cursor_data.get(primary_field)
            cursor_id = cursor_data.get("_id")
            if cursor_value is not None and cursor_id is not None:
                op = "$gt" if primary_dir == 1 else "$lt"
                # Compound condition: (sort_field > cursor_value) OR
                # (sort_field == cursor_value AND _id > cursor_id)
                query["$or"] = [
                    {primary_field: {op: cursor_value}},
                    {
                        primary_field: cursor_value,
                        "_id": {"$gt": PydanticObjectId(cursor_id)},
                    },
                ]

    # Query with pagination
    items_cursor = WordListItemDoc.find(query)
    if sort_list:
        items_cursor = items_cursor.sort(sort_list)

    if cursor:
        # Cursor-based: no skip needed
        items = await items_cursor.limit(params.limit).to_list()
    else:
        items = await items_cursor.skip(params.offset).limit(params.limit).to_list()

    # Apply lazy temperature cooling
    for item in items:
        item.update_temperature()

    # Refine due_only with Python method (handles timezone edge cases)
    if params.due_only:
        items = [w for w in items if w.is_due_for_review()]

    # Convert to response format
    result = [item.model_dump(mode="json") for item in items]

    # Build next_cursor from the last item
    next_cursor = None
    if items and len(items) == params.limit and mapped_sort_fields:
        last_item = items[-1]
        primary_field, _ = mapped_sort_fields[0]
        last_dump = last_item.model_dump(mode="json")
        # Navigate dotted field paths
        cursor_val = last_dump
        for part in primary_field.split("."):
            if isinstance(cursor_val, dict):
                cursor_val = cursor_val.get(part)
            else:
                cursor_val = None
                break
        if cursor_val is not None:
            next_cursor = _encode_cursor(
                {
                    primary_field: cursor_val,
                    "_id": str(last_item.id),
                }
            )

    # Populate word text
    word_ids = [item.get("word_id") for item in result if item.get("word_id")]
    if word_ids:
        oids = [PydanticObjectId(wid) if isinstance(wid, str) else wid for wid in word_ids]
        word_docs = await Word.find({"_id": {"$in": oids}}).to_list()
        text_map = {str(w.id): w.text for w in word_docs}
        for item in result:
            wid = item.pop("word_id", None)
            item["word"] = text_map.get(str(wid), "") if wid else ""
            # Remove wordlist_id from response (internal FK)
            item.pop("wordlist_id", None)
            # Remove internal document fields
            item.pop("id", None)
            item.pop("revision_id", None)

    response_data = ListResponse(
        items=result,
        total=total,
        offset=params.offset,
        limit=params.limit,
    )

    # Include next_cursor in the response dict
    if next_cursor:
        response_dict = response_data.model_dump(mode="json")
        response_dict["next_cursor"] = next_cursor
        return response_dict

    return response_data


@router.post("/{wordlist_id}/words", response_model=ResourceResponse)
async def add_word(
    wordlist_id: PydanticObjectId,
    request: WordAddRequest,
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Add a word to the wordlist."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    updated_list = await repo.add_word(wordlist_id, request)
    from .search import invalidate_wordlist_corpus
    await invalidate_wordlist_corpus(wordlist_id)

    collapsed_added = repo._collapse_entries(request.words)

    return ResourceResponse(
        data={
            "id": str(updated_list.id),
            "word_count": updated_list.unique_words,
            "unique_words": updated_list.unique_words,
            "total_words": updated_list.total_words,
            "added_words": [word.model_dump(mode="json") for word in collapsed_added],
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
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Update a word's metadata (notes, tags) in a wordlist."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    word_doc = await Word.find_one({"text": word})
    if not word_doc:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not found")

    target_item = await WordListItemDoc.find_one(
        {"wordlist_id": wordlist_id, "word_id": word_doc.id}
    )
    if target_item is None:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not in wordlist")

    if request.notes is not None:
        target_item.notes = request.notes
    if request.tags is not None:
        target_item.tags = request.tags

    await target_item.save()

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
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    version: int | None = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Remove a word from the wordlist."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    word_doc = await Word.find_one({"text": word})
    if not word_doc:
        raise HTTPException(status_code=404, detail="Word not found")

    assert word_doc.id is not None
    await repo.remove_word(wordlist_id, word_doc.id, version=version)
    from .search import invalidate_wordlist_corpus
    await invalidate_wordlist_corpus(wordlist_id)


class BulkDeleteRequest(BaseModel):
    """Request for bulk word deletion."""

    words: list[str] = Field(..., min_length=1, description="Words to remove")


@router.delete("/{wordlist_id}/words", response_model=ResourceResponse)
async def bulk_delete_words(
    wordlist_id: PydanticObjectId,
    request: BulkDeleteRequest,
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Remove multiple words from a wordlist in a single operation."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    # Find all word docs
    word_docs = await Word.find({"text": {"$in": request.words}}).to_list()
    word_id_set = {w.id for w in word_docs}

    # Count items to be deleted
    original_count = await WordListItemDoc.find({"wordlist_id": wordlist_id}).count()

    # Delete matching items from the items collection
    await WordListItemDoc.find(
        {"wordlist_id": wordlist_id, "word_id": {"$in": list(word_id_set)}}
    ).delete()

    remaining_count = await WordListItemDoc.find({"wordlist_id": wordlist_id}).count()
    removed_count = original_count - remaining_count

    # Recompute denormalized stats via aggregation pipeline
    await repo.recompute_stats(wordlist_id)
    from .search import invalidate_wordlist_corpus
    await invalidate_wordlist_corpus(wordlist_id)

    return ResourceResponse(
        data={
            "removed": removed_count,
            "remaining": remaining_count,
        },
    )


@router.post("/{wordlist_id}/words/{word}/visit", response_model=ResourceResponse)
async def mark_word_visited(
    wordlist_id: PydanticObjectId,
    word: str,
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Mark a word as visited/viewed."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    updated = await repo.mark_word_visited(wordlist_id, word)

    return ResourceResponse(
        data={"word": word, "visited": True},
        metadata={"version": updated.version},
    )
