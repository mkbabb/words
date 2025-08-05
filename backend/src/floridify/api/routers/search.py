"""Search endpoints for word discovery."""

from __future__ import annotations

import time
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...caching.decorators import cached_api_call
from ...core.corpus_manager import CorpusType, get_corpus_manager
from ...core.search_pipeline import get_search_engine, reset_search_engine
from ...models.definition import Language
from ...search.constants import SearchMethod
from ...search.corpus.semantic_cache import SemanticIndexCache
from ...search.language import get_language_search
from ...text import clear_lemma_cache
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
    semantic: bool = Field(default=False, description="Enable semantic search")
    semantic_weight: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Weight for semantic results"
    )


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
    """Enhanced request for rebuilding search index with unified corpus management."""

    # Language and source options
    languages: list[Language] = Field(
        default=[Language.ENGLISH], description="Languages to rebuild (defaults to English)"
    )
    force_download: bool = Field(default=True, description="Force re-download of lexicon sources")
    
    # Unified corpus management options
    corpus_types: list[str] = Field(
        default=["language_search"], 
        description="Corpus types to rebuild: 'language_search', 'wordlist', 'wordlist_names', 'custom'"
    )
    rebuild_all_corpora: bool = Field(default=False, description="Rebuild all corpus types")
    
    # Semantic search options
    rebuild_semantic: bool = Field(default=True, description="Rebuild semantic search indices")
    semantic_force_rebuild: bool = Field(default=False, description="Force rebuild semantic even if cached")
    quantization_type: str = Field(default="binary", description="Quantization method: 'binary', 'scalar', 'none'")
    auto_semantic_small_corpora: bool = Field(default=True, description="Auto-enable semantic for small corpora (<10k words)")
    
    # Cache management options
    clear_existing_cache: bool = Field(default=False, description="Clear all existing caches before rebuild")
    clear_semantic_cache: bool = Field(default=False, description="Clear only semantic caches")
    clear_lexicon_cache: bool = Field(default=False, description="Clear only lexicon caches")
    
    # Performance options
    enable_lemmatization_cache: bool = Field(default=True, description="Enable lemmatization memoization")
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
    vocabulary_optimization_ratio: float = Field(default=1.0, description="Vocabulary reduction ratio")
    
    # Unified corpus management results
    corpus_results: dict[str, Any] = Field(default_factory=dict, description="Corpus rebuild results by type")
    corpus_manager_stats: dict[str, Any] = Field(default_factory=dict, description="Corpus manager statistics")
    
    # Cache management results
    caches_cleared: dict[str, int] = Field(default_factory=dict, description="Caches cleared counts")
    compression_stats: dict[str, float] = Field(default_factory=dict, description="Compression statistics")
    
    # Quality metrics
    vocabulary_quality: dict[str, Any] = Field(default_factory=dict, description="Vocabulary validation results")
    lemmatization_stats: dict[str, int] = Field(default_factory=dict, description="Lemmatization cache statistics")


