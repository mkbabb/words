"""
Simplified corpus REST API with TTL cache.

Provides streamlined corpus creation and search with automatic cleanup.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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


class CreateCorpusRequest(BaseModel):
    """Request model for creating a corpus."""

    words: list[str] = Field(..., min_length=1, description="List of words to include")
    phrases: list[str] = Field(default_factory=list, description="Optional phrases")
    name: str = Field(default="", description="Optional corpus name")
    ttl_hours: float = Field(default=1.0, gt=0, le=24, description="Time to live in hours")


class CreateCorpusResponse(BaseModel):
    """Response model for corpus creation."""

    corpus_id: str = Field(..., description="Unique corpus identifier")
    word_count: int = Field(..., description="Number of words added")
    phrase_count: int = Field(..., description="Number of phrases added")
    expires_at: str = Field(..., description="Expiration timestamp")


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


@router.post("/corpus", response_model=CreateCorpusResponse)
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
        data = CorpusCreate(
            words=request.words,
            phrases=request.phrases,
            name=request.name,
            ttl_hours=request.ttl_hours,
        )

        result = await repo.create(data)

        return CreateCorpusResponse(
            corpus_id=result["corpus_id"],
            word_count=result["word_count"],
            phrase_count=result["phrase_count"],
            expires_at=result["expires_at"],
        )

    except Exception as e:
        logger.error(f"Failed to create corpus: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create corpus: {e}")


@router.post("/corpus/{corpus_id}/search", response_model=SearchCorpusResponse)
async def search_corpus(
    corpus_id: str,
    params: CorpusSearchQueryParams = Depends(),
    repo: CorpusRepository = Depends(get_corpus_repo),
) -> SearchCorpusResponse:
    """
    Search within a corpus.

    Performs multi-method search (exact, prefix, fuzzy) within the specified corpus.
    Returns error if corpus doesn't exist or has expired.
    """
    try:
        search_params = CorpusSearchParams(
            query=params.query,
            max_results=params.max_results,
            min_score=params.min_score,
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
