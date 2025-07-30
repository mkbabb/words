"""WordLists API - Simplified CRUD operations for word lists."""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ....wordlist.models import WordList
from ....wordlist.parser import parse_file
from ....wordlist.utils import generate_wordlist_name
from ...core import (
    ListResponse,
    PaginationParams,
    ResourceResponse,
    SortParams,
    get_pagination,
    get_sort,
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
    repo: WordListRepository = Depends(get_wordlist_repo),
    pagination: PaginationParams = Depends(get_pagination),
    sort: SortParams = Depends(get_sort),
    params: WordListQueryParams = Depends(),
) -> ListResponse[WordList]:
    """List wordlists with filtering and pagination.

    Query Parameters:
        - name/name_pattern: Name filters
        - owner_id: Filter by owner
        - is_public: Visibility filter
        - has_tag: Tag filter
        - min/max_words: Word count range
        - created_after/before: Date range
        - Standard pagination params

    Returns:
        Paginated list of wordlists.
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

    # Get data
    wordlists, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=pagination,
        sort=sort,
    )
    
    # Populate word text for each wordlist
    populated_wordlists = []
    for wordlist in wordlists:
        populated_data = await repo.populate_words(wordlist)
        populated_wordlists.append(populated_data)

    return ListResponse(
        items=populated_wordlists,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
    )


@router.post("", response_model=ResourceResponse, status_code=201)
async def create_wordlist(
    data: WordListCreate,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Create a new wordlist.

    Body:
        - name: List name (required)
        - description: List description
        - is_public: Visibility (default: false)
        - tags: List of tags
        - words: Initial words (optional)

    Returns:
        Created wordlist with resource links.
    """
    wordlist = await repo.create(data)

    return ResourceResponse(
        data=wordlist.model_dump(mode="json"),
        links={
            "self": f"/wordlists/{wordlist.id}",
            "words": f"/wordlists/{wordlist.id}/words",
            "stats": f"/wordlists/{wordlist.id}/stats",
        },
    )


