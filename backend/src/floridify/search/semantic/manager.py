"""Semantic Search Manager - Centralized management of semantic search instances.

Provides unified API for managing semantic search instances with proper
versioning, caching, and lifecycle management.
"""

from __future__ import annotations

import time
from datetime import timedelta

from ...caching.models import CacheTTL
from ...caching.manager import BaseManager
from ...core.constants import ResourceType
from ...caching.versioned import VersionConfig, VersionedDataManager, get_semantic_version_manager
from ...corpus.core import Corpus
from ...models.versioned import SemanticVersionedData
from ..models import SemanticMetadata
from .constants import DEFAULT_SENTENCE_MODEL
from .core import SemanticSearch


class SemanticSearchManager(BaseManager[SemanticSearch, SemanticMetadata]):
    """Centralized manager for semantic search instances.

    Uses unified versioning API for creation, caching, and lifecycle management.
    """

    def __init__(self) -> None:
        """Initialize semantic search manager."""
        super().__init__()

    @property
    def resource_type(self) -> ResourceType:
        """Get the resource type this manager handles."""
        return ResourceType.SEMANTIC

    @property
    def default_cache_ttl(self) -> timedelta | None:
        """Get default cache TTL for semantic operations."""
        return CacheTTL.SEMANTIC

    def _get_version_manager(self) -> VersionedDataManager[SemanticVersionedData]:
        """Get the version manager for semantic search."""
        return get_semantic_version_manager()

    async def _reconstruct_resource(
        self, versioned_data: SemanticVersionedData
    ) -> SemanticSearch | None:
        """Reconstruct semantic search from versioned data."""
        try:
            if versioned_data.content_inline:
                from .core import SemanticSearch as SemanticSearchClass

                return SemanticSearchClass.model_load(versioned_data.content_inline)
            if versioned_data.content_location:
                # Load content from storage
                version_manager = self._get_version_manager()
                content = await version_manager.load_content(versioned_data.content_location)
                if content:
                    from .core import SemanticSearch as SemanticSearchClass

                    return SemanticSearchClass.model_load(content)
            return None
        except Exception:
            return None

    async def create_semantic_index(
        self,
        corpus_name: str,
        corpus: Corpus,
        model_name: str | None = None,
        use_ttl: bool = True,
    ) -> SemanticMetadata:
        """Create a new semantic index from corpus.

        Args:
            corpus_name: Unique name for the corpus
            corpus: Corpus with vocabulary to index
            model_name: Embedding model (defaults to BGE-M3)
            use_ttl: Whether to use TTL for caching

        Returns:
            Semantic metadata

        """
        # Use default model if not provided
        if model_name is None:
            model_name = DEFAULT_SENTENCE_MODEL

        # Create semantic search instance
        start_time = time.time()
        semantic_search = SemanticSearch(corpus, model_name)  # type: ignore[arg-type]
        build_time_ms = (time.time() - start_time) * 1000

        # Create metadata
        vocab_hash = corpus.vocabulary_hash

        # Get dimension from embeddings if available
        embedding_dimension = 0
        if semantic_search.sentence_embeddings is not None:
            embedding_dimension = semantic_search.sentence_embeddings.shape[1]

        metadata = SemanticMetadata(
            corpus_data_id=None,  # Will be set if linked to corpus
            vocabulary_hash=vocab_hash,
            model_name=model_name,
            embedding_dimension=embedding_dimension,
            vocabulary_size=len(corpus.vocabulary),
            build_time_ms=build_time_ms,
        )

        # Configure versioning
        config = VersionConfig(
            force_rebuild=False,
            check_cache=True,
            save_versions=True,
            ttl=CacheTTL.SEMANTIC if use_ttl else None,
        )

        # Save to versioned storage
        index_name = f"{corpus_name}_{model_name.replace('/', '_')}"
        version_manager = self._get_version_manager()
        await version_manager.save(
            resource_id=index_name,
            content=semantic_search.model_dump(),
            resource_type=self.resource_type.value,
            metadata=metadata.model_dump(),
            tags=["semantic", corpus_name],
            config=config,
            index_name=index_name,
            corpus_id=corpus_name,
            embedding_model=model_name,
            dimension=embedding_dimension,
            total_vectors=len(corpus.vocabulary),
        )

        # Cache the instance
        self._cache[index_name] = semantic_search

        # Save metadata to MongoDB
        await metadata.save()

        return metadata

    async def get_semantic_index(
        self,
        corpus_name: str,
        model_name: str | None = None,
        use_ttl: bool = True,
    ) -> SemanticSearch | None:
        """Get existing semantic search instance.

        Args:
            corpus_name: Unique name for the corpus
            model_name: Embedding model (defaults to BGE-M3)
            use_ttl: Whether to use TTL for caching

        Returns:
            SemanticSearch instance or None if not found

        """
        # Use default model if not provided
        if model_name is None:
            model_name = DEFAULT_SENTENCE_MODEL

        index_name = f"{corpus_name}_{model_name.replace('/', '_')}"
        return await self.get(index_name, use_ttl)

    async def get_or_create_semantic_index(
        self,
        corpus_name: str,
        corpus: Corpus | None = None,
        model_name: str | None = None,
        use_ttl: bool = True,
    ) -> tuple[SemanticSearch, SemanticMetadata]:
        """Get existing semantic index or create new one.

        Args:
            corpus_name: Unique name for the corpus
            corpus: Corpus with vocabulary (required for creation)
            model_name: Embedding model (defaults to BGE-M3)
            use_ttl: Whether to use TTL for caching

        Returns:
            Tuple of (semantic_search, metadata)

        """
        # Try to get existing index
        semantic_search = await self.get_semantic_index(corpus_name, model_name, use_ttl)
        if semantic_search:
            index_name = f"{corpus_name}_{(model_name or DEFAULT_SENTENCE_MODEL).replace('/', '_')}"
            metadata = await SemanticMetadata.find_one({"index_name": index_name})
            if metadata:
                return semantic_search, metadata

        # Create new index if corpus provided
        if corpus is None:
            raise ValueError(f"Corpus required to create semantic index for '{corpus_name}'")

        metadata = await self.create_semantic_index(
            corpus_name=corpus_name,
            corpus=corpus,
            model_name=model_name,
            use_ttl=use_ttl,
        )
        index_name = f"{corpus_name}_{(model_name or DEFAULT_SENTENCE_MODEL).replace('/', '_')}"
        semantic_search = self._cache[index_name]
        return semantic_search, metadata

    async def cleanup_versions(  # type: ignore[override]
        self,
        corpus_name: str | None = None,
        model_name: str | None = None,
        keep_count: int = 3,
    ) -> int:
        """Clean up old versions of semantic indices.

        Args:
            corpus_name: Optional corpus name to clean up
            model_name: Optional model name to clean up
            keep_count: Number of versions to keep

        Returns:
            Total number of versions deleted

        """
        if corpus_name and model_name:
            index_name = f"{corpus_name}_{model_name.replace('/', '_')}"
            return await super().cleanup_versions(index_name, keep_count)
        if corpus_name:
            # Clean up all models for a corpus
            total_deleted = 0
            for model in [DEFAULT_SENTENCE_MODEL, "sentence-transformers/all-MiniLM-L6-v2"]:
                index_name = f"{corpus_name}_{model.replace('/', '_')}"
                deleted = await super().cleanup_versions(index_name, keep_count)
                total_deleted += deleted
            return total_deleted
        # Clean up all indices
        total_deleted = 0
        for index_name in self._cache.keys():
            deleted = await super().cleanup_versions(index_name, keep_count)
            total_deleted += deleted
        return total_deleted


# Global instance for singleton pattern
_semantic_search_manager: SemanticSearchManager | None = None


def get_semantic_search_manager() -> SemanticSearchManager:
    """Get the global semantic search manager instance."""
    global _semantic_search_manager
    if _semantic_search_manager is None:
        _semantic_search_manager = SemanticSearchManager()
    return _semantic_search_manager
