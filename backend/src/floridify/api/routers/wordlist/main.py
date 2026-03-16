"""WordLists API - CRUD operations for word lists."""

import asyncio
import csv
import io
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ....core.state_tracker import Stages, StateTracker
from ....core.streaming import create_streaming_response
from ....models import Word
from ....models.dictionary import Definition
from ....models.user import UserRole
from ....wordlist.models import WordList, WordListItemDoc
from ....wordlist.parser import parse_file
from ....wordlist.utils import generate_wordlist_name
from ...core import (
    CurrentUserDep,
    ListResponse,
    OptionalUserDep,
    OptionalUserRoleDep,
    PaginationDep,
    ResourceResponse,
    SortDep,
)
from ...repositories import (
    WordListCreate,
    WordListFilter,
    WordListRepository,
    WordListUpdate,
)

router = APIRouter()


def get_wordlist_repo() -> WordListRepository:
    """Dependency to get word list repository."""
    return WordListRepository()


async def verify_wordlist_ownership(
    wordlist: WordList,
    user_id: str,
    user_role: UserRole | None = None,
) -> None:
    """Verify user owns the wordlist or is admin."""
    if user_role == UserRole.ADMIN:
        return
    if wordlist.owner_id != user_id:
        raise HTTPException(403, "Not authorized to access this wordlist")


class WordListQueryParams(BaseModel):
    """Query parameters for listing wordlists."""

    name: str | None = Field(None, description="Exact name match")
    name_pattern: str | None = Field(None, description="Partial name match")
    owner_id: str | None = Field(None, description="Filter by owner")
    is_public: bool | None = Field(None, description="Filter by visibility")
    has_tag: str | None = Field(None, description="Filter by tag")
    min_words: int | None = Field(None, ge=0, description="Minimum word count")
    max_words: int | None = Field(None, ge=0, description="Maximum word count")
    created_after: datetime | None = Field(None, description="Created after date")
    created_before: datetime | None = Field(None, description="Created before date")