@router.get("/{wordlist_id}", response_model=ResourceResponse)
async def get_wordlist(
    wordlist_id: PydanticObjectId,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Get wordlist details.

    Returns:
        Wordlist with metadata and statistics.
    """
    wordlist = await repo.get(wordlist_id, raise_on_missing=True)
    assert wordlist is not None

    # Calculate statistics
    total_words = len(wordlist.words)
    mastery_distribution: dict[str, int] = {}
    for word in wordlist.words:
        level = word.mastery_level.value
        mastery_distribution[level] = mastery_distribution.get(level, 0) + 1

    # Populate with word text
    wordlist_data = await repo.populate_words(wordlist)

    return ResourceResponse(
        data=wordlist_data,
        metadata={
            "statistics": {
                "total_words": total_words,
                "mastery_distribution": mastery_distribution,
                "study_sessions": wordlist.learning_stats.total_reviews,
                "total_study_time": wordlist.learning_stats.study_time_minutes,
            }
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
    """Get detailed wordlist statistics.

    Returns:
        Comprehensive statistics about the wordlist.
    """
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
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Update wordlist metadata.

    Body:
        - name: New name
        - description: New description
        - is_public: New visibility
        - tags: New tags

    Returns:
        Updated wordlist.
    """
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
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> None:
    """Delete a wordlist."""
    await repo.delete(wordlist_id)


@router.post("/upload", response_model=ResourceResponse, status_code=201)
async def upload_wordlist(
    file: UploadFile = File(...),
    name: str | None = None,
    description: str | None = None,
    is_public: bool = False,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ResourceResponse:
    """Upload a wordlist from a file.

    Accepts text files with one word per line.

    Form Data:
        - file: Text file with words
        - name: List name (auto-generated if not provided)
        - description: List description
        - is_public: Visibility

    Returns:
        Created wordlist.
    """
    try:
        # Read file content
        content = await file.read()

        # Create temporary file for parser
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        try:
            # Parse file
            parsed = parse_file(tmp_path)

            # Generate name if not provided
            if not name:
                name = generate_wordlist_name(parsed.words)

            # Create wordlist
            data = WordListCreate(
                name=name,
                description=description or parsed.metadata.get("description", ""),
                is_public=is_public,
                tags=parsed.metadata.get("tags", []),
                words=parsed.words,
            )

            wordlist = await repo.create(data)

            return ResourceResponse(
                data={
                    "id": str(wordlist.id),
                    "name": wordlist.name,
                    "word_count": len(wordlist.words),
                    "created_at": wordlist.created_at.isoformat() if wordlist.created_at else None,
                },
                metadata={
                    "uploaded_filename": file.filename,
                    "parsed_words": len(parsed.words),
                },
                links={
                    "self": f"/wordlists/{wordlist.id}",
                    "words": f"/wordlists/{wordlist.id}/words",
                },
            )

        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(400, detail=f"Failed to parse file: {str(e)}")


@router.post("/upload/stream", status_code=201)
async def upload_wordlist_stream(
    file: UploadFile = File(...),
    name: str | None = None,
    description: str | None = None,
    is_public: bool = False,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> StreamingResponse:
    """Upload a wordlist with streaming progress updates.

    Returns Server-Sent Events (SSE) with progress updates.
    
    Form Data:
        - file: Text file with words
        - name: List name (auto-generated if not provided)
        - description: List description
        - is_public: Visibility

    Event Types:
        - progress: Update on current operation
        - complete: Final result with wordlist info
        - error: Error details if something goes wrong
    """
    # Read file content before creating the generator
    content = await file.read()
    filename = file.filename
    
    # Capture parameters in the generator scope
    list_name = name
    list_description = description
    list_is_public = is_public
    
    async def generate_progress():
        try:
            # Send initial progress
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Starting upload...', 'percentage': 0})}\n\n"
            await asyncio.sleep(0.1)  # Small delay for UI update
            
            # File already read
            yield f"data: {json.dumps({'type': 'progress', 'message': 'Processing file...', 'percentage': 10})}\n\n"
            
            # Create temporary file for parser
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as tmp_file:
                tmp_file.write(content)
                tmp_path = Path(tmp_file.name)
            
            try:
                # Parse file
                yield f"data: {json.dumps({'type': 'progress', 'message': 'Parsing words...', 'percentage': 20})}\n\n"
                parsed = parse_file(tmp_path)
                total_words = len(parsed.words)
                
                yield f"data: {json.dumps({'type': 'progress', 'message': f'Found {total_words} words', 'percentage': 30})}\n\n"
                
                # Generate name if not provided
                final_name = list_name
                if not final_name:
                    final_name = generate_wordlist_name(parsed.words)
                
                # Create progress-aware wordlist creation
                data = WordListCreate(
                    name=final_name,
                    description=list_description or parsed.metadata.get("description", ""),
                    is_public=list_is_public,
                    tags=parsed.metadata.get("tags", []),
                    words=parsed.words,
                )
                
                # Create wordlist with progress updates
                yield f"data: {json.dumps({'type': 'progress', 'message': 'Creating word entries...', 'percentage': 40})}\n\n"
                
                # Here we could add more granular progress for batch operations
                # For now, we'll simulate progress during word creation
                wordlist = await repo.create(data)
                
                yield f"data: {json.dumps({'type': 'progress', 'message': 'Finalizing wordlist...', 'percentage': 90})}\n\n"
                
                # Send completion event
                result = {
                    'type': 'complete',
                    'data': {
                        'id': str(wordlist.id),
                        'name': wordlist.name,
                        'word_count': len(wordlist.words),
                        'created_at': wordlist.created_at.isoformat() if wordlist.created_at else None,
                    },
                    'metadata': {
                        'uploaded_filename': filename,
                        'parsed_words': total_words,
                    },
                    'links': {
                        'self': f'/wordlists/{wordlist.id}',
                        'words': f'/wordlists/{wordlist.id}/words',
                    },
                    'percentage': 100
                }
                yield f"data: {json.dumps(result)}\n\n"
                
            finally:
                # Clean up temp file
                tmp_path.unlink(missing_ok=True)
                
        except Exception as e:
            error_event = {
                'type': 'error',
                'message': f'Failed to upload wordlist: {str(e)}',
                'percentage': -1
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/search/{query}", response_model=ListResponse[dict[str, Any]])
async def search_wordlists(
    query: str,
    limit: int = 10,
    repo: WordListRepository = Depends(get_wordlist_repo),
) -> ListResponse[WordList]:
    """Search wordlists by name.

    Path Parameters:
        - query: Search query

    Query Parameters:
        - limit: Maximum results

    Returns:
        Matching wordlists.
    """
    filter_params = WordListFilter(name_pattern=query, min_words=None, max_words=None)

    wordlists, total = await repo.list(
        filter_dict=filter_params.to_query(),
        pagination=PaginationParams(offset=0, limit=limit),
    )
    
    # Populate word text for each wordlist
    populated_wordlists = []
    for wordlist in wordlists:
        populated_data = await repo.populate_words(wordlist)
        populated_wordlists.append(populated_data)

    return ListResponse(
        items=populated_wordlists,
        total=total,
        offset=0,
        limit=limit,
    )