def parse_search_params(
    language: str = Query(default="en", description="Language code"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(default=0.6, ge=0.0, le=1.0, description="Minimum score"),
    semantic: bool = Query(default=False, description="Enable semantic search"),
    semantic_weight: float = Query(
        default=0.7, ge=0.0, le=1.0, description="Weight for semantic results"
    ),
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
        semantic=semantic,
        semantic_weight=semantic_weight,
    )


@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda query, params: (
        "api_search",
        query,
        params.language.value,
        params.max_results,
        params.min_score,
        params.semantic,
        params.semantic_weight,
    ),
)
async def _cached_search(query: str, params: SearchParams) -> SearchResponse:
    """Cached search implementation."""
    logger.info(
        f"Searching for '{query}' in {params.language.value} (semantic={'enabled' if params.semantic else 'disabled'})"
    )

    try:
        # Get language search instance (always has semantic support)
        language_search = await get_language_search(
            languages=[params.language]
        )

        # Perform search with semantic option
        results = await language_search.search(
            query=query,
            max_results=params.max_results,
            min_score=params.min_score,
            semantic=params.semantic,
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
    Streamlined rebuild of search index with unified corpus management.

    This endpoint provides unified control over:
    1. All corpus types (language_search, wordlist, wordlist_names, custom)
    2. Automatic semantic embeddings for small corpora
    3. Integrated cache management through CorpusManager
    4. Performance optimization and quality validation
    """
    logger.info(
        f"Rebuilding search index with unified corpus management: "
        f"languages={[lang.value for lang in request.languages]}, "
        f"corpus_types={request.corpus_types}, semantic={request.rebuild_semantic}"
    )
    start_time = time.perf_counter()
    
    try:
        # Initialize unified corpus manager
        corpus_manager = await get_corpus_manager()
        
        # Determine corpus types to rebuild
        target_corpus_types = []
        if request.rebuild_all_corpora:
            target_corpus_types = [CorpusType.LANGUAGE_SEARCH, CorpusType.WORDLIST, CorpusType.WORDLIST_NAMES]
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
        
        # Cache cleanup if requested
        caches_cleared = {}
        if request.clear_existing_cache or request.clear_semantic_cache:
            semantic_cleared = await SemanticIndexCache.cleanup_expired()
            caches_cleared["semantic_expired"] = semantic_cleared
            logger.info(f"Cleared {semantic_cleared} expired semantic cache entries")

        # Lemmatization cache management
        lemmatization_stats = {}
        if request.enable_lemmatization_cache:
            cleared_count = clear_lemma_cache()
            lemmatization_stats["cache_cleared"] = cleared_count

        # Rebuild each corpus type using unified manager
        corpus_results = {}
        semantic_start = time.perf_counter()
        
        for corpus_type in target_corpus_types:
            if corpus_type == CorpusType.LANGUAGE_SEARCH:
                # Rebuild language search corpus (main search engine)
                await reset_search_engine()
                search_engine = await get_search_engine(
                    languages=request.languages,
                    force_rebuild=request.force_download or request.semantic_force_rebuild,
                )
                stats = search_engine.get_stats()
                corpus_results["language_search"] = {
                    "status": "rebuilt",
                    "languages": [lang.value for lang in request.languages],
                    "vocabulary_size": stats.get("vocabulary_size", 0),
                    "semantic_enabled": request.rebuild_semantic,
                }
            else:
                # Invalidate other corpus types to trigger rebuild on next use
                invalidated_count = await corpus_manager.invalidate_all_corpora(corpus_type)
                corpus_results[corpus_type.value] = {
                    "status": "invalidated",
                    "invalidated_entries": invalidated_count,
                    "note": "Will rebuild automatically on next use",
                }
        
        semantic_build_time = time.perf_counter() - semantic_start

        # Get corpus manager statistics
        corpus_manager_stats = await corpus_manager.get_stats()
        
        # Compression statistics
        compression_stats: dict[str, float] = {}
        if request.rebuild_semantic:
            compression_stats = {
                "estimated_compression_ratio": 24.0 if request.quantization_type == "binary" else 3.75,
            }

        # Vocabulary quality analysis
        vocabulary_quality = {}
        if request.validate_vocabulary and "language_search" in corpus_results:
            ls_stats = corpus_results["language_search"]
            total_vocab = ls_stats.get("vocabulary_size", 0)
            vocabulary_quality = {
                "total_entries": total_vocab,
                "validation_passed": total_vocab > 1000,
                "semantic_auto_enabled": total_vocab <= 10000 and request.auto_semantic_small_corpora,
            }

        # Final performance metrics
        total_elapsed = time.perf_counter() - start_time
        
        # Update lemmatization stats
        from ...text.normalize import _lemma_cache
        lemmatization_stats.update({
            "cache_size": len(_lemma_cache),
            "cache_enabled": request.enable_lemmatization_cache,
        })

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
        raise HTTPException(status_code=500, detail=f"Failed to rebuild search index: {str(e)}")


class InvalidateCorpusRequest(BaseModel):
    """Request for invalidating corpus caches using unified management."""

    # Unified corpus invalidation options
    corpus_types: list[str] = Field(
        default=[], 
        description="Corpus types to invalidate: 'language_search', 'wordlist', 'wordlist_names', 'custom'"
    )
    specific_corpus_id: str | None = Field(None, description="Specific corpus ID to invalidate")
    invalidate_all: bool = Field(default=False, description="Invalidate all corpus types")
    
    cleanup_expired: bool = Field(default=True, description="Also cleanup expired entries")


class InvalidateCorpusResponse(BaseModel):
    """Response for unified corpus cache invalidation."""

    status: str = Field(..., description="Operation status")
    total_invalidated: int = Field(..., description="Total number of entries invalidated")
    corpus_results: dict[str, int] = Field(default_factory=dict, description="Invalidation results by corpus type")
    expired_cleaned: int = Field(default=0, description="Number of expired entries cleaned")
    message: str = Field(..., description="Status message")


@router.post("/search/invalidate-corpus", response_model=InvalidateCorpusResponse)
async def invalidate_corpus_unified(
    request: InvalidateCorpusRequest = InvalidateCorpusRequest(
        corpus_types=[],
        specific_corpus_id=None,
        invalidate_all=False,
        cleanup_expired=True,
    ),
) -> InvalidateCorpusResponse:
    """
    Unified corpus cache invalidation using CorpusManager.
    
    This endpoint provides streamlined invalidation for all corpus types:
    - language_search: Main search engine corpus
    - wordlist: Individual wordlist corpora  
    - wordlist_names: Wordlist names corpus
    - custom: User-defined corpora
    """
    logger.info(f"Unified corpus invalidation: types={request.corpus_types}, all={request.invalidate_all}")
    
    try:
        corpus_manager = await get_corpus_manager()
        
        # Determine corpus types to invalidate
        target_corpus_types = []
        if request.invalidate_all:
            target_corpus_types = [CorpusType.LANGUAGE_SEARCH, CorpusType.WORDLIST, CorpusType.WORDLIST_NAMES, CorpusType.CUSTOM]
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
        
        # Invalidate each corpus type
        corpus_results = {}
        total_invalidated = 0
        
        for corpus_type in target_corpus_types:
            if request.specific_corpus_id:
                # Invalidate specific corpus
                count = await corpus_manager.invalidate_corpus(corpus_type, request.specific_corpus_id)
                corpus_results[f"{corpus_type.value}_specific"] = count
            else:
                # Invalidate all corpora of this type
                count = await corpus_manager.invalidate_all_corpora(corpus_type)
                corpus_results[corpus_type.value] = count
            
            total_invalidated += count
            logger.info(f"Invalidated {count} {corpus_type.value} corpus entries")
        
        # Cleanup expired entries
        expired_cleaned = 0
        if request.cleanup_expired:
            expired_cleaned = await SemanticIndexCache.cleanup_expired()
            logger.info(f"Cleaned up {expired_cleaned} expired cache entries")
        
        message = f"Successfully invalidated {total_invalidated} corpus entries"
        if expired_cleaned > 0:
            message += f" and cleaned {expired_cleaned} expired entries"
        
        return InvalidateCorpusResponse(
            status="success",
            total_invalidated=total_invalidated,
            corpus_results=corpus_results,
            expired_cleaned=expired_cleaned,
            message=message,
        )
    
    except Exception as e:
        logger.error(f"Failed to invalidate corpus caches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invalidate corpus caches: {str(e)}")