@router.get("", response_model=ListResponse[dict[str, Any]])
async def list_wordlists(
    pagination: PaginationDep,
    sort: SortDep,
    user_id: OptionalUserDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
    params: WordListQueryParams = Depends(),
) -> ListResponse[dict[str, Any]]:
    """List wordlists with filtering and pagination.

    Returns metadata only (no embedded words) for performance.
    Use GET /{wordlist_id}/words for word data.
    """
    # Build filter
    filter_params = WordListFilter(
        name=params.name,
        name_pattern=params.name_pattern,
        owner_id=params.owner_id,
        is_public=params.is_public,
        has_tag=params.has_tag,
        min_words=params.min_words,
        max_words=params.max_words,
        created_after=params.created_after,
        created_before=params.created_before,
    )

    # If no explicit owner filter and user is authenticated, show their lists + public
    query = filter_params.to_query()
    if params.owner_id is None and params.is_public is None and user_id:
        query["$or"] = [{"owner_id": user_id}, {"is_public": True}]
    elif params.owner_id is None and not user_id:
        query["is_public"] = True

    # Get data
    wordlists, total = await repo.list(
        filter_dict=query,
        pagination=pagination,
        sort=sort,
    )

    # Return metadata only (no word population) for performance
    items = []
    for wordlist in wordlists:
        data = wordlist.model_dump(mode="json")
        data["word_count"] = wordlist.unique_words
        items.append(data)

    return ListResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_wordlist(
    data: WordListCreate,
    response: Response,
    user_id: CurrentUserDep,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Create a new wordlist."""
    # Set owner from authenticated user
    data.owner_id = user_id

    wordlist, created = await repo.create(data)

    if not created:
        response.status_code = 200

    return ResourceResponse(
        data=wordlist.model_dump(mode="json"),
        metadata={"created": created, "word_count": wordlist.unique_words},
        links={
            "self": f"/wordlists/{wordlist.id}",
            "words": f"/wordlists/{wordlist.id}/words",
            "stats": f"/wordlists/{wordlist.id}/stats",
        },
    )


@router.get("/generate-name", response_model=dict[str, str])
async def generate_wordlist_slug() -> dict[str, str]:
    """Generate a random slug name for a wordlist."""
    try:
        slug_name = generate_wordlist_name()
        return {"name": slug_name}
    except Exception:
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        return {"name": f"wordlist-{timestamp}"}


@router.get("/{wordlist_id}", response_model=ResourceResponse)
async def get_wordlist(
    wordlist_id: PydanticObjectId,
    user_id: OptionalUserDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Get wordlist metadata (no embedded words — use /words endpoint for word data)."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Check access: public or owner
    if not wordlist.is_public and wordlist.owner_id and user_id != wordlist.owner_id:
        raise HTTPException(403, "Not authorized to access this wordlist")

    # Mastery distribution via aggregation pipeline (never loads all items)
    pipeline = [
        {"$match": {"wordlist_id": wordlist.id}},
        {"$group": {"_id": "$mastery_level", "count": {"$sum": 1}}},
    ]
    mastery_distribution: dict[str, int] = {}
    collection = WordListItemDoc.get_pymongo_collection()
    async for doc in collection.aggregate(pipeline):
        mastery_distribution[doc["_id"]] = doc["count"]

    wordlist_data = wordlist.model_dump(mode="json")

    return ResourceResponse(
        data=wordlist_data,
        metadata={
            "statistics": {
                "total_words": wordlist.unique_words,
                "mastery_distribution": mastery_distribution,
                "study_sessions": wordlist.learning_stats.total_reviews,
                "total_study_time": wordlist.learning_stats.study_time_minutes,
            },
        },
        links={
            "self": f"/wordlists/{wordlist_id}",
            "words": f"/wordlists/{wordlist_id}/words",
            "review": f"/wordlists/{wordlist_id}/review",
            "stats": f"/wordlists/{wordlist_id}/stats",
        },
    )


@router.get("/{wordlist_id}/stats", response_model=ResourceResponse)
async def get_wordlist_statistics(
    wordlist_id: PydanticObjectId,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Get detailed wordlist statistics."""
    stats = await repo.get_statistics(wordlist_id)

    return ResourceResponse(
        data=stats,
        links={
            "wordlist": f"/wordlists/{wordlist_id}",
        },
    )


@router.put("/{wordlist_id}", response_model=ResourceResponse)
async def update_wordlist(
    wordlist_id: PydanticObjectId,
    data: WordListUpdate,
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Update wordlist metadata."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None
    await verify_wordlist_ownership(wordlist, user_id, user_role)

    wordlist = await repo.update(wordlist_id, data)

    return ResourceResponse(
        data=wordlist.model_dump(mode="json"),
        metadata={
            "version": wordlist.version,
        },
        links={
            "self": f"/wordlists/{wordlist_id}",
            "words": f"/wordlists/{wordlist_id}/words",
        },
    )


@router.delete("/{wordlist_id}", status_code=204, response_model=None)
async def delete_wordlist(
    wordlist_id: PydanticObjectId,
    user_id: CurrentUserDep,
    user_role: OptionalUserRoleDep = None,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Delete a wordlist."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None
    await verify_wordlist_ownership(wordlist, user_id, user_role)
    await repo.delete(wordlist_id)


@router.post("/{wordlist_id}/clone", response_model=ResourceResponse, status_code=201)
async def clone_wordlist(
    wordlist_id: PydanticObjectId,
    user_id: CurrentUserDep,
    name: str | None = Query(None, description="Name for cloned list"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Clone a wordlist with reset learning stats."""
    source = await repo.get(wordlist_id, raise_on_missing=True)
    assert source is not None

    # Get word texts for the clone by querying items collection
    source_items = await WordListItemDoc.find({"wordlist_id": wordlist_id}).to_list()
    word_ids = [item.word_id for item in source_items]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_texts = [w.text for w in words]

    clone_data = WordListCreate(
        name=name or f"{source.name} (copy)",
        description=source.description,
        words=word_texts,
        tags=source.tags,
        is_public=False,
        owner_id=user_id,
    )

    cloned, _ = await repo.create(clone_data)

    return ResourceResponse(
        data=cloned.model_dump(mode="json"),
        metadata={"cloned_from": str(wordlist_id), "word_count": cloned.unique_words},
        links={
            "self": f"/wordlists/{cloned.id}",
            "source": f"/wordlists/{wordlist_id}",
        },
    )


@router.get("/{wordlist_id}/export")
async def export_wordlist(
    wordlist_id: PydanticObjectId,
    format: str = Query("txt", description="Export format: txt, csv, json"),
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> StreamingResponse:
    """Export wordlist as a downloadable file."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Get items from items collection
    items = await WordListItemDoc.find({"wordlist_id": wordlist_id}).to_list()

    # Get word texts
    word_ids = [item.word_id for item in items]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(w.id): w.text for w in words}

    safe_name = wordlist.name.replace(" ", "_").replace("/", "_")[:50]

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["word", "mastery_level", "ease_factor", "interval", "repetitions", "lapse_count"]
        )
        for item in items:
            text = word_text_map.get(str(item.word_id), "")
            writer.writerow(
                [
                    text,
                    item.mastery_level.value,
                    item.review_data.ease_factor,
                    item.review_data.interval,
                    item.review_data.repetitions,
                    item.review_data.lapse_count,
                ]
            )
        content = output.getvalue().encode("utf-8")
        media_type = "text/csv"
        filename = f"{safe_name}.csv"
    elif format == "json":
        # Build JSON from already-fetched items (no extra DB round-trip)
        wordlist_dict = wordlist.model_dump(mode="json")
        wordlist_dict["words"] = [
            {
                "word": word_text_map.get(str(item.word_id), ""),
                "mastery_level": item.mastery_level.value,
                "ease_factor": item.review_data.ease_factor,
                "interval": item.review_data.interval,
                "repetitions": item.review_data.repetitions,
                "lapse_count": item.review_data.lapse_count,
                "notes": item.notes,
                "tags": item.tags,
            }
            for item in items
        ]
        content = json.dumps(wordlist_dict, indent=2, default=str).encode("utf-8")
        media_type = "application/json"
        filename = f"{safe_name}.json"
    else:
        # txt format
        lines = []
        for i, item in enumerate(items, 1):
            text = word_text_map.get(str(item.word_id), "")
            lines.append(f"{i}. {text}")
        content = "\n".join(lines).encode("utf-8")
        media_type = "text/plain"
        filename = f"{safe_name}.txt"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{wordlist_id}/export/anki")
async def export_wordlist_anki(
    wordlist_id: PydanticObjectId,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> StreamingResponse:
    """Export wordlist as Anki .apkg file."""
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Get items from items collection, then word texts and definitions
    anki_items = await WordListItemDoc.find({"wordlist_id": wordlist_id}).to_list()
    word_ids = [item.word_id for item in anki_items]
    words = await Word.find({"_id": {"$in": word_ids}}).to_list()
    word_text_map = {str(w.id): w.text for w in words}
    word_texts = [w.text for w in words]

    # Get definitions for these words
    definitions = await Definition.find({"word_id": {"$in": word_ids}}).to_list()
    word_defs: dict[str, list[str]] = {}
    for defn in definitions:
        text = word_text_map.get(str(defn.word_id), "")
        if text:
            if text not in word_defs:
                word_defs[text] = []
            word_defs[text].append(defn.text)

    try:
        from ....anki.generator import AnkiDeckGenerator

        generator = AnkiDeckGenerator()
        apkg_path = generator.generate(
            deck_name=wordlist.name,
            words=word_texts,
            definitions=word_defs,
        )

        return StreamingResponse(
            open(apkg_path, "rb"),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{wordlist.name}.apkg"',
            },
        )
    except ImportError:
        raise HTTPException(501, "Anki export requires genanki package")
    except Exception as e:
        raise HTTPException(500, f"Failed to generate Anki deck: {e!s}")


@router.post("/upload", response_model=ResourceResponse, status_code=201)
async def upload_wordlist(
    user_id: CurrentUserDep,
    file: UploadFile = File(...),
    name: str | None = None,
    description: str | None = None,
    is_public: bool = False,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Upload a wordlist from a file."""
    try:
        content = await file.read()

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        try:
            parsed = parse_file(tmp_path)

            if not name:
                name = generate_wordlist_name(parsed.words)

            data = WordListCreate(
                name=name,
                description=description or parsed.metadata.get("description", ""),
                is_public=is_public,
                tags=parsed.metadata.get("tags", []),
                words=parsed.words,
                owner_id=user_id,
            )

            wordlist, created = await repo.create(data)

            return ResourceResponse(
                data={
                    "id": str(wordlist.id),
                    "name": wordlist.name,
                    "word_count": wordlist.unique_words,
                    "created_at": wordlist.created_at.isoformat() if wordlist.created_at else None,
                },
                metadata={
                    "uploaded_filename": file.filename,
                    "parsed_words": len(parsed.words),
                    "created": created,
                },
                links={
                    "self": f"/wordlists/{wordlist.id}",
                    "words": f"/wordlists/{wordlist.id}/words",
                },
            )

        finally:
            tmp_path.unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(400, detail=f"Failed to parse file: {e!s}")


@router.post("/upload/stream", status_code=201)
async def upload_wordlist_stream(
    user_id: CurrentUserDep,
    file: UploadFile = File(...),
    name: str | None = None,
    description: str | None = None,
    is_public: bool = False,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> StreamingResponse:
    """Upload a wordlist with streaming progress updates."""
    content = await file.read()

    state_tracker = StateTracker(category="upload")

    async def upload_process() -> WordList:
        try:
            await state_tracker.update_stage(Stages.UPLOAD_START)
            await state_tracker.update(stage=Stages.UPLOAD_START, message="Starting upload...")
            await asyncio.sleep(0.1)

            await state_tracker.update_stage(Stages.UPLOAD_READING)
            await state_tracker.update(
                stage=Stages.UPLOAD_READING, message="File read successfully"
            )

            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)

            try:
                await state_tracker.update_stage(Stages.UPLOAD_PARSING)
                await state_tracker.update(
                    stage=Stages.UPLOAD_PARSING, message="Parsing words from file..."
                )
                parsed = parse_file(tmp_path)
                total_words = len(parsed.words)

                await state_tracker.update(
                    stage=Stages.UPLOAD_PARSING,
                    progress=35,
                    message=f"Found {total_words} words",
                )

                final_name = name
                if not final_name:
                    final_name = generate_wordlist_name(parsed.words)

                await state_tracker.update_stage(Stages.UPLOAD_PROCESSING)
                await state_tracker.update(
                    stage=Stages.UPLOAD_PROCESSING, message="Creating word entries..."
                )

                data = WordListCreate(
                    name=final_name,
                    description=description or parsed.metadata.get("description", ""),
                    is_public=is_public,
                    tags=parsed.metadata.get("tags", []),
                    words=parsed.words,
                    owner_id=user_id,
                )

                await state_tracker.update_stage(Stages.UPLOAD_CREATING)
                await state_tracker.update(
                    stage=Stages.UPLOAD_CREATING, message="Finalizing wordlist creation..."
                )
                wordlist, _ = await repo.create(data)

                await state_tracker.update_stage(Stages.UPLOAD_FINALIZING)
                await state_tracker.update(
                    stage=Stages.UPLOAD_FINALIZING, message="Completing upload..."
                )
                await state_tracker.update_complete(message="Upload completed successfully!")

                return wordlist

            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as e:
            await state_tracker.update_error(f"Failed to upload wordlist: {e!s}")
            raise

    return await create_streaming_response(
        state_tracker=state_tracker,
        process_func=upload_process,
        include_stage_definitions=True,
        include_completion_data=True,
    )
