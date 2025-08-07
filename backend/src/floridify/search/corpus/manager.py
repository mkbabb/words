"""
Cache and retrieval manager for Corpus instances.

Provides get/create/invalidate operations for Corpus objects with
lightweight MongoDB metadata storage.
"""

from __future__ import annotations

import time
from typing import Any

from ...caching.core import CacheNamespace, CacheTTL
from ...caching.unified import get_unified
from ...utils.logging import get_logger
from ..utils import get_vocabulary_hash
from ..models import CorpusMetadata
from .core import Corpus

logger = get_logger(__name__)


class CorpusManager:
    """
    Cache and retrieval manager for Corpus instances.

    Similar to SemanticManager - handles caching and returns Corpus objects
    instead of CorpusMetadata. Stores only metadata in MongoDB.
    """

    def __init__(self) -> None:
        """Initialize corpus manager."""
        pass

    async def get_corpus(
        self,
        corpus_name: str,
        vocab_hash: str | None = None,
        vocabulary: list[str] | None = None,
    ) -> Corpus | None:
        """
        Get existing corpus from cache.

        Args:
            corpus_name: Unique name for the corpus
            vocab_hash: Pre-computed vocabulary hash (preferred)
            vocabulary: Vocabulary to hash if vocab_hash not provided

        Returns:
            Cached Corpus instance or None if not found
        """
        if vocab_hash is None:
            if vocabulary is None:
                raise ValueError("Must provide either vocab_hash or vocabulary")
            vocab_hash = get_vocabulary_hash(vocabulary)

        cache = await get_unified()
        cache_key = f"corpus:{corpus_name}:{vocab_hash}"
        logger.debug(f"Looking for corpus in cache with key: {cache_key}")
        cached_data: dict[str, Any] | None = await cache.get(CacheNamespace.CORPUS, cache_key)
        if cached_data:
            corpus = Corpus.model_load(cached_data)
            logger.info(f"Cache hit for corpus '{corpus_name}' (using hash: {vocab_hash})")
            return corpus

        logger.info(f"Cache miss for corpus '{corpus_name}' (looking for hash: {vocab_hash})")
        return None

    async def get_corpus_metadata(self, corpus_name: str) -> CorpusMetadata | None:
        """
        Get corpus metadata from MongoDB.

        Args:
            corpus_name: Corpus name to find

        Returns:
            CorpusMetadata from MongoDB or None if not found
        """
        try:
            corpus_data = await CorpusMetadata.find_one({"corpus_name": corpus_name})
            if corpus_data:
                logger.info(f"Found corpus metadata in MongoDB: '{corpus_name}' (metadata hash: {corpus_data.vocabulary_hash})")
                return corpus_data
        except Exception as e:
            logger.warning(f"Error finding corpus metadata '{corpus_name}': {e}")
        return None

    async def create_corpus(
        self,
        corpus_name: str,
        vocabulary: list[str],
    ) -> Corpus:
        """
        Create new corpus with caching and metadata storage.

        Args:
            corpus_name: Unique name for the corpus
            vocabulary: Combined list of words and phrases

        Returns:
            Fully processed Corpus instance
        """
        logger.info(f"Creating new corpus '{corpus_name}' with {len(vocabulary)} vocabulary items")
        start_time = time.perf_counter()

        # Create corpus using Corpus.create()
        corpus = await Corpus.create(corpus_name, vocabulary, False)
        logger.debug(f"Corpus object created with hash: {corpus.vocabulary_hash[:8]}...")

        # Cache the corpus instance
        cache = await get_unified()
        cache_key = f"corpus:{corpus_name}:{corpus.vocabulary_hash}"
        logger.info(f"Caching corpus with key: {cache_key} (full hash: {corpus.vocabulary_hash})")
        await cache.set(
            namespace=CacheNamespace.CORPUS,
            key=cache_key,
            value=corpus.model_dump(),
            ttl=CacheTTL.CORPUS,
            tags=[f"{CacheNamespace.CORPUS}:{corpus_name}"],
        )
        logger.debug("Corpus cached successfully")

        # Save lightweight metadata to MongoDB (optional - continue without database if it fails)
        try:
            corpus_data = CorpusMetadata(
                corpus_name=corpus.corpus_name,
                vocabulary_hash=corpus.vocabulary_hash,
                vocabulary_stats=corpus.vocabulary_stats,
                metadata=corpus.metadata,
                semantic_data_id=None,
            )
            await corpus_data.save()
            logger.info(f"Stored corpus metadata in MongoDB for '{corpus_name}' (full hash: {corpus.vocabulary_hash})")
        except Exception as e:
            logger.warning(
                f"Failed to store corpus metadata in MongoDB (continuing without database): {e}"
            )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Created corpus '{corpus_name}' in {elapsed_ms}ms")

        return corpus

    async def get_or_create_corpus(
        self,
        corpus_name: str,
        vocabulary: list[str],
        vocab_hash: str | None = None,
        force_rebuild: bool = False,
    ) -> Corpus:
        """
        Get existing or create new corpus.

        Args:
            corpus_name: Unique name for the corpus
            vocabulary: Combined list of words and phrases
            vocab_hash: Pre-computed vocabulary hash (optional, for efficiency)
            force_rebuild: Force rebuild even if cached

        Returns:
            Corpus instance with pre-computed indices and embeddings
        """
        if not force_rebuild:
            logger.debug(f"Checking for existing corpus '{corpus_name}'")
            existing = await self.get_corpus(
                corpus_name, vocab_hash=vocab_hash, vocabulary=vocabulary
            )
            if existing is not None:
                logger.info(f"Using existing corpus '{corpus_name}'")
                return existing
            logger.debug(f"No existing corpus found, will create new")

        return await self.create_corpus(corpus_name, vocabulary)

    async def invalidate_corpus(self, corpus_name: str) -> bool:
        """
        Invalidate and remove corpus instance with cascading deletion.

        Args:
            corpus_name: Corpus name to invalidate

        Returns:
            True if instance was removed, False if not found
        """
        # Invalidate unified cache by tags
        cache = await get_unified()
        cache_removed = await cache.invalidate_by_tags([f"{CacheNamespace.CORPUS}:{corpus_name}"])

        # Remove CorpusMetadata from MongoDB (optional - continue without database if it fails)
        deleted_count = 0
        try:
            async for corpus_data in CorpusMetadata.find({"corpus_name": corpus_name}):
                await corpus_data.delete()
                deleted_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to remove corpus metadata from MongoDB (continuing without database): {e}"
            )

        removed = cache_removed > 0 or deleted_count > 0
        if removed:
            logger.info(
                f"Invalidated corpus '{corpus_name}' (cache: {cache_removed}, db: {deleted_count})"
            )

        return removed

    async def invalidate_all_corpora(self) -> dict[str, int]:
        """
        Invalidate all corpus instances and metadata.

        Returns:
            Dictionary with counts of removed items
        """
        # Invalidate all corpus cache entries
        cache = await get_unified()
        cache_removed = await cache.invalidate_namespace(CacheNamespace.CORPUS)

        # Remove all CorpusMetadata from MongoDB
        deleted_count = 0
        try:
            async for corpus_data in CorpusMetadata.find():
                await corpus_data.delete()
                deleted_count += 1
        except Exception as e:
            logger.warning(f"Failed to remove corpus metadata from MongoDB: {e}")

        logger.info(f"Invalidated all corpora (cache: {cache_removed}, db: {deleted_count})")

        return {
            "cache_removed": cache_removed,
            "db_removed": deleted_count,
            "total": cache_removed + deleted_count,
        }

    async def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about cached corpora.

        Returns:
            Dictionary with corpus statistics
        """
        # Get database corpus count and names
        db_count = 0
        corpus_names = []
        total_vocabulary_size = 0
        try:
            async for corpus_data in CorpusMetadata.find():
                db_count += 1
                corpus_names.append(corpus_data.corpus_name)
                if corpus_data.vocabulary_stats:
                    total_vocabulary_size += corpus_data.vocabulary_stats.get("total", 0)
        except Exception as e:
            logger.warning(f"Failed to get corpus stats from MongoDB: {e}")

        # Get approximate cache count (based on corpus names)
        # Since we can't directly count cache entries, estimate based on corpus names
        cache_count = len(corpus_names)  # Approximate

        return {
            "cache_entries": cache_count,
            "db_entries": db_count,
            "corpus_names": corpus_names,
            "total_vocabulary_size": total_vocabulary_size,
            "total_entries": db_count,
        }


# Global instance
_corpus_manager: CorpusManager | None = None


def get_corpus_manager() -> CorpusManager:
    """Get the global corpus manager instance."""
    global _corpus_manager
    if _corpus_manager is None:
        _corpus_manager = CorpusManager()
    return _corpus_manager
