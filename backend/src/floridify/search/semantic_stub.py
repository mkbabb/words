"""
TEMPORARY STUB: Semantic search implementation disabled for lightweight deployment.
This stub provides the interface without the heavy ML dependencies.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


class SemanticSearch:
    """
    TEMPORARY STUB - Semantic search disabled for lightweight deployment.
    Returns empty results for all queries.
    """

    def __init__(
        self,
        embedding_levels: list[str] | None = None,
        embedding_dimension: int = 384,
        cache_dir: str = "data/embeddings",
        force_rebuild: bool = False,
    ):
        """Initialize stub semantic search."""
        self.embedding_levels = embedding_levels or ["word"]
        self.embedding_dimension = embedding_dimension
        self.cache_dir = cache_dir
        self.force_rebuild = force_rebuild
        self.vocabulary: list[str] = []
        self.word_to_id: dict[str, int] = {}
        logger.warning("SemanticSearch initialized in STUB mode - functionality disabled")

    async def initialize(self, vocabulary: list[str]) -> None:
        """Initialize semantic search with vocabulary - STUB version."""
        logger.warning(f"SemanticSearch.initialize() called with {len(vocabulary)} words - STUB mode, no action taken")
        self.vocabulary = vocabulary
        self.word_to_id = {word: i for i, word in enumerate(vocabulary)}

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.5,
        embedding_levels: list[str] | None = None,
        **kwargs: Any,
    ) -> list[tuple[str, float]]:
        """
        Search for semantically similar words - STUB version.
        
        Returns empty list since semantic search is disabled.
        """
        logger.warning(f"SemanticSearch.search() called for '{query}' - returning empty results (STUB mode)")
        return []

    async def get_embeddings(
        self,
        words: list[str],
        embedding_level: str = "word",
    ) -> dict[str, list[float]]:
        """Get embeddings for words - STUB version."""
        logger.warning(f"SemanticSearch.get_embeddings() called for {len(words)} words - returning empty results (STUB mode)")
        return {}

    async def similarity(
        self,
        word1: str,
        word2: str,
        embedding_level: str = "word",
    ) -> float:
        """Calculate similarity between two words - STUB version."""
        logger.warning(f"SemanticSearch.similarity() called for '{word1}' and '{word2}' - returning 0.0 (STUB mode)")
        return 0.0