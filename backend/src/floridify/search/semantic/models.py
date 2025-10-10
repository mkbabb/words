"""Semantic search models."""

from __future__ import annotations

from typing import Any, ClassVar

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ...caching.core import get_versioned_content
from ...caching.manager import get_version_manager
from ...caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ResourceType,
    VersionConfig,
)
from ...corpus.core import Corpus
from ...utils.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "SemanticIndex",
]


class SemanticIndex(BaseModel):
    """Complete semantic index data model for SemanticSearch.

    Contains all embeddings, FAISS index, and semantic search data.
    """

    # Index identification
    index_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    corpus_id: PydanticObjectId
    corpus_name: str
    vocabulary_hash: str
    model_name: str

    # Model configuration
    batch_size: int = 32
    device: str = "cpu"

    # Index data - stored externally via content_location, not inline
    # These fields are removed to prevent double storage and MongoDB size issues
    # Data is accessed via get_versioned_content() from the metadata object

    # Vocabulary and mappings
    vocabulary: list[str] = Field(default_factory=list)
    lemmatized_vocabulary: list[str] = Field(default_factory=list)
    variant_mapping: dict[str, int] = Field(default_factory=dict)  # embedding idx -> lemma idx
    lemma_to_embeddings: dict[str, list[int]] = Field(
        default_factory=dict,
    )  # lemma idx -> embedding idxs

    # Index configuration
    index_type: str = "Flat"  # Flat, IVF, IVFPQ, etc.
    index_params: dict[str, Any] = Field(default_factory=dict)  # nlist, nprobe, etc.

    # Statistics
    num_embeddings: int = 0
    embedding_dimension: int = 0
    build_time_seconds: float = 0.0
    memory_usage_mb: float = 0.0
    embeddings_per_second: float = 0.0

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.SEMANTIC,
        default_namespace=CacheNamespace.SEMANTIC,
    ):
        """Minimal semantic metadata for versioning."""

        # CRITICAL: Override Beanie's default _class_id for polymorphism
        # Without this, Beanie uses "BaseVersionedData.Metadata" for all subclasses
        _class_id: ClassVar[str] = "SemanticIndex.Metadata"

        corpus_id: PydanticObjectId
        model_name: str
        vocabulary_hash: str = ""
        embedding_dimension: int = 0
        index_type: str = "flat"

    @classmethod
    async def get(
        cls,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        model_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> SemanticIndex | None:
        """Get semantic index from versioned storage by ID or name.

        Args:
            corpus_id: Corpus ObjectId (preferred)
            corpus_name: Name of the corpus (fallback)
            model_name: Name of the embedding model
            config: Version configuration

        Returns:
            SemanticIndex instance or None if not found

        """
        # Skip cache entirely if force_rebuild is requested
        if config and config.force_rebuild:
            return None

        if not corpus_id and not corpus_name:
            raise ValueError("Either corpus_id or corpus_name must be provided")

        model_name = model_name or "all-MiniLM-L6-v2"
        manager = get_version_manager()

        # Build resource ID - always use corpus_id for consistency
        # If only corpus_name provided, look up corpus_id first
        if not corpus_id and corpus_name:
            from floridify.corpus.core import Corpus

            corpus = await Corpus.get(corpus_name=corpus_name, config=config)
            if not corpus:
                logger.warning(f"Corpus '{corpus_name}' not found")
                return None
            corpus_id = corpus.corpus_id

        resource_id = f"{corpus_id!s}:semantic:{model_name}"

        # Get the latest semantic index metadata
        metadata: SemanticIndex.Metadata | None = await manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEMANTIC,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

        if not metadata:
            return None

        # Load content from metadata
        content = await get_versioned_content(metadata)
        if not content:
            return None

        index = cls.model_validate(content)

        # FIX: Preserve binary_data from external storage
        # This is critical for loading embeddings and FAISS indices
        if "binary_data" in content:
            object.__setattr__(index, "binary_data", content["binary_data"])

        # Ensure the index ID is set from metadata
        if metadata.id:
            index.index_id = metadata.id
        return index

    @classmethod
    async def create(
        cls,
        corpus: Corpus,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int | None = None,
    ) -> SemanticIndex:
        """Create new semantic index from corpus.

        Args:
            corpus: Corpus containing vocabulary and lemmas
            model_name: Sentence transformer model to use
            batch_size: Batch size for embedding generation

        Returns:
            SemanticIndex instance ready for embedding generation

        """
        from .constants import DEFAULT_BATCH_SIZE, MODEL_BATCH_SIZES

        logger.info(f"Creating semantic index for '{corpus.corpus_name}' with model '{model_name}'")

        # Auto-select batch size if not provided
        if batch_size is None:
            batch_sizes: dict[str, int] = MODEL_BATCH_SIZES  # type: ignore
            batch_size = batch_sizes.get(model_name, DEFAULT_BATCH_SIZE)

        return cls(
            corpus_id=corpus.corpus_id
            if (hasattr(corpus, "corpus_id") and corpus.corpus_id)
            else PydanticObjectId(),
            corpus_name=corpus.corpus_name,
            vocabulary_hash=corpus.vocabulary_hash,
            model_name=model_name,
            batch_size=batch_size,
            vocabulary=corpus.vocabulary,
            lemmatized_vocabulary=corpus.lemmatized_vocabulary,
        )

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int | None = None,
        config: VersionConfig | None = None,
    ) -> SemanticIndex:
        """Get existing semantic index or create new one.

        Args:
            corpus: Corpus containing vocabulary
            model_name: Name of the embedding model
            batch_size: Batch size for embedding generation
            config: Version configuration

        Returns:
            SemanticIndex instance

        """
        # Try to get existing using corpus ID if available, otherwise name
        existing = await cls.get(
            corpus_id=corpus.corpus_id,
            corpus_name=corpus.corpus_name,
            model_name=model_name,
            config=config,
        )

        # FIX: Check if embeddings actually exist before returning cached
        # Reject cached indices with 0 embeddings (corrupted/incomplete builds)
        if (
            existing
            and existing.vocabulary_hash == corpus.vocabulary_hash
            and existing.num_embeddings > 0
        ):
            logger.debug(
                f"Using cached semantic index for corpus '{corpus.corpus_name}' "
                f"with model '{model_name}' ({existing.num_embeddings:,} embeddings)"
            )
            return existing

        if existing and existing.num_embeddings == 0:
            logger.warning(
                f"Found cached semantic index for '{corpus.corpus_name}' but it has 0 embeddings. "
                f"Will rebuild."
            )

        # Create new (but DON'T save yet - let caller save after building embeddings)
        logger.info(f"Creating new semantic index for corpus '{corpus.corpus_name}'")
        index = await cls.create(
            corpus=corpus,
            model_name=model_name,
            batch_size=batch_size,
        )

        # NOTE: Not saving here - caller must save after building embeddings
        # This prevents saving empty indices to the cache
        return index

    async def save(
        self,
        config: VersionConfig | None = None,
        corpus_id: PydanticObjectId | None = None,
        binary_data: dict[str, str] | None = None,
    ) -> None:
        """Save semantic index to versioned storage.

        Large binary data (embeddings, FAISS index) is automatically stored
        externally via the filesystem cache for indices > 16MB.

        Args:
            config: Version configuration
            corpus_id: ID of the associated corpus
            binary_data: Optional dict with 'embeddings' and 'index_data' keys
                        containing base64-encoded binary data

        """
        manager = get_version_manager()
        # Use corpus_id for consistency with get() method
        cid = corpus_id or self.corpus_id
        resource_id = f"{cid!s}:semantic:{self.model_name}"

        # Prepare content - exclude binary data from inline storage
        content = self.model_dump(exclude_none=True)

        # If binary data provided, merge it for external storage
        if binary_data:
            content["binary_data"] = binary_data

        try:
            # Save using version manager - large content automatically goes to filesystem
            await manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.SEMANTIC,
                namespace=manager._get_namespace(ResourceType.SEMANTIC),
                content=content,
                config=config or VersionConfig(),
                metadata={
                    "corpus_id": str(corpus_id or self.corpus_id) if (corpus_id or self.corpus_id) else None,
                    "model_name": self.model_name,
                    "vocabulary_hash": self.vocabulary_hash,
                    "embedding_dimension": self.embedding_dimension,
                    "index_type": self.index_type,
                    # Extra metadata (not in Metadata model)
                    "num_embeddings": self.num_embeddings,
                },
            )

            # Verify save succeeded by attempting to retrieve
            saved = await self.get(corpus_id=cid, model_name=self.model_name, config=config)
            if not saved:
                raise RuntimeError(
                    f"Verification failed: Could not retrieve saved semantic index {resource_id}"
                )

            logger.info(f"Successfully saved and verified semantic index for {resource_id}")

        except Exception as e:
            logger.error(f"Failed to save semantic index {resource_id}: {e}")
            raise RuntimeError(
                f"Semantic index persistence failed for {resource_id}. "
                f"Index may be corrupted or too large. Error: {e}"
            ) from e

    async def delete(self) -> None:
        """Delete semantic index from versioned storage.

        Raises:
            ValueError: If corpus_id is not set
        """
        if not self.corpus_id:
            logger.warning("Cannot delete semantic index without corpus_id")
            raise ValueError("Cannot delete semantic index without corpus_id")

        logger.info(
            f"Deleting SemanticIndex for corpus {self.corpus_name} (ID: {self.corpus_id}) with model {self.model_name}"
        )

        manager = get_version_manager()
        resource_id = f"{self.corpus_id!s}:semantic:{self.model_name}"

        try:
            # Get the latest version to delete
            metadata = await manager.get_latest(
                resource_id=resource_id,
                resource_type=ResourceType.SEMANTIC,
            )

            if metadata and metadata.version_info:
                await manager.delete_version(
                    resource_id=resource_id,
                    resource_type=ResourceType.SEMANTIC,
                    version=metadata.version_info.version,
                )
                logger.info(
                    f"Successfully deleted SemanticIndex for corpus {self.corpus_name} (ID: {self.corpus_id})"
                )
            else:
                logger.warning(
                    f"No metadata found for SemanticIndex {resource_id}, may already be deleted"
                )
        except Exception as e:
            logger.error(f"Failed to delete SemanticIndex {resource_id}: {e}")
            raise RuntimeError(f"SemanticIndex deletion failed for {resource_id}: {e}") from e

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize index to dictionary for caching."""
        kwargs["exclude_none"] = True
        return super().model_dump(**kwargs)

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> SemanticIndex:
        """Deserialize index from cached dictionary."""
        return cls.model_validate(data)
