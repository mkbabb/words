"""Search endpoints for word discovery."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...caching.core import CacheNamespace, get_global_cache
from ...core.search_pipeline import get_search_engine, reset_search_engine
from ...corpus.manager import get_corpus_manager
from ...corpus.models import CorpusType
from ...models.base import Language
from ...search.constants import SearchMode
from ...search.language import get_language_search
from ...search.models import SearchResult
from ...text import clear_lemma_cache, get_lemma_cache_stats
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class SearchParams(BaseModel):
    """Parameters for search endpoint."""

    language: Language = Field(default=Language.ENGLISH, description="Search language")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum score")
    mode: SearchMode = Field(
        default=SearchMode.SMART,
        description="Search mode: smart, exact, fuzzy, semantic",
    )


class SearchResponse(BaseModel):
    """Response for search operations with unified SearchResult model."""

    query: str = Field(..., description="Original search query")
    results: list[SearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of matches")
    language: Language = Field(..., description="Language searched")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")

    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return len(self.results) > 0

    class Config:
        json_schema_extra = {
            "example": {
                "query": "test",
                "results": [{"word": "test", "score": 1.0, "method": "exact", "is_phrase": False}],
                "total_found": 1,
                "language": "en",
                "metadata": {"search_time_ms": 15},
            },
        }


class RebuildIndexRequest(BaseModel):
    """Enhanced request for rebuilding search index with unified corpus management."""

    # Language and source options
    languages: list[Language] = Field(
        default=[Language.ENGLISH],
        description="Languages to rebuild (defaults to English)",
    )
    force_download: bool = Field(default=True, description="Force re-download of lexicon sources")

    # Unified corpus management options
    corpus_types: list[str] = Field(
        default=["language_search"],
        description="Corpus types to rebuild: 'language_search', 'wordlist', 'wordlist_names', 'custom'",
    )
    rebuild_all_corpora: bool = Field(default=False, description="Rebuild all corpus types")

    # Semantic search options
    rebuild_semantic: bool = Field(default=True, description="Rebuild semantic search indices")
    semantic_force_rebuild: bool = Field(
        default=False,
        description="Force rebuild semantic even if cached",
    )
    quantization_type: str = Field(
        default="binary",
        description="Quantization method: 'binary', 'scalar', 'none'",
    )
    auto_semantic_small_corpora: bool = Field(
        default=True,
        description="Auto-enable semantic for small corpora (<10k words)",
    )

    # Cache management options
    clear_existing_cache: bool = Field(
        default=False,
        description="Clear all existing caches before rebuild",
    )
    clear_semantic_cache: bool = Field(default=False, description="Clear only semantic caches")
    clear_lexicon_cache: bool = Field(default=False, description="Clear only lexicon caches")

    # Performance options
    enable_lemmatization_cache: bool = Field(
        default=True,
        description="Enable lemmatization memoization",
    )
    batch_size: int = Field(default=1000, ge=100, le=5000, description="Batch size for processing")

    # Validation options
    validate_vocabulary: bool = Field(default=True, description="Validate vocabulary quality")
    min_word_length: int = Field(default=2, ge=1, le=10, description="Minimum word length")
    max_word_length: int = Field(default=50, ge=10, le=100, description="Maximum word length")


class RebuildIndexResponse(BaseModel):
    """Enhanced response for index rebuild operation with unified corpus management."""

    status: str = Field(..., description="Rebuild status")
    languages: list[Language] = Field(..., description="Languages rebuilt")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Index statistics")
    message: str = Field(..., description="Status message")

    # Performance metrics
    total_time_seconds: float = Field(..., description="Total rebuild time in seconds")
    semantic_build_time_seconds: float = Field(default=0.0, description="Semantic index build time")
    vocabulary_optimization_ratio: float = Field(
        default=1.0,
        description="Vocabulary reduction ratio",
    )

    # Unified corpus management results
    corpus_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Corpus rebuild results by type",
    )
    corpus_manager_stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Corpus manager statistics",
    )

    # Cache management results
    caches_cleared: dict[str, int] = Field(
        default_factory=dict,
        description="Caches cleared counts",
    )
    compression_stats: dict[str, float] = Field(
        default_factory=dict,
        description="Compression statistics",
    )

    # Quality metrics
    vocabulary_quality: dict[str, Any] = Field(
        default_factory=dict,
        description="Vocabulary validation results",
    )
    lemmatization_stats: dict[str, int] = Field(
        default_factory=dict,
        description="Lemmatization cache statistics",
    )


def parse_search_params(
    language: str = Query(default="en", description="Language code"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(default=0.6, ge=0.0, le=1.0, description="Minimum score"),
    mode: str = Query(default="smart", description="Search mode: smart, exact, fuzzy, semantic"),
) -> SearchParams:
    """Parse and validate search parameters."""
    try:
        language_enum = Language(language.lower())
    except ValueError:
        language_enum = Language.ENGLISH

    try:
        mode_enum = SearchMode(mode.lower())
    except ValueError:
        mode_enum = SearchMode.SMART

    return SearchParams(
        language=language_enum,
        max_results=max_results,
        min_score=min_score,
        mode=mode_enum,
    )


# @cached_api_call(
#     ttl_hours=1.0,
#     key_prefix="search",
# )
async def _cached_search(query: str, params: SearchParams) -> SearchResponse:
    """Cached search implementation."""
    logger.info(f"Searching for '{query}' in {params.language.value} (mode={params.mode.value})")

    try:
        # Get language search instance
        language_search = await get_language_search(languages=[params.language])

        # Perform search with specified mode
        results = await language_search.search_with_mode(
            query=query,
            mode=params.mode,
            max_results=params.max_results,
            min_score=params.min_score,
        )

        # Results are already in SearchResult format
        response_items = results

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
        raise HTTPException(status_code=500, detail=f"Internal error during search: {e!s}")


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
            f"Search completed: '{query}' -> {len(result.results)} results in {elapsed_ms}ms",
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during search: {e!s}")


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
            f"Suggestions completed: '{query}' -> {len(result.results)} results in {elapsed_ms}ms",
        )

        return result

    except Exception as e:
        logger.error(f"Suggestions failed for '{query}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal error during suggestions: {e!s}")


@router.post("/search/rebuild", response_model=RebuildIndexResponse)
async def rebuild_search_index(
    request: RebuildIndexRequest = RebuildIndexRequest(),
) -> RebuildIndexResponse:
    """Streamlined rebuild of search index with unified corpus management.

    This endpoint provides unified control over:
    1. All corpus types (language_search, wordlist, wordlist_names, custom)
    2. Automatic semantic embeddings for small corpora
    3. Integrated cache management through CorpusManager
    4. Performance optimization and quality validation
    """
    logger.info(
        f"Rebuilding search index with unified corpus management: "
        f"languages={[lang.value for lang in request.languages]}, "
        f"corpus_types={request.corpus_types}, semantic={request.rebuild_semantic}",
    )
    start_time = time.perf_counter()

    try:
        # Initialize unified corpus manager
        corpus_manager = get_corpus_manager()

        # Determine corpus types to rebuild
        target_corpus_types = []
        if request.rebuild_all_corpora:
            target_corpus_types = [
                CorpusType.LANGUAGE_SEARCH,
                CorpusType.WORDLIST,
                CorpusType.WORDLIST_NAMES,
            ]
        else:
            corpus_type_map = {
                "language_search": CorpusType.LANGUAGE_SEARCH,
                "wordlist": CorpusType.WORDLIST,
                "wordlist_names": CorpusType.WORDLIST_NAMES,
                "custom": CorpusType.CUSTOM,
            }
            target_corpus_types = [
                corpus_type_map.get(ct.lower(), CorpusType.LANGUAGE_SEARCH)
                for ct in request.corpus_types
            ]

        # Always clear all caches during rebuild to ensure fresh data
        caches_cleared = {}

        # Clear vocabulary caches

        cache = await get_global_cache()
        vocab_cleared = await cache.invalidate_namespace(CacheNamespace.CORPUS)
        caches_cleared["vocabulary_caches"] = vocab_cleared

        # Clear semantic caches
        # Cleanup expired entries in unified cache
        await get_global_cache()
        semantic_cleared = 0  # Unified cache handles expiration automatically
        caches_cleared["semantic_expired"] = semantic_cleared

        # Clear corpus caches
        corpus_cleared_result = await corpus_manager.invalidate_all_corpora()
        corpus_cleared = corpus_cleared_result.get("total", 0)
        caches_cleared["corpus_caches"] = corpus_cleared

        # Lemmatization cache management
        lemmatization_stats: dict[str, int] = {}
        if request.enable_lemmatization_cache:
            clear_lemma_cache()  # Returns None
            lemmatization_stats["cache_cleared"] = 1  # Use int instead of bool

        # Rebuild each corpus type using unified manager
        corpus_results = {}
        semantic_start = time.perf_counter()

        for corpus_type in target_corpus_types:
            if corpus_type == CorpusType.LANGUAGE_SEARCH:
                # Rebuild language search corpus (main search engine)
                await reset_search_engine()
                search_engine = await get_search_engine(
                    languages=request.languages,
                    force_rebuild=request.force_download
                    or request.semantic_force_rebuild
                    or request.clear_lexicon_cache,
                )
                stats = search_engine.get_stats()
                corpus_results["language_search"] = {
                    "status": "rebuilt",
                    "languages": [lang.value for lang in request.languages],
                    "vocabulary_size": stats.get("vocabulary_size", 0),
                    "semantic_enabled": request.rebuild_semantic,
                }
            else:
                # Invalidate specific corpus to trigger rebuild on next use
                # Note: Currently invalidate_all_corpora doesn't support type filtering
                corpus_results[corpus_type.value] = {
                    "status": "marked_for_rebuild",
                    "note": "Will rebuild automatically on next use",
                }

        semantic_build_time = time.perf_counter() - semantic_start

        # Get corpus manager statistics
        corpus_manager_stats = await corpus_manager.get_stats()

        # Compression statistics
        compression_stats: dict[str, float] = {}
        if request.rebuild_semantic:
            compression_stats = {
                "estimated_compression_ratio": 24.0
                if request.quantization_type == "binary"
                else 3.75,
            }

        # Vocabulary quality analysis
        vocabulary_quality = {}
        if request.validate_vocabulary and "language_search" in corpus_results:
            ls_stats = corpus_results["language_search"]
            total_vocab = ls_stats.get("vocabulary_size", 0)
            vocabulary_quality = {
                "total_entries": total_vocab,
                "validation_passed": total_vocab > 1000,
                "semantic_auto_enabled": total_vocab <= 10000
                and request.auto_semantic_small_corpora,
            }

        # Final performance metrics
        total_elapsed = time.perf_counter() - start_time

        # Update lemmatization stats
        cache_stats = get_lemma_cache_stats()
        lemmatization_stats.update(
            {
                "cache_size": cache_stats["size"],
                "cache_hits": cache_stats["hits"],
                "cache_misses": cache_stats["misses"],
                "cache_enabled": 1 if request.enable_lemmatization_cache else 0,
            },
        )

        logger.info(f"Unified corpus rebuild completed in {total_elapsed:.2f}s")

        return RebuildIndexResponse(
            status="success",
            languages=request.languages,
            statistics=corpus_manager_stats,
            message=f"Unified corpus management rebuild completed in {total_elapsed:.2f}s",
            total_time_seconds=total_elapsed,
            semantic_build_time_seconds=semantic_build_time,
            vocabulary_optimization_ratio=vocabulary_quality.get("optimization_ratio", 1.0),
            corpus_results=corpus_results,
            corpus_manager_stats=corpus_manager_stats,
            caches_cleared=caches_cleared,
            compression_stats=compression_stats,
            vocabulary_quality=vocabulary_quality,
            lemmatization_stats=lemmatization_stats,
        )

    except Exception as e:
        logger.error(f"Failed to rebuild search index with unified corpus management: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rebuild search index: {e!s}")
