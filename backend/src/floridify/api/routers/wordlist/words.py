"""WordList words management endpoints."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException
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
    semantic: bool | None = Field(
        None,
        description="Enable semantic search. If not set, automatically enabled "
        "for wordlists with more than 100 words.",
    )
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
    """List words in a wordlist with filtering and sorting."""
    # Verify wordlist exists
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

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
    for field, order in zip(sort_fields, sort_orders, strict=False):
        field = field.strip()
        # Map field names
        if field == "added_at":
            field = "added_date"
        direction = -1 if order.strip().lower() == "desc" else 1
        sort_list.append((field, direction))

    # Query with pagination
    items_cursor = WordListItemDoc.find(query)
    if sort_list:
        items_cursor = items_cursor.sort(sort_list)
    items = await items_cursor.skip(params.offset).limit(params.limit).to_list()

    # Apply lazy temperature cooling
    for item in items:
        item.update_temperature()

    # Refine due_only with Python method (handles timezone edge cases)
    if params.due_only:
        items = [w for w in items if w.is_due_for_review()]

    # Convert to response format
    result = [item.model_dump(mode="json") for item in items]

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

    return ListResponse(
        items=result,
        total=total,
        offset=params.offset,
        limit=params.limit,
    )


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
    assert wordlist is not None
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    updated_list = await repo.add_word(wordlist_id, request)

    return ResourceResponse(
        data={
            "id": str(updated_list.id),
            "word_count": updated_list.unique_words,
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
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Update a word's metadata (notes, tags) in a wordlist."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None
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
    assert wordlist is not None
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    word_doc = await Word.find_one({"text": word})
    if not word_doc:
        raise HTTPException(status_code=404, detail="Word not found")

    assert word_doc.id is not None
    await repo.remove_word(wordlist_id, word_doc.id, version=version)


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
    assert wordlist is not None
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
    assert wordlist is not None
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    updated = await repo.mark_word_visited(wordlist_id, word)

    return ResourceResponse(
        data={"word": word, "visited": True},
        metadata={"version": updated.version},
    )
