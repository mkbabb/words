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
import hashlib

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
    corpus_uuid: str  # Stable UUID reference to corpus
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

    # CRITICAL FIX: Binary data storage field
    # This field holds base64-encoded embeddings and FAISS index data
    # It's excluded from serialization since it's stored externally via content_location
    # Previous implementation used object.__setattr__() which was fragile
    binary_data: dict[str, str] | None = Field(
        default=None,
        exclude=True,  # Never serialize to model_dump() - handled via external storage
        description="Base64-encoded embeddings and FAISS index data (stored externally)",
    )

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.SEMANTIC,
        default_namespace=CacheNamespace.SEMANTIC,
    ):
        """Minimal semantic metadata for versioning."""

        # CRITICAL: Override Beanie's default _class_id for polymorphism
        # Without this, Beanie uses "BaseVersionedData.Metadata" for all subclasses
        _class_id: ClassVar[str] = "SemanticIndex.Metadata"

        class Settings(BaseVersionedData.Settings):
            class_id = "_class_id"

        corpus_uuid: str
        model_name: str
        vocabulary_hash: str = ""
        embedding_dimension: int = 0
        index_type: str = "flat"

    @classmethod
    async def get(
        cls,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        model_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> SemanticIndex | None:
        """Get semantic index from versioned storage by ID or name.

        Args:
            corpus_uuid: Corpus stable UUID (preferred)
            corpus_name: Name of the corpus (fallback)
            model_name: Name of the embedding model
            config: Version configuration

        Returns:
            SemanticIndex instance or None if not found

        """
        # Skip cache entirely if force_rebuild is requested
        if config and config.force_rebuild:
            return None

        if not corpus_uuid and not corpus_name:
            raise ValueError("Either corpus_uuid or corpus_name must be provided")

        # Use constant for consistency
        from .constants import DEFAULT_SENTENCE_MODEL
        model_name = model_name or DEFAULT_SENTENCE_MODEL
        manager = get_version_manager()

        # Build resource ID using uuid (always stable across versions)
        if corpus_uuid:
            resource_id = f"{corpus_uuid}:semantic:{model_name}"
        else:
            # Lookup uuid from corpus_name
            from floridify.corpus.core import Corpus

            corpus = await Corpus.get(corpus_name=corpus_name, config=config)
            if not corpus or not corpus.corpus_uuid:
                logger.warning(f"Corpus '{corpus_name}' not found or missing uuid")
                return None
            resource_id = f"{corpus.corpus_uuid}:semantic:{model_name}"

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

        # CRITICAL FIX: Preserve binary_data from external storage
        # Now using proper field assignment instead of object.__setattr__()
        if "binary_data" in content:
            index.binary_data = content["binary_data"]

        # Ensure the index ID is set from metadata
        if metadata.id:
            index.index_id = metadata.id
        return index

    @classmethod
    async def create(
        cls,
        corpus: Corpus,
        model_name: str | None = None,
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
        from .constants import DEFAULT_BATCH_SIZE, DEFAULT_SENTENCE_MODEL, MODEL_BATCH_SIZES

        # Use constant for consistency
        model_name = model_name or DEFAULT_SENTENCE_MODEL

        logger.info(f"Creating semantic index for '{corpus.corpus_name}' with model '{model_name}'")

        # Auto-select batch size if not provided
        if batch_size is None:
            batch_sizes: dict[str, int] = MODEL_BATCH_SIZES  # type: ignore
            batch_size = batch_sizes.get(model_name, DEFAULT_BATCH_SIZE)

        if not corpus.corpus_uuid:
            raise ValueError("Corpus must have corpus_uuid set")

        return cls(
            corpus_uuid=corpus.corpus_uuid,
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
        model_name: str | None = None,
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
        # Use constant for consistency
        from .constants import DEFAULT_SENTENCE_MODEL
        model_name = model_name or DEFAULT_SENTENCE_MODEL

        # Try to get existing using corpus ID if available, otherwise name
        existing = await cls.get(
            corpus_uuid=corpus.corpus_uuid,
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
        corpus_uuid: str | None = None,
        binary_data: dict[str, str] | None = None,
    ) -> None:
        """Save semantic index to versioned storage.

        Large binary data (embeddings, FAISS index) is automatically stored
        externally via the filesystem cache for indices > 16MB.

        Args:
            config: Version configuration
            corpus_uuid: Stable UUID of the associated corpus
            binary_data: Optional dict with 'embeddings' and 'index_data' keys
                        containing base64-encoded binary data

        """
        manager = get_version_manager()
        # Use corpus_uuid for consistency with get() method
        cid = corpus_uuid or self.corpus_uuid
        resource_id = f"{cid}:semantic:{self.model_name}"

        # CRITICAL FIX: Prepare content WITHOUT binary_data for manager.save()
        # binary_data will be added to external storage AFTER metadata is saved
        # This prevents JSON encoding 1290MB of data which causes hang
        content = self.model_dump(exclude_none=True)

        # Store binary_data separately to avoid JSON encoding in manager.save()
        binary_data_to_store = binary_data

        try:
            # Save metadata using version manager (without binary_data)
            versioned = await manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.SEMANTIC,
                namespace=manager._get_namespace(ResourceType.SEMANTIC),
                content=content,
                config=config or VersionConfig(),
                metadata={
                    "corpus_uuid": corpus_uuid or self.corpus_uuid,
                    "model_name": self.model_name,
                    "vocabulary_hash": self.vocabulary_hash,
                    "embedding_dimension": self.embedding_dimension,
                    "index_type": self.index_type,
                    # Extra metadata (not in Metadata model)
                    "num_embeddings": self.num_embeddings,
                },
            )

            # CRITICAL FIX: Store binary_data separately after metadata is saved
            # For large compressed bytes, store directly to cache using pickle
            # This avoids base64 encoding which creates massive strings (392MB -> 523MB)
            if binary_data_to_store:
                from ...caching.core import get_global_cache
                from ...caching.manager import _generate_cache_key
                from ...caching.models import ContentLocation, StorageType

                # Write large binary data directly to cache without JSON/base64 encoding
                cache = await get_global_cache()

                # Generate cache key for this content
                cache_key = _generate_cache_key(
                    versioned.resource_type,
                    versioned.resource_id,
                    "content",
                    versioned.version_info.data_hash[:8]
                )

                # Merge binary data with content - diskcache will pickle the bytes directly
                content_with_binary = {**content, "binary_data": binary_data_to_store}

                # Ensure namespace is CacheNamespace enum
                namespace = versioned.namespace
                if isinstance(namespace, str):
                    from ...caching.models import CacheNamespace
                    namespace = CacheNamespace(namespace)

                logger.info(f"Storing large binary data to cache for {resource_id} (pickle will handle bytes)")
                await cache.set(
                    namespace=namespace,
                    key=cache_key,
                    value=content_with_binary,
                    ttl_override=versioned.ttl,
                )

                # Estimate size (rough calculation to avoid full JSON encoding)
                binary_size = sum(
                    len(v) if isinstance(v, bytes) else len(str(v))
                    for v in binary_data_to_store.values()
                )
                content_size = binary_size + 1000  # Add overhead estimate

                versioned.content_location = ContentLocation(
                    cache_namespace=versioned.namespace,
                    cache_key=cache_key,
                    storage_type=StorageType.CACHE,
                    size_bytes=content_size,
                    checksum="skip-large-binary-data",  # Skip checksum for large data
                )
                versioned.content_inline = None

                # Save the updated versioned object with content_location
                await versioned.save()

            # Verify save succeeded by attempting to retrieve
            saved = await self.get(corpus_uuid=cid, model_name=self.model_name, config=config)
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
            ValueError: If corpus_uuid is not set
        """
        if not self.corpus_uuid:
            logger.warning("Cannot delete semantic index without corpus_uuid")
            raise ValueError("Cannot delete semantic index without corpus_uuid")

        logger.info(
            f"Deleting SemanticIndex for corpus {self.corpus_name} (uuid: {self.corpus_uuid}) with model {self.model_name}"
        )

        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:semantic:{self.model_name}"

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
                    f"Successfully deleted SemanticIndex for corpus {self.corpus_name} (uuid: {self.corpus_uuid})"
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


