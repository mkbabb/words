"""Minimal WOTD Storage - for testing fixes without circular imports."""

from __future__ import annotations

from typing import Any


# Minimal storage implementation without complex dependencies
class WOTDStorage:
    """Minimal WOTD storage for testing imports."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def save_corpus(self, corpus: Any) -> None:
        """Save corpus placeholder."""
        pass

    async def save_multiple_corpora(self, corpora: Any) -> None:
        """Save multiple corpora placeholder."""
        pass

    async def get_corpus(self, corpus_id: str) -> Any | None:
        """Get corpus placeholder."""
        return None

    async def load_corpora_dict(self) -> dict[str, Any]:
        """Load corpora dict placeholder."""
        return {}

    async def list_corpora(self, limit: int = 50) -> list[Any]:
        """List corpora placeholder."""
        return []

    async def save_training_results(self, results: Any) -> None:
        """Save training results placeholder."""
        pass

    async def get_latest_training_results(self) -> Any | None:
        """Get latest training results placeholder."""
        return None

    async def save_semantic_ids(self, semantic_ids: dict[str, Any]) -> None:
        """Save semantic IDs placeholder."""
        pass

    async def get_semantic_ids(self) -> dict[str, Any]:
        """Get semantic IDs placeholder."""
        return {}

    async def get_cache_stats(self) -> dict[str, Any] | None:
        """Get cache stats placeholder."""
        return {"status": "test_mode"}

    async def get_cached_embeddings(self, cache_key: str) -> dict[str, Any] | None:
        """Get cached embeddings placeholder."""
        return None

    async def cache_embeddings(self, cache_key: str, embeddings: dict[str, Any]) -> None:
        """Cache embeddings placeholder."""
        pass


_storage: WOTDStorage | None = None


async def get_wotd_storage() -> WOTDStorage:
    """Get minimal storage instance."""
    global _storage
    if _storage is None:
        _storage = WOTDStorage()
    return _storage
