"""Query and result caching for semantic search with LRU eviction and L2 persistence."""

from __future__ import annotations

import asyncio
import hashlib

import numpy as np

from ...caching.core import get_global_cache
from ...caching.models import CacheNamespace
from ...utils.logging import get_logger
from ..result import SearchResult

logger = get_logger(__name__)


class SemanticQueryCache:
    """Manages query embedding and search result caches with LRU eviction and L2 persistence.

    Provides two caches:
    - Query embedding cache: Maps query strings to their computed embeddings.
    - Result cache: Maps query strings to their final search results.

    Both caches support debounced flush to L2 (disk) for persistence across restarts.
    """

    def __init__(
        self,
        corpus_uuid: str,
        model_name: str,
        query_cache_size: int = 100,
        result_cache_size: int = 500,
    ):
        """Initialize query cache.

        Args:
            corpus_uuid: UUID of the corpus (used for L2 cache keys).
            model_name: Name of the sentence transformer model (used for L2 cache keys).
            query_cache_size: Max entries in the query embedding LRU cache.
            result_cache_size: Max entries in the result LRU cache.

        """
        self.corpus_uuid = corpus_uuid
        self.model_name = model_name

        # Query embedding cache (LRU)
        self.query_cache: dict[str, np.ndarray] = {}
        self.query_cache_size = query_cache_size
        self.query_cache_order: list[str] = []  # For LRU tracking

        # Result cache (LRU) - cache final search results
        self.result_cache: dict[str, list[SearchResult]] = {}
        self.result_cache_order: list[str] = []
        self.result_cache_size = result_cache_size

        # Debounced flush tasks for persisting caches to L2
        self._flush_task: asyncio.Task[None] | None = None
        self._result_flush_task: asyncio.Task[None] | None = None

    # --- Query embedding cache ---

    def get_cached_query_embedding(self, query: str) -> np.ndarray | None:
        """Get cached query embedding using LRU eviction.

        Args:
            query: Normalized query string

        Returns:
            Cached embedding if available, None otherwise

        """
        cache_key = hashlib.md5(query.encode()).hexdigest()

        if cache_key in self.query_cache:
            # Move to end of LRU order (most recently used)
            if cache_key in self.query_cache_order:
                self.query_cache_order.remove(cache_key)
            self.query_cache_order.append(cache_key)
            return self.query_cache[cache_key]

        return None

    def cache_query_embedding(self, query: str, embedding: np.ndarray) -> None:
        """Cache query embedding with LRU eviction and L2 persistence.

        Args:
            query: Normalized query string
            embedding: Query embedding to cache

        """
        cache_key = hashlib.md5(query.encode()).hexdigest()

        # LRU eviction if cache is full
        if len(self.query_cache) >= self.query_cache_size:
            if self.query_cache_order:
                oldest_key = self.query_cache_order.pop(0)
                self.query_cache.pop(oldest_key, None)

        # Add to cache
        self.query_cache[cache_key] = embedding
        self.query_cache_order.append(cache_key)

        # Schedule debounced flush to L2
        self._schedule_query_cache_flush()

    def _query_cache_l2_key(self) -> str:
        """L2 cache key for this index's query embedding cache."""
        return f"query_embed_cache:{self.corpus_uuid}:{self.model_name}"

    async def load_query_cache_from_l2(self) -> None:
        """Load persisted query embeddings from L2 cache on startup."""
        cache = await get_global_cache()
        cached = await cache.get(
            namespace=CacheNamespace.SEMANTIC,
            key=self._query_cache_l2_key(),
        )
        if not isinstance(cached, dict):
            return
        count = 0
        for key, emb_bytes in cached.items():
            if isinstance(emb_bytes, bytes):
                self.query_cache[key] = np.frombuffer(emb_bytes, dtype=np.float32).copy()
                self.query_cache_order.append(key)
                count += 1
        if count > 0:
            logger.debug(f"Loaded {count} cached query embeddings from L2")

    def _schedule_query_cache_flush(self) -> None:
        """Schedule a debounced (5s) flush of query cache to L2."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
        try:
            loop = asyncio.get_running_loop()
            self._flush_task = loop.create_task(self._debounced_flush())
        except RuntimeError:
            # By design: no event loop means flush is skipped (e.g., sync context)
            pass

    async def _debounced_flush(self) -> None:
        """Wait 5s then persist query cache to L2."""
        await asyncio.sleep(5.0)
        if not self.query_cache:
            return
        cache = await get_global_cache()
        serializable = {k: v.tobytes() for k, v in self.query_cache.items()}
        await cache.set(
            namespace=CacheNamespace.SEMANTIC,
            key=self._query_cache_l2_key(),
            value=serializable,
        )
        logger.debug(f"Flushed {len(serializable)} query embeddings to L2")

    # --- Result cache ---

    def _get_result_cache_key(self, query: str) -> str:
        """Generate cache key for search results (query-only for max reuse)."""
        return hashlib.md5(query.encode()).hexdigest()

    def get_cached_results(
        self, query: str, max_results: int, min_score: float
    ) -> list[SearchResult] | None:
        """Get cached search results using LRU eviction. Truncates from full cache."""
        cache_key = self._get_result_cache_key(query)

        if cache_key in self.result_cache:
            # Move to end of LRU order (most recently used)
            if cache_key in self.result_cache_order:
                self.result_cache_order.remove(cache_key)
            self.result_cache_order.append(cache_key)
            # Filter and truncate from cached full result set
            cached = self.result_cache[cache_key]
            return [r for r in cached if r.score >= min_score][:max_results]

        return None

    def cache_results(
        self, query: str, max_results: int, min_score: float, results: list[SearchResult]
    ) -> None:
        """Cache search results with LRU eviction. Stores full result set."""
        cache_key = self._get_result_cache_key(query)

        # LRU eviction if cache is full
        if len(self.result_cache) >= self.result_cache_size:
            if self.result_cache_order:
                oldest_key = self.result_cache_order.pop(0)
                self.result_cache.pop(oldest_key, None)

        # Add to cache
        self.result_cache[cache_key] = results
        self.result_cache_order.append(cache_key)

        # Schedule debounced flush to L2
        self._schedule_result_cache_flush()

    def _result_cache_l2_key(self) -> str:
        """L2 cache key for this index's result cache."""
        return f"result_cache:{self.corpus_uuid}:{self.model_name}"

    async def load_result_cache_from_l2(self) -> None:
        """Load persisted search results from L2 cache on startup."""
        cache = await get_global_cache()
        cached = await cache.get(
            namespace=CacheNamespace.SEMANTIC,
            key=self._result_cache_l2_key(),
        )
        if not isinstance(cached, dict):
            return
        count = 0
        for key, results_data in cached.items():
            if isinstance(results_data, list):
                self.result_cache[key] = [SearchResult.model_validate(r) for r in results_data]
                self.result_cache_order.append(key)
                count += 1
        if count > 0:
            logger.debug(f"Loaded {count} cached search results from L2")

    def _schedule_result_cache_flush(self) -> None:
        """Schedule a debounced (5s) flush of result cache to L2."""
        if self._result_flush_task and not self._result_flush_task.done():
            self._result_flush_task.cancel()
        try:
            loop = asyncio.get_running_loop()
            self._result_flush_task = loop.create_task(self._debounced_result_flush())
        except RuntimeError:
            # By design: no event loop means flush is skipped (e.g., sync context)
            pass

    async def _debounced_result_flush(self) -> None:
        """Wait 5s then persist result cache to L2."""
        await asyncio.sleep(5.0)
        if not self.result_cache:
            return
        cache = await get_global_cache()
        serializable = {
            k: [r.model_dump(mode="json") for r in results]
            for k, results in self.result_cache.items()
        }
        await cache.set(
            namespace=CacheNamespace.SEMANTIC,
            key=self._result_cache_l2_key(),
            value=serializable,
        )
        logger.debug(f"Flushed {len(serializable)} search result sets to L2")

    # --- Bulk operations ---

    def clear_result_cache(self) -> None:
        """Clear the result cache (e.g., after corpus update)."""
        self.result_cache.clear()
        self.result_cache_order.clear()
