"""Search endpoints for word discovery."""

from __future__ import annotations

import time
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...caching.decorators import cached_api_call
from ...constants import Language
from ...core.search_pipeline import get_search_engine, reset_search_engine
from ...search.constants import SearchMethod
from ...search.language import get_language_search
from ...utils.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)
router = APIRouter()


class SearchResultResponse[T](BaseModel):
    """Response for search operations with scoring and metadata."""

    query: str = Field(..., description="Original search query")
    results: list[T] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of matches")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")

    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return len(self.results) > 0


class SearchParams(BaseModel):
    """Parameters for search endpoint."""

    language: Language = Field(default=Language.ENGLISH, description="Search language")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum score")


class SearchResponseItem(BaseModel):
    """Single search result item."""

    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: SearchMethod = Field(..., description="Search method used")
    is_phrase: bool = Field(default=False, description="Is multi-word phrase")


class SearchResponse(SearchResultResponse[SearchResponseItem]):
    """Response for search query with language metadata."""

    language: Language = Field(..., description="Language searched")


class RebuildIndexRequest(BaseModel):
    """Request for rebuilding search index."""

    languages: list[Language] = Field(
        default=[Language.ENGLISH], description="Languages to rebuild (defaults to English)"
    )
    force_download: bool = Field(default=True, description="Force re-download of lexicon sources")


class RebuildIndexResponse(BaseModel):
    """Response for index rebuild operation."""

    status: str = Field(..., description="Rebuild status")
    languages: list[Language] = Field(..., description="Languages rebuilt")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Index statistics")
    message: str = Field(..., description="Status message")


def parse_search_params(
    language: str = Query(default="en", description="Language code"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(default=0.6, ge=0.0, le=1.0, description="Minimum score"),
) -> SearchParams:
    """Parse and validate search parameters."""
    try:
        language_enum = Language(language.lower())
    except ValueError:
        language_enum = Language.ENGLISH

    return SearchParams(
        language=language_enum,
        max_results=max_results,
        min_score=min_score,
    )


@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda query, params: (
        "api_search",
        query,
        params.language.value,
        params.max_results,
        params.min_score,
    ),
)
async def _cached_search(query: str, params: SearchParams) -> SearchResponse:
    """Cached search implementation."""
    logger.info(f"Searching for '{query}' in {params.language.value}")

    try:
        # Get language search instance
        language_search = await get_language_search(languages=[params.language])

        # Perform search
        results = await language_search.search(
            query=query,
            max_results=params.max_results,
            min_score=params.min_score,
        )

        # Convert to response format - optimized dictionary creation
        response_items = [
            SearchResponseItem(
                word=result.word,
                score=result.score,
                method=result.method,
                is_phrase=result.is_phrase,
            )
            for result in results
        ]

        return SearchResponse(
            query=query,
            results=response_items,
            total_found=len(results),
            language=params.language,
        )

    except Exception as e:
        logger.error(f"Failed to search for '{query}': {e}")
        raise


@router.get("/search", response_model=SearchResponse)
async def search_words_query(
    q: str = Query(..., description="Search query"),
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    """Search for words using query parameter."""
    start_time = time.perf_counter()

    try:
        result = await _cached_search(q, params)

        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Search completed: '{q}' -> {len(result.results)} results in {elapsed_ms}ms")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during search: {str(e)}")


@router.get("/search/{query}", response_model=SearchResponse)
async def search_words_path(
    query: str,
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    """Search for words using path parameter."""
    start_time = time.perf_counter()

    try:
        result = await _cached_search(query, params)

        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"Search completed: '{query}' -> {len(result.results)} results in {elapsed_ms}ms"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during search: {str(e)}")


@router.get("/search/{query}/suggestions", response_model=SearchResponse)
async def get_search_suggestions(
    query: str,
    limit: int = Query(default=8, ge=1, le=20, description="Maximum suggestions"),
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    """Get search suggestions for autocomplete (lower threshold)."""
    start_time = time.perf_counter()

    # Override parameters for suggestions
    suggestion_params = SearchParams(
        language=params.language,
        max_results=limit,
        min_score=0.3,  # Lower threshold for suggestions
    )

    try:
        result = await _cached_search(query, suggestion_params)

        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"Suggestions completed: '{query}' -> {len(result.results)} results in {elapsed_ms}ms"
        )

        return result

    except Exception as e:
        logger.error(f"Suggestions failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during suggestions: {str(e)}")


@router.post("/search/rebuild-index", response_model=RebuildIndexResponse)
async def rebuild_search_index(
    request: RebuildIndexRequest = RebuildIndexRequest(),
) -> RebuildIndexResponse:
    """
    Rebuild the search index for specified languages.

    This endpoint will:
    1. Clear the existing search engine singleton
    2. Re-download lexicon sources if force_download is True
    3. Rebuild all search indices (trie, fuzzy, semantic)
    4. Return statistics about the rebuilt index
    """
    logger.info(
        f"Rebuilding search index for languages: {[lang.value for lang in request.languages]}"
    )
    start_time = time.perf_counter()

    try:
        # Reset the search engine singleton
        await reset_search_engine()

        # Rebuild with force_rebuild flag
        search_engine = await get_search_engine(
            languages=request.languages, force_rebuild=request.force_download
        )

        # Get statistics from the rebuilt engine
        stats = search_engine.get_stats()

        elapsed_time = time.perf_counter() - start_time
        logger.info(f"Search index rebuilt successfully in {elapsed_time:.2f}s")

        return RebuildIndexResponse(
            status="success",
            languages=request.languages,
            statistics=stats,
            message=f"Search index rebuilt successfully in {elapsed_time:.2f}s",
        )

    except Exception as e:
        logger.error(f"Failed to rebuild search index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild search index: {str(e)}")
