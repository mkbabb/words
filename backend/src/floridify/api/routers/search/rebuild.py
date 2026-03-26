"""Search index rebuild endpoint."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from ....caching.core import CacheNamespace, get_global_cache
from ....caching.gridfs import gridfs_cleanup_stale
from ....caching.models import VersionConfig
from ....corpus.manager import get_tree_corpus_manager
from ....core.search_pipeline import get_search_engine_manager
from ....search.cache import reset_search_cache
from ....search.engine import Search
from ....search.index import SearchIndex
from ....utils.logging import get_logger
from ...core import AdminDep
from .models import RebuildIndexRequest, RebuildIndexResponse

logger = get_logger(__name__)
router = APIRouter()


async def _clear_corpus_caches(corpus_name: str, corpus_uuid: str | None) -> dict[str, int]:
    """Clear all cache tiers for a specific corpus."""
    cleared: dict[str, int] = {}
    cache = await get_global_cache()

    # Invalidate corpus in TreeCorpusManager
    manager = get_tree_corpus_manager()
    if await manager.invalidate_corpus(corpus_name):
        cleared["corpus"] = 1

    # Evict from Search instance cache
    reset_search_cache()
    cleared["search_instances"] = 1

    # Clear SEMANTIC namespace entries for this corpus
    await cache.clear_namespace(CacheNamespace.SEMANTIC)
    cleared["semantic_cache"] = 1

    # Clear SEARCH and TRIE namespaces
    await cache.clear_namespace(CacheNamespace.SEARCH)
    cleared["search_cache"] = 1
    await cache.clear_namespace(CacheNamespace.TRIE)
    cleared["trie_cache"] = 1

    return cleared


async def _get_semantic_info(search: Search) -> dict[str, Any]:
    """Extract semantic index metadata for f32 validation."""
    info: dict[str, Any] = {}
    if search.semantic_search and search.semantic_search.index:
        si = search.semantic_search.index
        info["num_embeddings"] = si.num_embeddings
        info["dimension"] = si.embedding_dimension
        info["index_type"] = si.index_type
        info["model_name"] = si.model_name
        info["build_time_seconds"] = si.build_time_seconds

        # dtype from actual embeddings array
        if search.semantic_search.sentence_embeddings is not None:
            info["dtype"] = str(search.semantic_search.sentence_embeddings.dtype)
    return info


async def _rebuild_corpus(
    corpus_name: str | None,
    corpus_uuid: str | None,
    components: list[str],
    clear_caches: bool,
    clean_gridfs: bool,
) -> RebuildIndexResponse:
    """Rebuild search index for a specific corpus."""
    start_time = time.perf_counter()

    # Resolve corpus
    manager = get_tree_corpus_manager()
    corpus = await manager.get_corpus(
        corpus_name=corpus_name,
        corpus_uuid=corpus_uuid,
        config=VersionConfig(use_cache=False),
    )
    if not corpus:
        raise HTTPException(
            status_code=404,
            detail=f"Corpus not found: {corpus_name or corpus_uuid}",
        )

    resolved_name = corpus.corpus_name
    resolved_uuid = corpus.corpus_uuid

    # Clear caches
    caches_cleared: dict[str, int] = {}
    if clear_caches:
        caches_cleared = await _clear_corpus_caches(resolved_name, resolved_uuid)

    components_rebuilt: list[str] = []
    force_config = VersionConfig(force_rebuild=True, use_cache=False)

    if "all" in components:
        # Full cascade delete + rebuild
        existing = await SearchIndex.get(corpus_uuid=resolved_uuid)
        if existing:
            await existing.delete()

        index = await SearchIndex.get_or_create(
            corpus=corpus, semantic=True, config=force_config
        )
        search = Search(index=index, corpus=corpus)
        await search.initialize()
        await search.await_semantic_ready()
        components_rebuilt = ["trie", "semantic"]

    elif "semantic" in components:
        # Rebuild semantic only
        from ....search.semantic.search import SemanticSearch
        from ....search.semantic.index import SemanticIndex as SemanticIndexModel

        # Delete existing semantic index
        existing_search = await SearchIndex.get(corpus_uuid=resolved_uuid)
        if existing_search and existing_search.semantic_index_id:
            try:
                sem_idx = await SemanticIndexModel.get(
                    corpus_uuid=resolved_uuid,
                    model_name=existing_search.semantic_model,
                )
                if sem_idx:
                    await sem_idx.delete()
            except Exception as e:
                logger.warning(f"Failed to delete old semantic index: {e}")
            existing_search.semantic_index_id = None
            await existing_search.save()

        # Rebuild via Search (which handles semantic init)
        index = await SearchIndex.get_or_create(
            corpus=corpus, semantic=True, config=force_config
        )
        search = Search(index=index, corpus=corpus)
        await search.initialize()
        await search.await_semantic_ready()
        components_rebuilt = ["semantic"]

    elif "trie" in components:
        # Rebuild trie only
        from ....search.trie import TrieSearch

        trie_search = await TrieSearch.from_corpus(corpus)
        existing = await SearchIndex.get(corpus_uuid=resolved_uuid)
        if existing and trie_search and trie_search.index:
            existing.trie_index_id = trie_search.index.index_id
            await existing.save()

        # Create minimal search for stats
        index = existing or await SearchIndex.get_or_create(corpus=corpus, semantic=False)
        search = Search(index=index, corpus=corpus)
        components_rebuilt = ["trie"]

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid components: {components}. Use 'all', 'trie', or 'semantic'.",
        )

    # GridFS cleanup
    gridfs_cleaned = 0
    if clean_gridfs:
        result = await gridfs_cleanup_stale(corpus_uuid=resolved_uuid, dry_run=False)
        gridfs_cleaned = result["deleted"]

    # Collect semantic info for f32 validation
    semantic_info = await _get_semantic_info(search)

    elapsed = time.perf_counter() - start_time

    return RebuildIndexResponse(
        status="success",
        message=f"Rebuilt {', '.join(components_rebuilt)} for '{resolved_name}' in {elapsed:.2f}s",
        corpus_name=resolved_name,
        corpus_uuid=resolved_uuid,
        components_rebuilt=components_rebuilt,
        vocabulary_size=len(corpus.vocabulary),
        caches_cleared=caches_cleared,
        gridfs_cleaned=gridfs_cleaned,
        total_time_seconds=elapsed,
        semantic_info=semantic_info,
    )


async def _rebuild_language(
    languages: list,
    components: list[str],
    clear_caches: bool,
    clean_gridfs: bool,
) -> RebuildIndexResponse:
    """Backward-compatible: rebuild language-level search engine."""
    start_time = time.perf_counter()

    # Clear caches
    caches_cleared: dict[str, int] = {}
    if clear_caches:
        cache = await get_global_cache()
        await cache.clear_namespace(CacheNamespace.CORPUS)
        await cache.clear_namespace(CacheNamespace.SEARCH)
        await cache.clear_namespace(CacheNamespace.TRIE)
        await cache.clear_namespace(CacheNamespace.SEMANTIC)
        reset_search_cache()
        corpus_manager = get_tree_corpus_manager()
        corpus_cleared = await corpus_manager.invalidate_all_corpora()
        caches_cleared = {
            "corpus": corpus_cleared,
            "search_instances": 1,
            "semantic_cache": 1,
            "search_cache": 1,
            "trie_cache": 1,
        }

    # Reset and rebuild via SearchEngineManager
    sem = get_search_engine_manager()
    await sem.reset()
    rebuild_semantic = "semantic" in components or "all" in components
    engine = await sem.get_engine(languages=languages, force_rebuild=True, semantic=rebuild_semantic)

    stats = engine.get_stats()
    corpus_name = stats.get("corpus_name", f"language_{'_'.join(l.value for l in languages)}")

    components_rebuilt = ["trie"]
    if rebuild_semantic:
        components_rebuilt.append("semantic")

    # GridFS cleanup
    gridfs_cleaned = 0
    if clean_gridfs:
        result = await gridfs_cleanup_stale(dry_run=False)
        gridfs_cleaned = result["deleted"]

    elapsed = time.perf_counter() - start_time

    return RebuildIndexResponse(
        status="success",
        message=f"Rebuilt language search for {[l.value for l in languages]} in {elapsed:.2f}s",
        corpus_name=corpus_name,
        components_rebuilt=components_rebuilt,
        vocabulary_size=stats.get("vocabulary_size", 0),
        caches_cleared=caches_cleared,
        gridfs_cleaned=gridfs_cleaned,
        total_time_seconds=elapsed,
    )


@router.post("/search/rebuild", response_model=RebuildIndexResponse)
async def rebuild_search_index(
    _admin: AdminDep,
    request: RebuildIndexRequest = RebuildIndexRequest(),
) -> RebuildIndexResponse:
    """Rebuild search index — per-corpus or language-level.

    Per-corpus mode (corpus_name or corpus_uuid specified):
        Targets a specific corpus. Supports component selection (trie, semantic, all).
        Returns semantic_info with dtype for f32 validation.

    Language mode (no corpus specified):
        Backward-compatible. Resets SearchEngineManager and rebuilds language search.
    """
    logger.info(
        f"Rebuilding search index: corpus_name={request.corpus_name}, "
        f"corpus_uuid={request.corpus_uuid}, components={request.components}"
    )

    try:
        if request.corpus_name or request.corpus_uuid:
            return await _rebuild_corpus(
                corpus_name=request.corpus_name,
                corpus_uuid=request.corpus_uuid,
                components=request.components,
                clear_caches=request.clear_caches,
                clean_gridfs=request.clean_gridfs,
            )
        else:
            return await _rebuild_language(
                languages=request.languages,
                components=request.components,
                clear_caches=request.clear_caches,
                clean_gridfs=request.clean_gridfs,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rebuild search index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rebuild search index: {e!s}")
