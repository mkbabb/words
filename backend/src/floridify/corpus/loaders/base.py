"""Base loader class for consistent corpus loading API."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...caching.core import get_global_cache
from ...caching.models import CacheNamespace
from ...utils.logging import get_logger
from ..models import LexiconData

logger = get_logger(__name__)


class BaseCorpusLoader(ABC):
    """Abstract base class for all corpus loaders.

    Provides consistent API for loading language and literature corpora.
    """

    def __init__(self, force_rebuild: bool = False):
        """Initialize base corpus loader.

        Args:
            force_rebuild: Force rebuilding corpus from source

        """
        self.force_rebuild = force_rebuild
        self._cache: Any = None  # GlobalCacheManager instance

    async def get_cache(self) -> Any:
        """Get or create cache instance."""
        if self._cache is None:
            self._cache = await get_global_cache()
        return self._cache

    @abstractmethod
    async def load_corpus(
        self,
        source_id: str,
        **kwargs: Any,
    ) -> LexiconData | None:
        """Load corpus from source.

        Args:
            source_id: Identifier for the corpus source
            **kwargs: Additional loader-specific parameters

        Returns:
            Loaded corpus data or None if loading fails

        """

    @abstractmethod
    async def get_or_create_corpus(
        self,
        corpus_name: str,
        **kwargs: Any,
    ) -> LexiconData | None:
        """Get existing corpus from cache or create new one.

        Args:
            corpus_name: Name of the corpus
            **kwargs: Additional loader-specific parameters

        Returns:
            Corpus data from cache or newly created

        """

    async def _cache_corpus(
        self,
        cache_key: str,
        data: LexiconData,
        ttl: int | None = None,
    ) -> None:
        """Cache corpus data.

        Args:
            cache_key: Key for caching
            data: Corpus data to cache
            ttl: Time to live in seconds

        """
        cache = await self.get_cache()
        await cache.set_compressed(
            namespace=CacheNamespace.CORPUS,
            key=cache_key,
            value=data.model_dump(),
            ttl=ttl,
        )

    async def _get_cached_corpus(
        self,
        cache_key: str,
    ) -> LexiconData | None:
        """Get corpus from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached corpus data or None

        """
        if self.force_rebuild:
            return None

        cache = await self.get_cache()
        cached = await cache.get(
            namespace=CacheNamespace.CORPUS,
            key=cache_key,
        )

        if cached:
            return LexiconData(**cached)
        return None

    def _calculate_metrics(self, vocabulary: list[str]) -> dict[str, float]:
        """Calculate vocabulary metrics.

        Args:
            vocabulary: List of words

        Returns:
            Dictionary of calculated metrics

        """
        if not vocabulary:
            return {
                "vocabulary_diversity": 0.0,
                "average_word_length": 0.0,
            }

        # Calculate vocabulary diversity (unique/total ratio)
        unique_words = set(vocabulary)
        vocabulary_diversity = len(unique_words) / len(vocabulary)

        # Calculate average word length
        total_length = sum(len(word) for word in vocabulary)
        average_word_length = total_length / len(vocabulary)

        return {
            "vocabulary_diversity": vocabulary_diversity,
            "average_word_length": average_word_length,
        }
