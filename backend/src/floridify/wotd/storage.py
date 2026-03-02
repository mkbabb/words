"""WOTD Storage - Persistent storage for training pipeline.

L1 in-memory dict for fast reads + L2 disk persistence via GlobalCacheManager.
Data survives process restarts through L2 (DiskCache, 7d TTL for WOTD namespace).
"""

from __future__ import annotations

from typing import Any

from ..caching.core import get_global_cache
from ..caching.models import CacheNamespace
from ..utils.logging import get_logger
from .core import (
    SemanticID,
    TrainingResults,
    WOTDCorpus,
)

logger = get_logger(__name__)

# L2 cache keys
_L2_CORPORA_INDEX = "wotd:corpora_index"
_L2_TRAINING_RESULTS = "wotd:training_results"
_L2_SEMANTIC_IDS = "wotd:semantic_ids"

_NS = CacheNamespace.WOTD

# Global WOTD storage instance
_wotd_storage: WOTDStorage | None = None


class WOTDStorage:
    """WOTD-specific storage with L1 in-memory + L2 disk persistence."""

    def __init__(self) -> None:
        self._corpora: dict[str, WOTDCorpus] = {}
        self._training_results: list[TrainingResults] = []
        self._semantic_ids: dict[str, SemanticID] = {}
        self._embeddings: dict[str, dict[str, Any]] = {}
        self._loaded_from_l2 = False

    async def _ensure_loaded(self) -> None:
        """Load data from L2 on first access. Idempotent."""
        if self._loaded_from_l2:
            return
        self._loaded_from_l2 = True

        cache = await get_global_cache()

        # Corpora
        corpora_data = await cache.get(namespace=_NS, key=_L2_CORPORA_INDEX)
        if isinstance(corpora_data, dict):
            for corpus_id, corpus_dict in corpora_data.items():
                self._corpora[corpus_id] = WOTDCorpus.model_validate(corpus_dict)
            logger.info(f"Loaded {len(self._corpora)} corpora from L2")

        # Training results
        training_data = await cache.get(namespace=_NS, key=_L2_TRAINING_RESULTS)
        if isinstance(training_data, list):
            self._training_results = [TrainingResults.model_validate(r) for r in training_data]
            logger.info(f"Loaded {len(self._training_results)} training results from L2")

        # Semantic IDs
        semantic_data = await cache.get(namespace=_NS, key=_L2_SEMANTIC_IDS)
        if isinstance(semantic_data, dict):
            self._semantic_ids = {
                k: tuple(v)
                for k, v in semantic_data.items()
                if isinstance(v, (list, tuple)) and len(v) == 4
            }
            logger.info(f"Loaded {len(self._semantic_ids)} semantic IDs from L2")

    async def _persist_corpora(self) -> None:
        cache = await get_global_cache()
        serialized = {cid: corpus.model_dump(mode="json") for cid, corpus in self._corpora.items()}
        await cache.set(namespace=_NS, key=_L2_CORPORA_INDEX, value=serialized)

    async def _persist_training_results(self) -> None:
        cache = await get_global_cache()
        serialized = [r.model_dump(mode="json") for r in self._training_results]
        await cache.set(namespace=_NS, key=_L2_TRAINING_RESULTS, value=serialized)

    async def _persist_semantic_ids(self) -> None:
        cache = await get_global_cache()
        serialized = {k: list(v) for k, v in self._semantic_ids.items()}
        await cache.set(namespace=_NS, key=_L2_SEMANTIC_IDS, value=serialized)

    async def save_corpus(self, corpus: WOTDCorpus) -> None:
        """Save a corpus to L1 + L2."""
        await self._ensure_loaded()
        self._corpora[corpus.id] = corpus
        await self._persist_corpora()
        logger.info(f"Saved corpus {corpus.id} with {len(corpus.words)} words")

    async def save_multiple_corpora(self, corpora: list[WOTDCorpus]) -> None:
        """Save multiple corpora to L1 + L2."""
        await self._ensure_loaded()
        for corpus in corpora:
            self._corpora[corpus.id] = corpus
        await self._persist_corpora()
        logger.info(f"Saved {len(corpora)} corpora to storage")

    async def get_corpus(self, corpus_id: str) -> WOTDCorpus | None:
        """Get a corpus by ID."""
        await self._ensure_loaded()
        return self._corpora.get(corpus_id)

    async def load_corpora_dict(self) -> dict[str, WOTDCorpus]:
        """Load all corpora as a dictionary."""
        await self._ensure_loaded()
        return self._corpora.copy()

    async def list_corpora(self, limit: int = 50) -> list[WOTDCorpus]:
        """List corpora with optional limit."""
        await self._ensure_loaded()
        corpora = list(self._corpora.values())
        return corpora[:limit]

    async def save_training_results(self, results: TrainingResults) -> None:
        """Save training results to L1 + L2."""
        await self._ensure_loaded()
        self._training_results.append(results)
        await self._persist_training_results()
        logger.info("Saved training results to storage")

    async def get_latest_training_results(self) -> TrainingResults | None:
        """Get the most recent training results."""
        await self._ensure_loaded()
        if self._training_results:
            return self._training_results[-1]
        return None

    async def save_semantic_ids(self, semantic_ids: dict[str, SemanticID]) -> None:
        """Save semantic IDs to L1 + L2."""
        await self._ensure_loaded()
        self._semantic_ids.update(semantic_ids)
        await self._persist_semantic_ids()
        logger.info(f"Saved {len(semantic_ids)} semantic IDs to storage")

    async def get_semantic_ids(self) -> dict[str, SemanticID]:
        """Get semantic IDs."""
        await self._ensure_loaded()
        return self._semantic_ids.copy()

    async def get_cache_stats(self) -> dict[str, Any] | None:
        """Get basic storage statistics."""
        await self._ensure_loaded()
        return {
            "status": "connected",
            "storage_type": "l1_memory_l2_disk",
            "corpus_count": len(self._corpora),
            "training_results_count": len(self._training_results),
            "semantic_ids_count": len(self._semantic_ids),
            "embeddings_count": len(self._embeddings),
        }

    async def get_cached_embeddings(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached embeddings from L1, then L2."""
        cached = self._embeddings.get(cache_key)
        if cached is not None:
            return cached
        # L2 fallback
        cache = await get_global_cache()
        l2_cached = await cache.get(namespace=_NS, key=f"wotd:embeddings:{cache_key}")
        if isinstance(l2_cached, dict):
            self._embeddings[cache_key] = l2_cached
            return l2_cached
        return None

    async def cache_embeddings(self, cache_key: str, embeddings: dict[str, Any]) -> None:
        """Cache embeddings to L1 + L2."""
        self._embeddings[cache_key] = embeddings
        cache = await get_global_cache()
        await cache.set(
            namespace=_NS,
            key=f"wotd:embeddings:{cache_key}",
            value=embeddings,
        )
        logger.info(f"Cached embeddings with key: {cache_key}")


async def get_wotd_storage() -> WOTDStorage:
    """Get the global WOTD storage instance."""
    global _wotd_storage

    if _wotd_storage is None:
        _wotd_storage = WOTDStorage()

    return _wotd_storage
