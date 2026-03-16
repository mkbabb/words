"""Search index rebuild endpoint."""

import time

from fastapi import APIRouter, HTTPException

from ....caching.core import CacheNamespace, get_global_cache
from ....core.search_pipeline import get_search_engine_manager
from ....corpus.crud import get_stats as get_corpus_stats
from ....corpus.manager import get_tree_corpus_manager
from ....corpus.models import CorpusType
from ....text import clear_lemma_cache, get_lemma_cache_stats
from ....utils.logging import get_logger
from ...core import AdminDep
from .models import RebuildIndexRequest, RebuildIndexResponse

logger = get_logger(__name__)
router = APIRouter()


@router.post("/search/rebuild", response_model=RebuildIndexResponse)
async def rebuild_search_index(
    _admin: AdminDep,
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
        corpus_manager = get_tree_corpus_manager()

        # Determine corpus types to rebuild
        target_corpus_types: list[CorpusType] = []
        if request.rebuild_all_corpora:
            target_corpus_types = [
                CorpusType.LANGUAGE,
                CorpusType.WORDLIST,
                CorpusType.WORDLIST_NAMES,
            ]
        else:
            corpus_type_map = {
                "language_search": CorpusType.LANGUAGE,
                "wordlist": CorpusType.WORDLIST,
                "wordlist_names": CorpusType.WORDLIST_NAMES,
                "custom": CorpusType.CUSTOM,
            }
            target_corpus_types = [
                corpus_type_map.get(ct.lower(), CorpusType.LANGUAGE) for ct in request.corpus_types
            ]

        # Always clear all caches during rebuild to ensure fresh data
        caches_cleared = {}

        # Clear vocabulary caches

        cache = await get_global_cache()
        await cache.clear_namespace(CacheNamespace.CORPUS)
        await cache.clear_namespace(CacheNamespace.SEARCH)
        await cache.clear_namespace(CacheNamespace.TRIE)
        caches_cleared["vocabulary_caches"] = 0

        # Clear semantic caches when requested or when force rebuilding
        semantic_cleared = 0
        logger.info(
            f"Semantic cache control: clear_semantic_cache={request.clear_semantic_cache}, "
            f"semantic_force_rebuild={request.semantic_force_rebuild}, "
            f"rebuild_semantic={request.rebuild_semantic}"
        )
        if request.clear_semantic_cache or request.semantic_force_rebuild:
            await cache.clear_namespace(CacheNamespace.SEMANTIC)
            semantic_cleared = 1
            logger.info("🔥 Cleared SEMANTIC cache namespace")
        else:
            logger.warning("❌ SEMANTIC cache NOT cleared - condition not met")
        caches_cleared["semantic_cleared"] = semantic_cleared

        # Clear corpus caches
        corpus_cleared = await corpus_manager.invalidate_all_corpora()
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
            if corpus_type == CorpusType.LANGUAGE:
                # Rebuild language search corpus via SearchEngineManager
                manager = get_search_engine_manager()
                await manager.reset()
                search_engine = await manager.get_engine(
                    languages=request.languages,
                    force_rebuild=True,
                    semantic=request.rebuild_semantic,
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
        corpus_manager_stats = await get_corpus_stats()

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
        raise HTTPException(status_code=500, detail="Failed to rebuild search index")
