"""SearchIndex active-record model for multi-method search index persistence."""

from __future__ import annotations

from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.core import get_versioned_content
from ..caching.manager import get_version_manager
from ..caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
    VersionConfig,
)
from ..corpus.core import Corpus
from ..corpus.utils import get_vocabulary_hash
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE
from .trie_index import TrieIndex

logger = get_logger(__name__)


def _get_default_semantic_model() -> str:
    """Lazy import to avoid circular dependency."""
    from .semantic.constants import DEFAULT_SENTENCE_MODEL

    return DEFAULT_SENTENCE_MODEL


class SearchIndex(BaseModel):
    """Complete search index data model for SearchEngine.

    Contains all configuration, references, and state for multi-method search.
    """

    # Index identification
    index_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    corpus_uuid: str  # Stable UUID reference to corpus
    corpus_name: str
    vocabulary_hash: str

    # Search configuration
    min_score: float = DEFAULT_MIN_SCORE
    semantic_enabled: bool = True
    semantic_model: str = Field(default_factory=_get_default_semantic_model)

    # Component indices (embedded or referenced)
    trie_index_id: PydanticObjectId | None = None
    semantic_index_id: PydanticObjectId | None = None

    # Component states
    has_trie: bool = False
    has_fuzzy: bool = False
    has_semantic: bool = False

    # Statistics
    vocabulary_size: int = 0
    total_indices: int = 0

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.SEARCH,
        default_namespace=CacheNamespace.SEARCH,
    ):
        """Minimal search metadata for versioning."""

        # CRITICAL: Override Beanie's default _class_id for polymorphism
        _class_id: ClassVar[str] = "SearchIndex.Metadata"

        class Settings(BaseVersionedData.Settings):
            class_id = "_class_id"

        corpus_uuid: str
        vocabulary_hash: str = ""
        has_trie: bool = False
        has_fuzzy: bool = False
        has_semantic: bool = False
        trie_index_id: PydanticObjectId | None = None
        semantic_index_id: PydanticObjectId | None = None

    @classmethod
    async def get(
        cls,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> SearchIndex | None:
        """Get search index from versioned storage by ID or name.

        Args:
            corpus_uuid: Corpus stable UUID (preferred)
            corpus_name: Name of the corpus (fallback)
            config: Version configuration

        Returns:
            SearchIndex instance or None if not found

        """
        effective_config = config or VersionConfig()
        # CRITICAL FIX: Don't clear force_rebuild flag - downstream methods need it
        # When force_rebuild=True, we want Corpus.get() and version manager to skip cache
        # The VersionedDataManager.get_latest() already checks both flags correctly:
        #   if use_cache and not config.force_rebuild: <check cache>
        if effective_config.force_rebuild:
            # Ensure use_cache=False for consistency (though force_rebuild already bypasses cache)
            effective_config = effective_config.model_copy()
            effective_config.use_cache = False

        if not corpus_uuid and not corpus_name:
            raise ValueError("Either corpus_uuid or corpus_name must be provided")

        manager = get_version_manager()

        # Build resource ID using uuid (always stable across versions)
        if corpus_uuid:
            resource_id = f"{corpus_uuid}:search"
        else:
            # Lookup uuid from corpus_name
            from ..corpus.manager import get_tree_corpus_manager

            corpus_manager = get_tree_corpus_manager()
            corpus = await corpus_manager.get_corpus(
                corpus_name=corpus_name, config=effective_config
            )
            if not corpus or not corpus.corpus_uuid:
                logger.warning(f"Corpus '{corpus_name}' not found or missing uuid")
                return None
            resource_id = f"{corpus.corpus_uuid}:search"

        # Get the latest search index metadata
        metadata: SearchIndex.Metadata | None = await manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH,
            use_cache=effective_config.use_cache,
            config=effective_config,
        )

        if not metadata:
            return None

        # Load content from metadata, respecting config.use_cache
        content = await get_versioned_content(metadata, config=effective_config)
        if not content:
            return None

        index = cls.model_validate(content)
        # Ensure the index ID is set from metadata
        if metadata.id:
            index.index_id = metadata.id
        return index

    @classmethod
    async def create(
        cls,
        corpus: Corpus,
        min_score: float = 0.75,
        semantic: bool = True,
        semantic_model: str | None = None,
    ) -> SearchIndex:
        """Create new search index from corpus.

        Args:
            corpus: Corpus containing vocabulary
            min_score: Minimum score threshold for results
            semantic: Enable semantic search
            semantic_model: Semantic model to use for embeddings

        Returns:
            SearchIndex instance with initialized configuration

        """
        if not corpus.corpus_uuid:
            raise ValueError("Corpus must have corpus_uuid set")

        return cls(
            corpus_uuid=corpus.corpus_uuid,
            corpus_name=corpus.corpus_name,
            vocabulary_hash=get_vocabulary_hash(corpus.vocabulary),
            min_score=min_score,
            semantic_enabled=semantic,
            semantic_model=semantic_model or _get_default_semantic_model(),
            vocabulary_size=len(corpus.vocabulary),
            has_trie=True,  # Always build trie for exact/prefix search
            has_fuzzy=True,  # Always enable fuzzy
            has_semantic=semantic,
        )

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        min_score: float = 0.75,
        semantic: bool = True,
        semantic_model: str | None = None,
        config: VersionConfig | None = None,
    ) -> SearchIndex:
        """Get existing search index or create new one.

        Args:
            corpus: Corpus containing vocabulary
            min_score: Minimum score threshold
            semantic: Enable semantic search
            semantic_model: Semantic model to use for embeddings
            config: Version configuration

        Returns:
            SearchIndex instance

        """
        # Try to get existing using corpus ID if available, otherwise name
        try:
            existing = await cls.get(
                corpus_uuid=corpus.corpus_uuid,
                corpus_name=corpus.corpus_name,
                config=config,
            )
            if existing and existing.vocabulary_hash == get_vocabulary_hash(corpus.vocabulary):
                # Upgrade semantic if requested but not currently enabled
                if semantic and not existing.semantic_enabled:
                    existing.semantic_enabled = True
                    existing.has_semantic = True
                    await existing.save(config)
                return existing
        except RuntimeError as e:
            # Handle corrupted data gracefully - proceed to create new
            logger.warning(f"Could not load existing search index (likely corrupted): {e}")

        # Create new
        index = await cls.create(
            corpus=corpus,
            min_score=min_score,
            semantic=semantic,
            semantic_model=semantic_model,
        )

        # Save the new index
        await index.save(config)
        return index

    async def save(
        self,
        config: VersionConfig | None = None,
    ) -> None:
        """Save search index to versioned storage with verification.

        Args:
            config: Version configuration

        Raises:
            RuntimeError: If save fails or verification fails

        """
        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:search"

        try:
            # Save using version manager - convert ObjectIds to strings for JSON
            await manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.SEARCH,
                namespace=manager._get_namespace(ResourceType.SEARCH),
                content=self.model_dump(mode="json"),
                config=config or VersionConfig(),
                metadata={
                    "corpus_uuid": self.corpus_uuid,
                    "vocabulary_hash": self.vocabulary_hash,
                    "has_trie": self.has_trie,
                    "has_fuzzy": self.has_fuzzy,
                    "has_semantic": self.has_semantic,
                    "trie_index_id": str(self.trie_index_id) if self.trie_index_id else None,
                    "semantic_index_id": str(self.semantic_index_id)
                    if self.semantic_index_id
                    else None,
                },
            )

            # Verify save succeeded
            saved = await self.get(corpus_uuid=self.corpus_uuid, config=config)
            if not saved:
                raise ValueError("Could not retrieve saved search index")
            if saved.vocabulary_hash != self.vocabulary_hash:
                raise ValueError(
                    f"Vocabulary hash mismatch after save: "
                    f"expected {self.vocabulary_hash}, got {saved.vocabulary_hash}"
                )

            # Verify component references are intact
            if self.has_trie and saved.trie_index_id != self.trie_index_id:
                raise ValueError("Trie index reference mismatch after save")
            if self.has_semantic and saved.semantic_index_id != self.semantic_index_id:
                raise ValueError("Semantic index reference mismatch after save")

            logger.info(f"Successfully saved and verified search index for {resource_id}")

        except Exception as e:
            logger.error(f"Failed to save search index {resource_id}: {e}")
            raise RuntimeError(
                f"Search index persistence failed for corpus {self.corpus_uuid}. "
                f"Index references may be corrupted. Error: {e}"
            ) from e

    async def delete(self) -> None:
        """Delete search index from storage with cascade deletion of dependent indices.

        Deletion order:
        1. Delete TrieIndex if it exists
        2. Delete SemanticIndex if it exists
        3. Delete the SearchIndex document itself

        Raises:
            ValueError: If corpus_uuid is not set
        """
        if not self.corpus_uuid:
            logger.warning("Cannot delete search index without corpus_uuid")
            raise ValueError("Cannot delete search index without corpus_uuid")

        logger.info(
            f"Starting cascade deletion for SearchIndex of corpus {self.corpus_name} (uuid: {self.corpus_uuid})"
        )

        # Step 1: Delete TrieIndex if it exists
        if self.has_trie and self.trie_index_id:
            try:
                logger.info(f"Deleting TrieIndex {self.trie_index_id}...")
                trie_index = await TrieIndex.get(corpus_uuid=self.corpus_uuid)
                if trie_index:
                    await trie_index.delete()
                else:
                    logger.debug(
                        f"TrieIndex {self.trie_index_id} not found, may already be deleted"
                    )
            except Exception as e:
                logger.error(f"Error deleting TrieIndex {self.trie_index_id}: {e}")
                # Continue with deletion even if TrieIndex deletion fails

        # Step 2: Delete SemanticIndex if it exists
        if self.has_semantic and self.semantic_index_id:
            try:
                logger.info(f"Deleting SemanticIndex {self.semantic_index_id}...")
                from ..search.semantic.models import SemanticIndex

                # SemanticIndex requires model_name, use the stored one
                semantic_index = await SemanticIndex.get(
                    corpus_uuid=self.corpus_uuid,
                    model_name=self.semantic_model,
                )
                if semantic_index:
                    await semantic_index.delete()
                else:
                    logger.debug(
                        f"SemanticIndex {self.semantic_index_id} not found, may already be deleted"
                    )
            except Exception as e:
                logger.error(f"Error deleting SemanticIndex {self.semantic_index_id}: {e}")
                # Continue with deletion even if SemanticIndex deletion fails

        # Step 3: Delete the SearchIndex itself through version manager
        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:search"

        try:
            # Get the latest version to delete
            metadata = await manager.get_latest(
                resource_id=resource_id,
                resource_type=ResourceType.SEARCH,
            )

            if metadata and metadata.version_info:
                await manager.delete_version(
                    resource_id=resource_id,
                    resource_type=ResourceType.SEARCH,
                    version=metadata.version_info.version,
                )
                logger.info(
                    f"Successfully deleted SearchIndex for corpus {self.corpus_name} (uuid: {self.corpus_uuid})"
                )
            else:
                logger.warning(
                    f"No metadata found for SearchIndex {resource_id}, may already be deleted"
                )
        except Exception as e:
            logger.error(f"Failed to delete SearchIndex {resource_id}: {e}")
            raise RuntimeError(f"SearchIndex deletion failed for {resource_id}: {e}") from e


__all__ = [
    "SearchIndex",
]
