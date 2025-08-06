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
from ...text.search import get_vocabulary_hash
from ...utils.logging import get_logger
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
        cached_data: dict[str, Any] | None = await cache.get(
            CacheNamespace.CORPUS, cache_key
        )
        if cached_data:
            corpus = Corpus.model_load(cached_data)
            logger.debug(f"Cache hit for corpus '{corpus_name}'")
            return corpus

        logger.error(f"🚨 CORPUS CACHE MISS: corpus='{corpus_name}', vocab_hash='{vocab_hash[:8]}...', cache_key='{cache_key}'")
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
                logger.debug(f"Found corpus metadata in MongoDB: '{corpus_name}'")
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
        logger.info(
            f"Creating corpus '{corpus_name}' with {len(vocabulary)} vocabulary items"
        )
        start_time = time.perf_counter()

        # Create corpus using Corpus.create()
        corpus = await Corpus.create(corpus_name, vocabulary, False)
        
        # Cache the corpus instance
        cache = await get_unified()
        cache_key = f"corpus:{corpus_name}:{corpus.vocabulary_hash}"
        await cache.set(
            namespace=CacheNamespace.CORPUS,
            key=cache_key,
            value=corpus.model_dump(),
            ttl=CacheTTL.CORPUS,
            tags=[f"{CacheNamespace.CORPUS}:{corpus_name}"],
        )

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
            logger.info("Stored corpus metadata in MongoDB")
        except Exception as e:
            logger.warning(f"Failed to store corpus metadata in MongoDB (continuing without database): {e}")


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
            existing = await self.get_corpus(
                corpus_name, vocab_hash=vocab_hash, vocabulary=vocabulary
            )
            if existing is not None:
                return existing

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
            logger.warning(f"Failed to remove corpus metadata from MongoDB (continuing without database): {e}")


        removed = cache_removed > 0 or deleted_count > 0
        if removed:
            logger.info(
                f"Invalidated corpus '{corpus_name}' (cache: {cache_removed}, db: {deleted_count})"
            )

        return removed


# Global instance
_corpus_manager: CorpusManager | None = None


def get_corpus_manager() -> CorpusManager:
    """Get the global corpus manager instance."""
    global _corpus_manager
    if _corpus_manager is None:
        _corpus_manager = CorpusManager()
    return _corpus_manager
