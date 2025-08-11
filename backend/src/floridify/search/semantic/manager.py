"""
Semantic Search Manager - Centralized management of semantic search instances.

Provides singleton pattern for managing semantic search instances across the application
with proper caching, initialization, and lifecycle management.
"""

from __future__ import annotations

import time
from typing import Any

from ...caching.core import CacheNamespace, CacheTTL
from ...caching.unified import get_unified
from ...utils.logging import get_logger
from ..corpus.core import Corpus
from ..models import CorpusMetadata, SemanticMetadata
from ..utils import get_vocabulary_hash
from .constants import DEFAULT_SENTENCE_MODEL, SemanticModel
from .core import SemanticSearch

logger = get_logger(__name__)


class SemanticSearchManager:
    """
    Centralized manager for semantic search instances.

    Handles creation, caching, and lifecycle of semantic search instances
    to avoid duplication and ensure efficient resource usage.
    """

    def __init__(self) -> None:
        """Initialize semantic search manager."""
        # Cache managed by unified cache - no separate TTL cache needed
        pass

    async def get_semantic_search(
        self,
        corpus_name: str,
        vocab_hash: str | None = None,
        vocabulary: list[str] | None = None,
        model_name: SemanticModel | None = None,
    ) -> SemanticSearch | None:
        """
        Get existing semantic search instance from cache.

        Supports both BGE-M3 (multilingual) and MiniLM (English) models.
        Cache keys include model name to isolate different embeddings.

        Args:
            corpus_name: Unique name for the corpus
            vocab_hash: Pre-computed vocabulary hash (preferred)
            vocabulary: Vocabulary to hash if vocab_hash not provided
            model_name: Embedding model (BGE-M3 or MiniLM)

        Returns:
            Cached SemanticSearch instance or None if not found
        """
        # Use default model name if not provided
        if model_name is None:
            model_name = DEFAULT_SENTENCE_MODEL

        if vocab_hash is None:
            if vocabulary is None:
                raise ValueError("Must provide either vocab_hash or vocabulary")
            vocab_hash = get_vocabulary_hash(vocabulary, model_name)

        cache = await get_unified()
        cache_key = f"semantic:{corpus_name}:{model_name.replace('/', '_')}:{vocab_hash}"
        cached_data: dict[str, Any] | None = await cache.get(CacheNamespace.SEMANTIC, cache_key)
        if cached_data:
            try:
                # Ensure cached_data is a dictionary, not a SemanticSearch object
                if isinstance(cached_data, dict):
                    semantic_search = SemanticSearch.model_load(cached_data)
                    logger.debug(f"Cache hit for semantic search '{corpus_name}'")
                    return semantic_search
                else:
                    logger.warning(
                        f"Invalid cached data type for semantic search '{corpus_name}': {type(cached_data)}. Invalidating cache."
                    )
                    await cache.delete(CacheNamespace.SEMANTIC, cache_key)
            except Exception as e:
                logger.warning(
                    f"Failed to load semantic search from cache for '{corpus_name}': {e}. Invalidating cache."
                )
                await cache.delete(CacheNamespace.SEMANTIC, cache_key)

        logger.error(
            f"🚨 SEMANTIC CACHE MISS: corpus='{corpus_name}', vocab_hash='{vocab_hash[:8]}...', cache_key='{cache_key}'"
        )
        return None

    async def create_semantic_search(
        self,
        corpus: Corpus,
        force_rebuild: bool = False,
        model_name: SemanticModel | None = None,
    ) -> SemanticSearch:
        """
        Create new semantic search instance with caching.

        Supports both BGE-M3 (1024D multilingual) and MiniLM (384D English).
        Model choice affects memory usage and performance.

        Args:
            corpus: Corpus instance containing vocabulary data
            force_rebuild: Force rebuild even if cached
            model_name: Embedding model (defaults to BGE-M3)

        Returns:
            Initialized SemanticSearch instance
        """
        # Use default model name if not provided
        if model_name is None:
            model_name = DEFAULT_SENTENCE_MODEL

        corpus_name = corpus.corpus_name
        logger.info(
            f"Creating semantic search for corpus '{corpus_name}' with {len(corpus.lemmatized_vocabulary)} lemmatized items using {model_name}"
        )
        start_time = time.perf_counter()
        vocab_hash = corpus.vocabulary_hash
        cache_key = f"semantic:{corpus_name}:{model_name.replace('/', '_')}:{vocab_hash}"

        semantic_search = SemanticSearch(
            corpus=corpus,
            model_name=model_name,
            force_rebuild=force_rebuild,
        )

        # Initialize with corpus instance directly
        await semantic_search.initialize()

        # Cache in unified cache (L1 + L2)
        cache = await get_unified()
        await cache.set(
            namespace=CacheNamespace.SEMANTIC,
            key=cache_key,
            value=semantic_search.model_dump(),
            ttl=CacheTTL.SEMANTIC,
            tags=[
                f"{CacheNamespace.CORPUS}:{corpus_name}",
                f"{CacheNamespace.SEMANTIC}:{corpus_name}",
            ],
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Semantic search created for '{corpus_name}' in {elapsed_ms}ms")

        return semantic_search

    async def invalidate_semantic_search(self, corpus_name: str) -> bool:
        """
        Invalidate and remove semantic search instance ONLY (not corpus).
        Updates corpus to remove semantic reference.

        Args:
            corpus_name: Corpus name to invalidate semantic search for

        Returns:
            True if instance was removed, False if not found
        """
        # Invalidate ONLY semantic data in unified cache
        cache = await get_unified()
        cache_removed = await cache.invalidate_by_tags([f"{CacheNamespace.SEMANTIC}:{corpus_name}"])

        # Update CorpusMetadata to remove semantic reference
        corpus_updated = 0
        async for corpus_metadata in CorpusMetadata.find({"corpus_name": corpus_name}):
            corpus_metadata.semantic_data_id = None
            await corpus_metadata.save()
            corpus_updated += 1

        # Cascading deletion: Remove SemanticMetadata from MongoDB
        deleted_count = 0
        async for semantic_metadata in SemanticMetadata.find({"corpus_name": corpus_name}):
            await semantic_metadata.delete()
            deleted_count += 1

        removed = cache_removed > 0 or deleted_count > 0
        if removed:
            logger.info(
                f"Invalidated semantic search for '{corpus_name}' (cache: {cache_removed}, db: {deleted_count}, corpus_updated: {corpus_updated})"
            )

        return removed

    async def invalidate_all(self) -> int:
        """
        Invalidate all semantic search instances with full cleanup.

        Returns:
            Number of instances invalidated
        """
        # Clear semantic data from unified cache
        cache = await get_unified()
        cache_removed = await cache.invalidate_namespace(CacheNamespace.SEMANTIC)

        # Cascading deletion: Remove all SemanticMetadata from MongoDB
        deleted_result = await SemanticMetadata.delete_all()
        deleted_count = deleted_result.deleted_count if deleted_result else 0

        total_count = cache_removed + deleted_count
        logger.info(
            f"Invalidated all semantic search instances (cache: {cache_removed}, db: {deleted_count})"
        )

        return total_count

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about managed semantic search instances."""
        cache = await get_unified()
        cache_stats = await cache.get_stats(CacheNamespace.SEMANTIC)

        return {
            "architecture": "Unified Cache (Memory TTL + Filesystem)",
            "cache_stats": cache_stats,
            "description": "Semantic search data cached in unified L1+L2 cache",
        }


# Global singleton instance
_semantic_search_manager: SemanticSearchManager | None = None


def get_semantic_search_manager() -> SemanticSearchManager:
    """Get or create global semantic search manager singleton."""
    global _semantic_search_manager
    if _semantic_search_manager is None:
        _semantic_search_manager = SemanticSearchManager()
        logger.info("Initialized semantic search manager")
    return _semantic_search_manager


async def shutdown_semantic_search_manager() -> None:
    """Shutdown global semantic search manager."""
    global _semantic_search_manager
    if _semantic_search_manager:
        await _semantic_search_manager.invalidate_all()
        _semantic_search_manager = None
        logger.info("Shutdown semantic search manager")
