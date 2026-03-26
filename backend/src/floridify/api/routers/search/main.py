"""Main search endpoints for word discovery."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ....caching.models import VersionConfig
from ....core.search_pipeline import get_search_engine_manager
from ....corpus.manager import get_tree_corpus_manager
from ....models.parameters import SearchParams
from ....models.responses import SearchResponse
from ....search.constants import DEFAULT_MIN_SCORE, SearchMethod, SearchMode
from ....search.engine import Search
from ....search.index import SearchIndex
from ....utils.logging import get_logger
from ....utils.sanitization import sanitize_mongodb_input

logger = get_logger(__name__)
router = APIRouter()


def _validate_search_query(query: str) -> str:
    """Validate and sanitize a search query string."""
    if not query or len(query.strip()) < 1:
        raise HTTPException(status_code=422, detail="Search query cannot be empty")
    if len(query) > 200:
        raise HTTPException(status_code=422, detail="Search query too long (max 200 characters)")
    return sanitize_mongodb_input(query)


def parse_search_params(
    languages: list[str] = Query(default=["en"], description="Language codes"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    min_score: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum score"),
    mode: str = Query(default="smart", description="Search mode: smart, exact, fuzzy, semantic"),
    force_rebuild: bool = Query(default=False, description="Force rebuild indices"),
    corpus_id: str | None = Query(default=None, description="Specific corpus ID"),
    corpus_name: str | None = Query(default=None, description="Specific corpus name"),
    semantic: bool = Query(
        default=True, description="Enable semantic search (disable to avoid model load)"
    ),
) -> SearchParams:
    """Parse and validate search parameters using shared model."""
    # Use the shared model's validators
    return SearchParams(
        languages=languages,  # validators handle conversion
        max_results=max_results,
        min_score=min_score,
        mode=mode,  # validators handle conversion
        force_rebuild=force_rebuild,
        corpus_id=corpus_id,
        corpus_name=corpus_name,
        semantic=semantic,
    )


async def _cached_search(query: str, params: SearchParams) -> SearchResponse:
    """Cached search implementation."""
    # Support comma-separated modes (e.g., "exact,fuzzy")
    mode_parts = [m.strip() for m in params.mode.split(",") if m.strip()]

    if len(mode_parts) > 1:
        # Multi-mode: run each mode and union results
        all_results = []
        seen_words: set[str] = set()
        for mode_str in mode_parts:
            try:
                sub_params = params.model_copy(update={"mode": mode_str})
                sub_response = await _cached_search(query, sub_params)
                for result in sub_response.results:
                    key = result.word.lower()
                    if key not in seen_words:
                        seen_words.add(key)
                        all_results.append(result)
            except Exception as e:
                logger.warning(f"Multi-mode search failed for mode '{mode_str}': {e}")

        # Sort by score with small method bonus for tiebreaking
        method_bonus = {
            SearchMethod.EXACT: 0.03,
            SearchMethod.PREFIX: 0.02,
            SearchMethod.SUBSTRING: 0.015,
            SearchMethod.SEMANTIC: 0.01,
            SearchMethod.FUZZY: 0.0,
        }
        all_results.sort(
            key=lambda r: r.score + method_bonus.get(r.method, 0.0),
            reverse=True,
        )
        all_results = all_results[: params.max_results]

        return SearchResponse(
            query=query,
            results=all_results,
            total_found=len(all_results),
            languages=params.languages,
            mode=params.mode,
            metadata={"modes": mode_parts},
        )

    # Convert string mode to enum
    mode_enum = SearchMode(params.mode)

    try:
        # CRITICAL FIX: Check if searching specific corpus by ID or name
        if params.corpus_id or params.corpus_name:
            # Search within specific corpus
            logger.info(
                f"Searching for '{query}' in corpus_id={params.corpus_id} corpus_name={params.corpus_name} (mode={mode_enum.value})"
            )

            corpus_manager = get_tree_corpus_manager()

            # Get the corpus by ID or name
            corpus = await corpus_manager.get_corpus(
                corpus_id=params.corpus_id,
                corpus_name=params.corpus_name,
                config=VersionConfig(use_cache=True),
            )

            if not corpus:
                logger.warning(
                    f"Corpus not found: id={params.corpus_id}, name={params.corpus_name}"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"Corpus not found: id={params.corpus_id}, name={params.corpus_name}",
                )

            # Per-corpus semantic policy (child-to-parent effective OR) + global engine toggle.
            global_semantic_enabled = get_search_engine_manager()._semantic
            corpus_semantic_enabled = corpus.semantic_enabled_effective

            if mode_enum == SearchMode.SEMANTIC and not corpus_semantic_enabled:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Semantic search disabled by corpus policy for '{corpus.corpus_name}'. "
                        "Enable it via PATCH /api/v1/corpus/{corpus_id}/semantic."
                    ),
                )
            if mode_enum == SearchMode.SEMANTIC and not global_semantic_enabled:
                raise HTTPException(
                    status_code=409,
                    detail="Semantic search disabled globally (SEMANTIC_SEARCH_ENABLED=false).",
                )

            use_semantic = mode_enum == SearchMode.SEMANTIC or (
                mode_enum == SearchMode.SMART
                and global_semantic_enabled
                and corpus_semantic_enabled
            )
            index = await SearchIndex.get_or_create(
                corpus=corpus,
                semantic=use_semantic,
                config=VersionConfig(use_cache=True),
            )

            # Create search engine from index
            search_engine = Search(index=index, corpus=corpus)
            await search_engine.initialize()

            # For per-corpus search, wait for semantic to be ready
            # (small corpora build quickly, and each request creates a new Search instance)
            if use_semantic:
                await search_engine.await_semantic_ready()

            # Perform search
            results = await search_engine.search_with_mode(
                query=query,
                mode=mode_enum,
                max_results=params.max_results,
                min_score=params.min_score,
            )

            # Set language from corpus in results
            for result in results:
                if not result.language:
                    result.language = corpus.language

            response_metadata = {
                "corpus_id": str(corpus.corpus_id),
                "corpus_name": corpus.corpus_name,
                "semantic_enabled_effective": corpus_semantic_enabled,
                "semantic_enabled_global": global_semantic_enabled,
            }
            if mode_enum == SearchMode.SMART and not use_semantic:
                response_metadata["semantic_disabled_reason"] = (
                    "corpus_policy" if not corpus_semantic_enabled else "global_toggle"
                )

            return SearchResponse(
                query=query,
                results=results,
                total_found=len(results),
                languages=[corpus.language] if corpus.language else params.languages,
                mode=params.mode,
                metadata=response_metadata,
            )
        else:
            # Original behavior: search by language
            logger.info(
                f"Searching for '{query}' in {[lang.value for lang in params.languages]} (mode={mode_enum.value})"
            )

            # Use shared SearchEngineManager engine so status + runtime stay in sync
            manager = get_search_engine_manager()
            language_search = await manager.get_engine(
                languages=params.languages,
                semantic=params.semantic,
            )

            # Perform search with specified mode
            results = await language_search.search_with_mode(
                query=query,
                mode=mode_enum,
                max_results=params.max_results,
                min_score=params.min_score,
            )

            # Results are already in SearchResult format
            response_items = results

            return SearchResponse(
                query=query,
                results=response_items,
                total_found=len(results),
                languages=params.languages,
                mode=params.mode,
                metadata={},
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
    q = _validate_search_query(q)
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
        raise HTTPException(status_code=500, detail="Internal error during search")


@router.get("/search/{query}", response_model=SearchResponse)
async def search_words_path(
    query: str,
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    """Search for words using path parameter."""
    query = _validate_search_query(query)
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
        raise HTTPException(status_code=500, detail="Internal error during search")


@router.get("/search/{query}/suggestions", response_model=SearchResponse)
async def get_search_suggestions(
    query: str,
    limit: int = Query(default=8, ge=1, le=20, description="Maximum suggestions"),
    params: SearchParams = Depends(parse_search_params),
) -> SearchResponse:
    """Get search suggestions for autocomplete (lower threshold)."""
    query = _validate_search_query(query)
    start_time = time.perf_counter()

    # Override parameters for suggestions
    suggestion_params = SearchParams(
        languages=params.languages,
        max_results=limit,
        min_score=DEFAULT_MIN_SCORE,
        mode=params.mode,
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
        raise HTTPException(status_code=500, detail="Internal error during suggestions")
