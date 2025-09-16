"""Semantic search models."""

from __future__ import annotations

from typing import Any

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

    # Index data (base64 encoded for JSON serialization)
    index_data: str = ""  # Base64 encoded FAISS index
    embeddings: str = ""  # Base64 encoded numpy embeddings

    # Vocabulary and mappings
    vocabulary: list[str] = Field(default_factory=list)
    lemmatized_vocabulary: list[str] = Field(default_factory=list)
    variant_mapping: dict[str, int] = Field(default_factory=dict)  # embedding idx -> lemma idx
    lemma_to_embeddings: dict[str, list[int]] = Field(
        default_factory=dict
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

    class Metadata(BaseVersionedData):
        """Minimal semantic metadata for versioning."""

        corpus_id: PydanticObjectId
        model_name: str

        def __init__(self, **data: Any) -> None:
            data.setdefault("resource_type", ResourceType.SEMANTIC)
            data.setdefault("namespace", CacheNamespace.SEMANTIC)
            super().__init__(**data)

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
        if not corpus_id and not corpus_name:
            raise ValueError("Either corpus_id or corpus_name must be provided")

        model_name = model_name or "all-MiniLM-L6-v2"
        manager = get_version_manager()

        # Build resource ID based on what we have
        if corpus_id:
            resource_id = f"{str(corpus_id)}:semantic:{model_name}"
        else:
            resource_id = f"{corpus_name}:semantic:{model_name}"

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
            corpus_id=corpus.id if hasattr(corpus, "id") else PydanticObjectId(),
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
        if existing and existing.vocabulary_hash == corpus.vocabulary_hash:
            logger.debug(
                f"Using cached semantic index for corpus '{corpus.corpus_name}' with model '{model_name}'"
            )
            return existing

        # Create new
        logger.info(f"Building new semantic index for corpus '{corpus.corpus_name}'")
        index = await cls.create(
            corpus=corpus,
            model_name=model_name,
            batch_size=batch_size,
        )

        # Save the new index
        await index.save(config)
        return index

    async def save(
        self,
        config: VersionConfig | None = None,
    ) -> None:
        """Save semantic index to versioned storage.

        Args:
            config: Version configuration
        """
        manager = get_version_manager()
        resource_id = f"{self.corpus_name}:semantic:{self.model_name}"

        # Save using version manager
        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEMANTIC,
            namespace=manager._get_namespace(ResourceType.SEMANTIC),
            content=self.model_dump(exclude_none=True),
            config=config or VersionConfig(),
            metadata={
                "vocabulary_hash": self.vocabulary_hash,
                "model_name": self.model_name,
                "num_embeddings": self.num_embeddings,
                "embedding_dimension": self.embedding_dimension,
            },
        )

        logger.debug(f"Saved semantic index for {resource_id}")

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize index to dictionary for caching."""
        return super().model_dump(exclude_none=True, **kwargs)

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> SemanticIndex:
        """Deserialize index from cached dictionary."""
        return cls.model_validate(data)
