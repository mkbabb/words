"""WOTD Storage - Simplified storage interface for training pipeline."""

from __future__ import annotations

from typing import Any

from ..utils.logging import get_logger
from .core import (
    SemanticID,
    TrainingResults,
    WOTDCorpus,
)

logger = get_logger(__name__)

# Global WOTD storage instance
_wotd_storage: WOTDStorage | None = None


class WOTDStorage:
    """WOTD-specific storage operations - simplified implementation."""

    def __init__(self) -> None:
        """Initialize WOTD storage."""
        self._data: dict[str, Any] = {
            "corpora": {},
            "training_results": [],
            "semantic_ids": {},
            "embeddings": {},
        }

    async def save_corpus(self, corpus: WOTDCorpus) -> None:
        """Save a corpus (in-memory for now)."""
        self._data["corpora"][corpus.id] = corpus
        logger.info(f"Saved corpus {corpus.id} with {len(corpus.words)} words")

    async def save_multiple_corpora(self, corpora: list[WOTDCorpus]) -> None:
        """Save multiple corpora efficiently (in-memory for now)."""
        for corpus in corpora:
            self._data["corpora"][corpus.id] = corpus
        logger.info(f"Saved {len(corpora)} corpora to storage")

    async def get_corpus(self, corpus_id: str) -> WOTDCorpus | None:
        """Get a corpus by ID."""
        return self._data["corpora"].get(corpus_id)

    async def load_corpora_dict(self) -> dict[str, WOTDCorpus]:
        """Load all corpora as a dictionary."""
        return self._data["corpora"].copy()

    async def list_corpora(self, limit: int = 50) -> list[WOTDCorpus]:
        """List corpora with optional limit."""
        corpora = list(self._data["corpora"].values())
        return corpora[:limit]

    async def save_training_results(self, results: TrainingResults) -> None:
        """Save training results."""
        self._data["training_results"].append(results)
        logger.info("Saved training results to storage")

    async def get_latest_training_results(self) -> TrainingResults | None:
        """Get the most recent training results."""
        if self._data["training_results"]:
            return self._data["training_results"][-1]
        return None

    async def save_semantic_ids(self, semantic_ids: dict[str, SemanticID]) -> None:
        """Save semantic IDs."""
        self._data["semantic_ids"].update(semantic_ids)
        logger.info(f"Saved {len(semantic_ids)} semantic IDs to storage")

    async def get_semantic_ids(self) -> dict[str, SemanticID]:
        """Get semantic IDs."""
        return self._data["semantic_ids"].copy()

    async def get_cache_stats(self) -> dict[str, Any] | None:
        """Get basic storage statistics."""
        return {
            "status": "connected",
            "storage_type": "in_memory",
            "corpus_count": len(self._data["corpora"]),
            "training_results_count": len(self._data["training_results"]),
            "semantic_ids_count": len(self._data["semantic_ids"]),
            "embeddings_count": len(self._data["embeddings"]),
        }

    async def get_cached_embeddings(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached embeddings."""
        return self._data["embeddings"].get(cache_key)

    async def cache_embeddings(self, cache_key: str, embeddings: dict[str, Any]) -> None:
        """Cache embeddings."""
        self._data["embeddings"][cache_key] = embeddings
        logger.info(f"Cached embeddings with key: {cache_key}")


async def get_wotd_storage() -> WOTDStorage:
    """Get the global WOTD storage instance."""
    global _wotd_storage

    if _wotd_storage is None:
        _wotd_storage = WOTDStorage()

    return _wotd_storage
