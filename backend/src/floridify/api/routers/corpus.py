"""
Simplified corpus REST API with TTL cache.

Provides streamlined corpus creation and search with automatic cleanup.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...search.corpus.manager import get_corpus_manager
from ...utils.logging import get_logger
from ..core import ListResponse, PaginationParams, get_pagination
from ..repositories.corpus_repository import CorpusCreate, CorpusRepository, CorpusSearchParams

logger = get_logger(__name__)
router = APIRouter()


def get_corpus_repo() -> CorpusRepository:
    """Dependency to get corpus repository."""
    return CorpusRepository()


class CorpusSearchQueryParams(BaseModel):
    """Query parameters for corpus search."""

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results to return")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum relevance score")
    semantic: bool = Field(default=False, description="Enable semantic search")
    semantic_weight: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Weight for semantic results"
    )


class CreateCorpusRequest(BaseModel):
    """Request model for creating a corpus."""

    words: list[str] = Field(..., min_length=1, description="List of words to include")
    phrases: list[str] = Field(default_factory=list, description="Optional phrases")
    name: str = Field(default="", description="Optional corpus name")
    ttl_hours: float = Field(default=1.0, gt=0, le=24, description="Time to live in hours")


class CreateCorpusResponse(BaseModel):
    """Response model for corpus creation."""

    corpus_id: str = Field(..., description="Unique corpus identifier")
    vocabulary_size: int = Field(..., description="Total vocabulary size")


class SearchCorpusResponse(BaseModel):
    """Response model for corpus search."""

    results: list[dict[str, Any]] = Field(..., description="Search results")
    metadata: dict[str, Any] = Field(..., description="Search metadata")


class CorpusInfoResponse(BaseModel):
    """Response model for corpus metadata."""

    corpus_id: str = Field(..., description="Unique corpus identifier")
    name: str = Field(..., description="Corpus name")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: str = Field(..., description="Expiration timestamp")
    word_count: int = Field(..., description="Number of words")
    phrase_count: int = Field(..., description="Number of phrases")
    search_count: int = Field(..., description="Number of searches performed")
    last_accessed: str = Field(..., description="Last access timestamp")


# ListCorporaResponse removed - using ListResponse[CorpusInfoResponse] instead


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""

    status: str = Field(..., description="Cache status")
    cache: dict[str, Any] = Field(..., description="Cache statistics")
    message: str = Field(..., description="Status message")


@router.post("/corpus", response_model=CreateCorpusResponse, status_code=201)
async def create_corpus(
    request: CreateCorpusRequest,
    repo: CorpusRepository = Depends(get_corpus_repo),
) -> CreateCorpusResponse:
    """
    Create a new searchable corpus.

    Creates an in-memory corpus with TTL-based auto-cleanup.
    Returns a unique ID for subsequent search operations.
    """
    try:
        # Combine words and phrases into vocabulary
        vocabulary = request.words + request.phrases

        data = CorpusCreate(
            vocabulary=vocabulary,
            name=request.name,
        )

        result = await repo.create(data)

        return CreateCorpusResponse(
            corpus_id=result["corpus_id"],
            vocabulary_size=result["vocabulary_size"],
        )

    except Exception as e:
        logger.error(f"Failed to create corpus: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create corpus: {e}")


@router.get("/corpus/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    repo: CorpusRepository = Depends(get_corpus_repo),
) -> CacheStatsResponse:
    """
    Get cache statistics.

    Returns overall cache usage and performance metrics.
    """
    try:
        stats = await repo.get_stats()

        return CacheStatsResponse(
            status="active", cache=stats, message="Simplified corpus cache is active"
        )

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")


@router.get("/corpus", response_model=ListResponse[CorpusInfoResponse])
async def list_corpora(
    repo: CorpusRepository = Depends(get_corpus_repo),
    pagination: PaginationParams = Depends(get_pagination),
) -> ListResponse[CorpusInfoResponse]:
    """
    List all active corpora with pagination.

    Returns summary of all non-expired corpora with basic metadata.
    """
    try:
        corpora_data = await repo.list_all()

        # Apply pagination
        total = len(corpora_data)
        start = pagination.offset
        end = start + pagination.limit
        paginated_data = corpora_data[start:end]

        return ListResponse(
            items=[CorpusInfoResponse(**corpus) for corpus in paginated_data],
            total=total,
            offset=pagination.offset,
            limit=pagination.limit,
        )

    except Exception as e:
        logger.error(f"Failed to list corpora: {e}")
        raise HTTPException(status_code=500, detail="Failed to list corpora")


@router.post("/corpus/{corpus_id}/search", response_model=SearchCorpusResponse)
async def search_corpus(
    corpus_id: str,
    params: CorpusSearchQueryParams = Depends(),
    repo: CorpusRepository = Depends(get_corpus_repo),
) -> SearchCorpusResponse:
    """
    Search within a corpus.

    Performs multi-method search (exact, prefix, fuzzy, and optionally semantic) within the specified corpus.
    Returns error if corpus doesn't exist or has expired.
    """
    try:
        search_params = CorpusSearchParams(
            query=params.query,
            max_results=params.max_results,
            min_score=params.min_score,
            semantic=params.semantic,
            semantic_weight=params.semantic_weight,
        )

        search_results = await repo.search(corpus_id, search_params)
        return SearchCorpusResponse(**search_results)

    except ValueError as e:
        # Corpus not found or expired
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to search corpus {corpus_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.get("/corpus/{corpus_id}", response_model=CorpusInfoResponse)
async def get_corpus_info(
    corpus_id: str,
    repo: CorpusRepository = Depends(get_corpus_repo),
) -> CorpusInfoResponse:
    """
    Get corpus metadata and statistics.

    Returns corpus information including creation time, expiration, and usage stats.
    """
    try:
        metadata = await repo.get(corpus_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Corpus {corpus_id} not found or expired")

        return CorpusInfoResponse(**metadata)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get corpus info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get corpus info")


class InvalidateCorpusRequest(BaseModel):
    """Request for invalidating corpus caches."""

    specific_corpus_id: str | None = Field(None, description="Specific corpus ID to invalidate")
    invalidate_all: bool = Field(default=False, description="Invalidate all corpus caches")


class InvalidateCorpusResponse(BaseModel):
    """Response for corpus cache invalidation."""

    status: str = Field(..., description="Operation status")
    total_invalidated: int = Field(..., description="Total number of entries invalidated")
    message: str = Field(..., description="Status message")


@router.post("/corpus/invalidate", response_model=InvalidateCorpusResponse)
async def invalidate_corpus(
    request: InvalidateCorpusRequest = InvalidateCorpusRequest(
        specific_corpus_id=None, invalidate_all=False
    ),
) -> InvalidateCorpusResponse:
    """
    Invalidate corpus caches.

    Allows invalidating a specific corpus by ID or all corpus caches.
    """
    logger.info(
        f"Corpus invalidation: specific={request.specific_corpus_id}, all={request.invalidate_all}"
    )

    try:
        corpus_manager = get_corpus_manager()
        total_invalidated = 0

        if request.specific_corpus_id:
            # Invalidate specific corpus by name
            success = await corpus_manager.invalidate_corpus(request.specific_corpus_id)
            total_invalidated = 1 if success else 0
            message = (
                f"Invalidated corpus '{request.specific_corpus_id}'"
                if success
                else "Corpus not found"
            )
        elif request.invalidate_all:
            # Invalidate all corpora
            result = await corpus_manager.invalidate_all_corpora()
            total_invalidated = result.get("total", 0)
            message = f"Invalidated {total_invalidated} corpus entries"
        else:
            message = "No invalidation action specified"

        return InvalidateCorpusResponse(
            status="success" if total_invalidated > 0 else "no_action",
            total_invalidated=total_invalidated,
            message=message,
        )

    except Exception as e:
        logger.error(f"Failed to invalidate corpus caches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate corpus caches: {str(e)}")
