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
from .constants import DEFAULT_BATCH_SIZE, DEFAULT_SENTENCE_MODEL, MATRYOSHKA_DIM, MODEL_BATCH_SIZES

logger = get_logger(__name__)

__all__ = [
    "SemanticIndex",
]


def _build_resource_id(corpus_uuid: str, model_name: str, vocab_hash: str) -> str:
    """Build a consistent resource ID for semantic indices.

    Includes MATRYOSHKA_DIM so old (full-dim) and new (truncated) indices coexist.
    """
    vocab_hash_short = vocab_hash[:8] if vocab_hash else "none"
    dim_suffix = f":d{MATRYOSHKA_DIM}" if MATRYOSHKA_DIM else ""
    return f"{corpus_uuid}:semantic:{model_name}:{vocab_hash_short}{dim_suffix}"


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

    # Vocabulary reference (hash check instead of duplicating full lists from Corpus)
    # Full vocabulary and lemmatized_vocabulary are loaded from Corpus when needed
    variant_mapping: dict[int, int] = Field(
        default_factory=dict
    )  # embedding idx -> lemma idx (int keys)
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

    # Opaque binary payload — never serialized through model_dump.
    # Holds {"embeddings_bytes": bytes, "index_bytes": bytes}. The version
    # manager pickles this into GridFS via the binary_payload= hook.
    binary_data: dict[str, bytes] | None = Field(
        default=None,
        exclude=True,
        description="Embeddings and FAISS index bytes stored externally via GridFS",
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
        corpus: Corpus | None = None,
    ) -> SemanticIndex | None:
        """Get semantic index from versioned storage by ID or name.

        Args:
            corpus_uuid: Corpus stable UUID (preferred)
            corpus_name: Name of the corpus (fallback)
            model_name: Name of the embedding model
            config: Version configuration
            corpus: Optional corpus instance to avoid database lookup

        Returns:
            SemanticIndex instance or None if not found

        """
        # Skip cache entirely if force_rebuild is requested
        if config and config.force_rebuild:
            return None

        if not corpus_uuid and not corpus_name and not corpus:
            raise ValueError("Either corpus_uuid, corpus_name, or corpus must be provided")

        # Use constant for consistency
        model_name = model_name or DEFAULT_SENTENCE_MODEL
        manager = get_version_manager()

        # Use provided corpus or load from database
        if not corpus:
            if corpus_uuid:
                from ...corpus.manager import get_tree_corpus_manager

                corpus_manager = get_tree_corpus_manager()
                corpus = await corpus_manager.get_corpus(corpus_uuid=corpus_uuid, config=config)
            else:
                from ...corpus.manager import get_tree_corpus_manager

                corpus_manager = get_tree_corpus_manager()
                corpus = await corpus_manager.get_corpus(corpus_name=corpus_name, config=config)

            if not corpus or not corpus.corpus_uuid:
                logger.warning(f"Corpus not found: uuid={corpus_uuid}, name={corpus_name}")
                return None

        resource_id = _build_resource_id(corpus.corpus_uuid, model_name, corpus.vocabulary_hash)

        # Get the latest semantic index metadata
        metadata: SemanticIndex.Metadata | None = await manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEMANTIC,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

        if not metadata:
            return None

        # Load content from metadata, respecting config.use_cache.
        # When binary_payload was used at write time, the manager-driven
        # GridFS path returns a dict with the "binary_data" key already
        # populated — we pop it off before model_validate so pydantic
        # doesn't have to coerce raw bytes.
        content = await get_versioned_content(metadata, config=config)
        if not content:
            return None

        binary_data = content.pop("binary_data", None) if isinstance(content, dict) else None

        index = cls.model_validate(content)
        if binary_data is not None:
            index.binary_data = binary_data

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
        model_name = model_name or DEFAULT_SENTENCE_MODEL

        # Try to get existing using corpus ID if available, otherwise name
        existing = await cls.get(
            corpus_uuid=corpus.corpus_uuid,
            corpus_name=corpus.corpus_name,
            model_name=model_name,
            config=config,
            corpus=corpus,
        )

        # Check embeddings exist AND match the current corpus.
        # Reject cached indices with 0 embeddings (corrupted/incomplete builds)
        # or with a stale vocabulary hash (different aggregation).
        # Note: num_embeddings matches LEMMATIZED vocabulary (often ~60% of full vocab),
        # so we compare against the hash, not the count.
        lemma_size = len(corpus.lemmatized_vocabulary) if corpus.lemmatized_vocabulary else 0
        vocab_size = len(corpus.vocabulary) if corpus.vocabulary else 0
        if existing:
            logger.info(
                f"Semantic cache check for '{corpus.corpus_name}': "
                f"cached_hash={existing.vocabulary_hash[:8]}, corpus_hash={corpus.vocabulary_hash[:8]}, "
                f"cached_embeddings={existing.num_embeddings}, corpus_vocab={vocab_size}, lemmas={lemma_size}"
            )
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
        binary_data: dict[str, bytes] | None = None,
    ) -> None:
        """Save semantic index to versioned storage.

        The metadata document is small (statistics, mappings, model config).
        The opaque binary blob (embeddings + FAISS index bytes) is handed
        to the version manager via the ``binary_payload`` hook, which
        pickles it into GridFS and warms the L1/L2 cache in one shot.

        Args:
            config: Version configuration.
            corpus_uuid: Stable UUID of the associated corpus.
            binary_data: ``{"embeddings_bytes": bytes, "index_bytes": bytes}``.
                Falls back to ``self.binary_data`` if not provided.
        """
        manager = get_version_manager()
        cid = corpus_uuid or self.corpus_uuid
        resource_id = _build_resource_id(cid, self.model_name, self.vocabulary_hash)

        # `binary_data` field is excluded from model_dump, so the metadata
        # dict stays small even when self.binary_data is populated.
        content = self.model_dump(exclude_none=True)
        payload = binary_data if binary_data is not None else self.binary_data

        try:
            await manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.SEMANTIC,
                namespace=manager._get_namespace(ResourceType.SEMANTIC),
                content=content,
                config=config or VersionConfig(),
                metadata={
                    "corpus_uuid": cid,
                    "model_name": self.model_name,
                    "vocabulary_hash": self.vocabulary_hash,
                    "embedding_dimension": self.embedding_dimension,
                    "index_type": self.index_type,
                    "num_embeddings": self.num_embeddings,
                },
                binary_payload=payload,
            )
            logger.info(f"Successfully saved semantic index for {resource_id}")
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
        resource_id = _build_resource_id(self.corpus_uuid, self.model_name, self.vocabulary_hash)

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
