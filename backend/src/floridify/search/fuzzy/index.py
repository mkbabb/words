"""FuzzyIndex active-record model for fuzzy search index persistence.

Persists the BK-tree, phonetic index, suffix array, and trigram index
as a single versioned unit using the existing caching infrastructure.
Keyed by corpus_uuid + vocabulary_hash for cache invalidation.
"""

from __future__ import annotations

import base64
import pickle
import time
from typing import Annotated, Any, ClassVar

from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_serializer, field_validator

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


class FuzzyIndex(BaseModel):
    """Persisted fuzzy search structures.

    Stores serialized BK-tree, phonetic index, and suffix array alongside
    the trigram index data, all keyed by vocabulary_hash for invalidation.
    """

    # Identification
    index_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    corpus_uuid: str
    corpus_name: str
    vocabulary_hash: str

    # Serialized binary data (pickle'd, base64-encoded for JSON storage)
    bk_tree_bytes: bytes | None = None
    phonetic_index_bytes: bytes | None = None
    suffix_array_bytes: bytes | None = None

    # Statistics
    vocabulary_size: int = 0
    build_time_seconds: float = 0.0

    # Base64 encode/decode for JSON serialization (versioned storage uses JSON)
    @field_serializer("bk_tree_bytes", "phonetic_index_bytes", "suffix_array_bytes")
    @classmethod
    def _encode_bytes(cls, v: bytes | None) -> str | None:
        return base64.b85encode(v).decode("ascii") if v else None

    @field_validator("bk_tree_bytes", "phonetic_index_bytes", "suffix_array_bytes", mode="before")
    @classmethod
    def _decode_bytes(cls, v: Any) -> bytes | None:
        if v is None:
            return None
        if isinstance(v, bytes):
            return v
        if isinstance(v, str):
            return base64.b85decode(v.encode("ascii"))
        return v

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.SEARCH,
        default_namespace=CacheNamespace.SEARCH,
    ):
        """Fuzzy index metadata for versioning."""

        _class_id: ClassVar[str] = "FuzzyIndex.Metadata"

        class Settings(BaseVersionedData.Settings):
            class_id = "_class_id"

        corpus_uuid: str
        vocabulary_hash: str = ""

    @classmethod
    async def get(
        cls,
        corpus_uuid: str,
        config: VersionConfig | None = None,
    ) -> FuzzyIndex | None:
        """Load fuzzy index from versioned storage."""
        effective_config = config or VersionConfig()
        if effective_config.force_rebuild:
            effective_config = effective_config.model_copy()
            effective_config.use_cache = False

        manager = get_version_manager()
        resource_id = f"{corpus_uuid}:fuzzy"

        metadata = await manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH,
            use_cache=effective_config.use_cache,
            config=effective_config,
        )

        if not metadata:
            return None

        content = await get_versioned_content(metadata, config=effective_config)
        if not content:
            return None

        index = cls.model_validate(content)
        if metadata.id:
            index.index_id = metadata.id
        return index

    @classmethod
    def create(cls, corpus: Corpus) -> FuzzyIndex:
        """Build fuzzy index structures from corpus.

        Builds BK-tree, phonetic index, and suffix array, then
        serializes them to bytes for storage.
        """
        from .bk_tree import BKTree
        from ..phonetic.index import PhoneticIndex
        from .suffix_array import SuffixArray

        if not corpus.corpus_uuid:
            raise ValueError("Corpus must have corpus_uuid set")

        start_time = time.perf_counter()
        vocab = corpus.vocabulary

        # Build and serialize BK-tree
        bk_tree = BKTree.build(vocab)
        bk_tree_bytes = pickle.dumps(bk_tree) if bk_tree else None

        # Build and serialize phonetic index
        phonetic_index = PhoneticIndex(vocab)
        phonetic_index_bytes = pickle.dumps(phonetic_index)

        # Build and serialize suffix array
        suffix_array = SuffixArray(vocab)
        suffix_array_bytes = pickle.dumps(suffix_array)

        build_time = time.perf_counter() - start_time
        logger.info(
            f"Built FuzzyIndex for '{corpus.corpus_name}': "
            f"BK={len(bk_tree_bytes) // 1024 if bk_tree_bytes else 0}KB, "
            f"phonetic={len(phonetic_index_bytes) // 1024}KB, "
            f"suffix={len(suffix_array_bytes) // 1024}KB, "
            f"time={build_time:.1f}s"
        )

        return cls(
            corpus_uuid=corpus.corpus_uuid,
            corpus_name=corpus.corpus_name,
            vocabulary_hash=corpus.vocabulary_hash,
            bk_tree_bytes=bk_tree_bytes,
            phonetic_index_bytes=phonetic_index_bytes,
            suffix_array_bytes=suffix_array_bytes,
            vocabulary_size=len(vocab),
            build_time_seconds=build_time,
        )

    def deserialize(
        self,
    ) -> tuple[Any | None, Any | None, Any | None]:
        """Deserialize stored structures back to runtime objects.

        Returns:
            Tuple of (BKTree | None, PhoneticIndex | None, SuffixArray | None)
        """
        bk_tree = pickle.loads(self.bk_tree_bytes) if self.bk_tree_bytes else None
        phonetic_index = (
            pickle.loads(self.phonetic_index_bytes)
            if self.phonetic_index_bytes
            else None
        )
        suffix_array = (
            pickle.loads(self.suffix_array_bytes)
            if self.suffix_array_bytes
            else None
        )
        return bk_tree, phonetic_index, suffix_array

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        config: VersionConfig | None = None,
    ) -> FuzzyIndex:
        """Get cached fuzzy index or build a new one.

        Uses vocabulary_hash for cache invalidation — if the hash matches,
        the cached structures are still valid.
        """
        if corpus.corpus_uuid:
            existing = await cls.get(corpus.corpus_uuid, config)
            if existing and existing.vocabulary_hash == corpus.vocabulary_hash:
                logger.debug(
                    f"Using cached fuzzy index for '{corpus.corpus_name}'"
                )
                return existing

        logger.info(f"Building new fuzzy index for '{corpus.corpus_name}'")
        index = cls.create(corpus)
        await index.save(config)
        return index

    async def save(self, config: VersionConfig | None = None) -> None:
        """Save fuzzy index to versioned storage."""
        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:fuzzy"

        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH,
            namespace=manager._get_namespace(ResourceType.SEARCH),
            content=self.model_dump(mode="json"),
            config=config or VersionConfig(),
            metadata={
                "corpus_uuid": self.corpus_uuid,
            },
        )

        logger.info(f"Saved fuzzy index for {resource_id}")

    async def delete(self) -> None:
        """Delete fuzzy index from versioned storage."""
        if not self.corpus_uuid:
            raise ValueError("Cannot delete fuzzy index without corpus_uuid")

        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:fuzzy"

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
            logger.info(f"Deleted FuzzyIndex for '{self.corpus_name}'")


__all__ = ["FuzzyIndex"]
