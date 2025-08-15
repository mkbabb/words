"""WOTD storage using unified cache and MongoDB - performance focused."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from ..caching.unified import get_unified
from ..storage.mongodb import get_database, get_storage
from .core import (
    CacheKeys,
    Collections,
    CorpusDict,
    SemanticIDDict,
    TrainingResults,
    WOTDCorpus,
)


class WOTDStorage:
    """Unified storage for WOTD using cache + MongoDB."""

    def __init__(self) -> None:
        self._cache_lock = asyncio.Lock()

    # Corpus Management
    async def save_corpus(self, corpus: WOTDCorpus, ttl_hours: int = 24) -> None:
        """Save corpus to cache and MongoDB."""
        cache = await get_unified()
        mongo = await get_storage()
        if not mongo._initialized:
            await mongo.connect()

        # Cache with TTL for fast access
        await cache.set(
            namespace=CacheKeys.NAMESPACE,
            key=f"{CacheKeys.SYNTHETIC_CORPUS}:{corpus.id}",
            value=corpus.model_dump(),
            ttl=timedelta(hours=ttl_hours),
        )

        # Persist to MongoDB
        database = await get_database()
        collection = database[Collections.CORPORA]
        await collection.replace_one({"id": corpus.id}, corpus.model_dump(), upsert=True)

    async def get_corpus(self, corpus_id: str) -> WOTDCorpus | None:
        """Get corpus from cache or MongoDB."""
        cache = await get_unified()

        # Try cache first
        cached = await cache.get(
            namespace=CacheKeys.NAMESPACE,
            key=f"{CacheKeys.SYNTHETIC_CORPUS}:{corpus_id}",
        )
        if cached:
            return WOTDCorpus.model_validate(cached)

        # Check MongoDB if not in cache
        database = await get_database()
        collection = database[Collections.CORPORA]
        doc = await collection.find_one({"id": corpus_id})

        if doc:
            # Remove MongoDB's _id field
            doc.pop("_id", None)
            corpus = WOTDCorpus.model_validate(doc)

            # Cache for next time
            await cache.set(
                namespace=CacheKeys.NAMESPACE,
                key=f"{CacheKeys.SYNTHETIC_CORPUS}:{corpus_id}",
                value=corpus.model_dump(),
                ttl=timedelta(hours=24),
            )
            return corpus

        return None

    async def list_corpora(self, limit: int = 100) -> list[WOTDCorpus]:
        """List all corpora from MongoDB."""
        database = await get_database()
        collection = database[Collections.CORPORA]

        corpora = []
        async for doc in collection.find().limit(limit):
            doc.pop("_id", None)
            corpora.append(WOTDCorpus.model_validate(doc))

        return corpora

    async def delete_corpus(self, corpus_id: str) -> bool:
        """Delete corpus from cache and MongoDB."""
        cache = await get_unified()
        mongo = await get_storage()
        if not mongo._initialized:
            await mongo.connect()

        # Delete from cache
        await cache.delete(
            namespace=CacheKeys.NAMESPACE,
            key=f"{CacheKeys.SYNTHETIC_CORPUS}:{corpus_id}",
        )

        # Delete from MongoDB
        database = await get_database()
        collection = database[Collections.CORPORA]
        result = await collection.delete_one({"id": corpus_id})

        return result.deleted_count > 0

    # Embeddings Cache
    async def cache_embeddings(
        self,
        corpus_id: str,
        embeddings: list[float],
        ttl_hours: int = 48,
    ) -> None:
        """Cache embeddings with compression."""
        cache = await get_unified()
        await cache.set_compressed(
            namespace=CacheKeys.NAMESPACE,
            key=f"{CacheKeys.EMBEDDINGS}:{corpus_id}",
            value=embeddings,
            ttl=timedelta(hours=ttl_hours),
        )

    async def get_cached_embeddings(self, corpus_id: str) -> list[float] | None:
        """Get cached embeddings."""
        cache = await get_unified()
        return await cache.get_compressed(
            namespace=CacheKeys.NAMESPACE,
            key=f"{CacheKeys.EMBEDDINGS}:{corpus_id}",
        )

    # Semantic IDs
    async def save_semantic_ids(
        self,
        semantic_ids: SemanticIDDict,
        ttl_hours: int = 168,  # 1 week
    ) -> None:
        """Save semantic IDs mapping."""
        cache = await get_unified()
        await cache.set_compressed(
            namespace=CacheKeys.NAMESPACE,
            key=CacheKeys.SEMANTIC_IDS,
            value=semantic_ids,
            ttl=timedelta(hours=ttl_hours),
        )

    async def get_semantic_ids(self) -> SemanticIDDict | None:
        """Get semantic IDs mapping."""
        cache = await get_unified()
        return await cache.get_compressed(namespace=CacheKeys.NAMESPACE, key=CacheKeys.SEMANTIC_IDS)

    # Training Results
    async def save_training_results(self, results: TrainingResults) -> None:
        """Save training results to MongoDB."""
        database = await get_database()
        collection = database[Collections.TRAINING_RUNS]

        await collection.insert_one(results.model_dump())

    async def get_latest_training_results(self) -> TrainingResults | None:
        """Get most recent training results."""
        database = await get_database()
        collection = database[Collections.TRAINING_RUNS]

        doc = await collection.find_one(sort=[("created_at", -1)])
        if doc:
            doc.pop("_id", None)
            return TrainingResults.model_validate(doc)

        return None

    # Batch Operations
    async def save_multiple_corpora(self, corpora: list[WOTDCorpus], ttl_hours: int = 24) -> None:
        """Save multiple corpora efficiently."""
        # Parallel cache operations
        cache = await get_unified()
        cache_tasks = [
            cache.set(
                namespace=CacheKeys.NAMESPACE,
                key=f"{CacheKeys.SYNTHETIC_CORPUS}:{corpus.id}",
                value=corpus.model_dump(),
                ttl=timedelta(hours=ttl_hours),
            )
            for corpus in corpora
        ]

        # Batch MongoDB insert
        database = await get_database()
        collection = database[Collections.CORPORA]

        # Prepare documents
        docs = [corpus.model_dump() for corpus in corpora]

        # Execute operations in parallel
        await asyncio.gather(*cache_tasks, collection.insert_many(docs, ordered=False))

    async def load_corpora_dict(self) -> CorpusDict:
        """Load all corpora as dictionary for training."""
        corpora = await self.list_corpora()
        return {corpus.id: corpus for corpus in corpora}

    # Cache Management
    async def invalidate_cache(self) -> int:
        """Invalidate all WOTD cache entries."""
        cache = await get_unified()
        return await cache.invalidate_namespace(CacheKeys.NAMESPACE)

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        cache = await get_unified()
        return await cache.get_stats(CacheKeys.NAMESPACE)


# Global instance
_storage: WOTDStorage | None = None
_storage_lock = asyncio.Lock()


async def get_wotd_storage() -> WOTDStorage:
    """Get global WOTD storage instance."""
    global _storage

    if _storage is None:
        async with _storage_lock:
            if _storage is None:
                _storage = WOTDStorage()

    return _storage
