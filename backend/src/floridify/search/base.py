"""Base classes for search implementations.

Provides abstract base classes and common functionality for all search types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..caching.manager import get_version_manager
from ..caching.models import CacheNamespace
from ..corpus.core import Corpus
from ..models.versioned import ResourceType, VersionConfig, VersionInfo
from ..utils.logging import get_logger
from .models import IndexMetadata, SearchResult

logger = get_logger(__name__)


class BaseIndexedSearch(ABC):
    """Abstract base class for all indexed search implementations.

    Provides common functionality for version management, caching,
    and index lifecycle management.
    """

    def __init__(
        self,
        index_type: str,
        index_version: str = "v1.0.0",
    ):
        """Initialize base indexed search.

        Args:
            index_type: Type of index ("trie", "fuzzy", "semantic")
            index_version: Version of the index implementation
        """
        self.index_type = index_type
        self.index_version = index_version

        # Index metadata
        self.metadata: IndexMetadata | None = None
        self.corpus: Corpus | None = None

        # Version management
        self.version_info: VersionInfo | None = None
        self._version_manager = None

    async def get_version_manager(self) -> Any:
        """Get or create version manager instance."""
        if self._version_manager is None:
            self._version_manager = get_version_manager()  # type: ignore[assignment]
        return self._version_manager

    @abstractmethod
    async def build_index(self, corpus: Corpus) -> None:
        """Build the search index from a corpus.

        Args:
            corpus: Corpus to build index from
        """

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Perform search on the index.

        Args:
            query: Search query
            max_results: Maximum number of results
            **kwargs: Additional search parameters

        Returns:
            List of search results
        """

    @abstractmethod
    async def serialize(self) -> bytes:
        """Serialize the index to bytes.

        Returns:
            Serialized index data
        """

    @abstractmethod
    async def deserialize(self, data: bytes) -> None:
        """Deserialize the index from bytes.

        Args:
            data: Serialized index data
        """

    async def save(
        self,
        namespace: CacheNamespace = CacheNamespace.SEARCH,
        config: VersionConfig | None = None,
    ) -> bool:
        """Save index to versioned storage.

        Args:
            namespace: Cache namespace for storage
            config: Version configuration

        Returns:
            True if save was successful
        """
        if not self.corpus or not self.metadata:
            logger.warning("Cannot save index without corpus and metadata")
            return False

        try:
            # Get version manager
            manager = await self.get_version_manager()

            # Serialize index
            index_data = await self.serialize()

            # Create cache key
            cache_key = f"{self.index_type}_{self.corpus.vocabulary_hash}"

            # Save with version manager
            result = await manager.save_versioned(
                namespace=namespace,
                key=cache_key,
                data=index_data,
                resource_type=ResourceType.SEARCH,
                config=config or VersionConfig(),
            )

            if result:
                self.version_info = result.version_info
                logger.info(
                    f"Saved {self.index_type} index with version {result.version_info.version_hash}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to save {self.index_type} index: {e}")

        return False

    async def load(
        self,
        corpus: Corpus,
        namespace: CacheNamespace = CacheNamespace.SEARCH,
        config: VersionConfig | None = None,
    ) -> bool:
        """Load index from versioned storage.

        Args:
            corpus: Corpus for this index
            namespace: Cache namespace for storage
            config: Version configuration

        Returns:
            True if load was successful
        """
        try:
            # Get version manager
            manager = await self.get_version_manager()

            # Create cache key
            cache_key = f"{self.index_type}_{corpus.vocabulary_hash}"

            # Load with version manager
            result = await manager.get_versioned(
                namespace=namespace,
                key=cache_key,
                resource_type=ResourceType.SEARCH,
                config=config or VersionConfig(),
            )

            if result and result.data:
                # Deserialize index
                await self.deserialize(result.data)

                # Set metadata
                self.corpus = corpus
                self.version_info = result.version_info
                self.metadata = IndexMetadata(
                    index_type=self.index_type,
                    index_version=self.index_version,
                    corpus_name=corpus.corpus_name,
                    corpus_hash=corpus.vocabulary_hash,
                    corpus_size=len(corpus.vocabulary),
                    version_info=result.version_info,
                )

                logger.info(
                    f"Loaded {self.index_type} index version {result.version_info.version_hash}"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to load {self.index_type} index: {e}")

        return False

    def get_cache_key(self, prefix: str = "") -> str:
        """Generate cache key for this index.

        Args:
            prefix: Optional prefix for the cache key

        Returns:
            Cache key string
        """
        if not self.corpus:
            raise ValueError("Cannot generate cache key without corpus")

        parts = [prefix] if prefix else []
        parts.extend(
            [
                self.index_type,
                self.corpus.vocabulary_hash[:8],  # Use short hash
            ]
        )

        return "_".join(filter(None, parts))


__all__ = [
    "BaseIndexedSearch",
]
