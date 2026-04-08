"""FuzzyIndex — persisted ``ffuzzy`` Rust index, stored as an opaque blob.

The index blob is a single self-contained byte buffer produced by
``ffuzzy.Index.to_bytes()``. The metadata document is small (a few
hundred bytes); the binary payload (ffuzzy bytes + pickled suffix
array) is stored externally via :class:`VersionedDataManager`'s
``binary_payload`` hook, which pickles it into GridFS in a single
shot — no JSON serialization, no double-pass, no consumer-side GridFS
plumbing.
"""

from __future__ import annotations

import pickle
import time
from typing import Any, ClassVar

import ffuzzy
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


class FuzzyIndex(BaseModel):
    """Persisted ffuzzy index (opaque Rust blob).

    The binary payload (``binary_data``) is excluded from
    ``model_dump`` so the version manager only sees a small metadata
    document. ``save()`` hands the bytes to the version manager via
    its ``binary_payload`` hook, which routes them to GridFS in one
    atomic write. ``get()`` reverses the process — the manager
    rehydrates the dict from GridFS and we pop the ``binary_data``
    key off before validating the metadata.
    """

    # Identification
    index_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    corpus_uuid: str
    corpus_name: str
    vocabulary_hash: str

    # Statistics
    vocabulary_size: int = 0
    build_time_seconds: float = 0.0
    ffuzzy_size_bytes: int = 0
    suffix_array_size_bytes: int = 0

    # Binary payload — never serialized through model_dump.
    # Holds {"ffuzzy": bytes, "suffix_array": bytes}.
    binary_data: dict[str, bytes] | None = Field(
        default=None,
        exclude=True,
        description="Opaque binary payload stored externally via GridFS",
    )

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

    # ── Read path ────────────────────────────────────────────────

    @classmethod
    async def get(
        cls,
        corpus_uuid: str,
        config: VersionConfig | None = None,
    ) -> FuzzyIndex | None:
        """Load fuzzy index from versioned storage.

        Loads the metadata document, then pops the binary payload off
        the dict the manager rehydrated from GridFS. Returns ``None`` if
        no version exists.
        """
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

        binary_data = content.pop("binary_data", None) if isinstance(content, dict) else None

        index = cls.model_validate(content)
        if binary_data is not None:
            index.binary_data = binary_data
        if metadata.id:
            index.index_id = metadata.id
        return index

    def deserialize(
        self,
    ) -> tuple[Any | None, Any | None, Any | None]:
        """Deserialize stored structures back to runtime objects.

        Returns a 3-tuple matching the legacy pipeline shape:
        ``(ffuzzy_index, None, suffix_array)``. The ``None`` slot used
        to hold the Python phonetic index — phonetic now lives inside
        the ffuzzy crate.
        """
        if self.binary_data is None:
            return None, None, None

        ffuzzy_bytes = self.binary_data.get("ffuzzy")
        suffix_array_bytes = self.binary_data.get("suffix_array")

        ffuzzy_index: Any = None
        if ffuzzy_bytes:
            ffuzzy_index = ffuzzy.Index.from_bytes(ffuzzy_bytes)

        suffix_array = pickle.loads(suffix_array_bytes) if suffix_array_bytes else None
        return ffuzzy_index, None, suffix_array

    # ── Write path ───────────────────────────────────────────────

    @classmethod
    def create(cls, corpus: Corpus) -> FuzzyIndex:
        """Build a new ffuzzy index + suffix array from a corpus.

        Builds the full SymSpell ``k=2`` hybrid. The resulting binary
        payload (potentially hundreds of MB) is opaque to the model —
        :meth:`save` hands it to the version manager which routes it
        through GridFS without ever touching JSON.
        """
        from .suffix_array import SuffixArray

        if not corpus.corpus_uuid:
            raise ValueError("Corpus must have corpus_uuid set")

        start_time = time.perf_counter()
        vocab = corpus.vocabulary

        rust_index = ffuzzy.Index.build(vocab)
        ffuzzy_bytes = rust_index.to_bytes()

        # Build and pickle the suffix array (Python).
        suffix_array = SuffixArray(vocab)
        suffix_array_bytes = pickle.dumps(suffix_array)

        build_time = time.perf_counter() - start_time
        logger.info(
            f"Built FuzzyIndex (ffuzzy) for '{corpus.corpus_name}': "
            f"ffuzzy={len(ffuzzy_bytes) // 1024}KB, "
            f"suffix={len(suffix_array_bytes) // 1024}KB, "
            f"time={build_time:.1f}s"
        )

        return cls(
            corpus_uuid=corpus.corpus_uuid,
            corpus_name=corpus.corpus_name,
            vocabulary_hash=corpus.vocabulary_hash,
            vocabulary_size=len(vocab),
            build_time_seconds=build_time,
            ffuzzy_size_bytes=len(ffuzzy_bytes),
            suffix_array_size_bytes=len(suffix_array_bytes),
            binary_data={
                "ffuzzy": ffuzzy_bytes,
                "suffix_array": suffix_array_bytes,
            },
        )

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        config: VersionConfig | None = None,
    ) -> FuzzyIndex:
        """Get cached fuzzy index or build a new one.

        A cached entry is reused only when all three hold:

        1. `vocabulary_hash` matches the current corpus.
        2. `binary_data["ffuzzy"]` is present (not a legacy-schema row).
        3. The ffuzzy blob round-trips through `ffuzzy.Index.from_bytes`
           successfully — the Rust side owns its own schema version and
           bincode layout, and when those shift (crate upgrade,
           `SCHEMA_VERSION` bump) the cached blob becomes structurally
           unreadable. Validating at get-time treats those as cache
           misses cleanly and saves the rebuilt blob so the next
           startup hits a warm cache.
        """
        if corpus.corpus_uuid:
            existing = await cls.get(corpus.corpus_uuid, config)
            if (
                existing
                and existing.vocabulary_hash == corpus.vocabulary_hash
                and existing.binary_data is not None
                and existing.binary_data.get("ffuzzy")
            ):
                try:
                    ffuzzy.Index.from_bytes(existing.binary_data["ffuzzy"])
                except Exception as e:
                    logger.info(
                        f"Cached FuzzyIndex for '{corpus.corpus_name}' "
                        f"failed ffuzzy deserialization ({e}); rebuilding."
                    )
                else:
                    logger.debug(
                        f"Using cached fuzzy index for '{corpus.corpus_name}'"
                    )
                    return existing
            elif existing:
                logger.info(
                    f"Cached FuzzyIndex for '{corpus.corpus_name}' is stale "
                    f"or missing ffuzzy payload; rebuilding."
                )

        logger.info(f"Building new fuzzy index for '{corpus.corpus_name}'")
        index = cls.create(corpus)
        await index.save(config)
        return index

    async def save(self, config: VersionConfig | None = None) -> None:
        """Save the fuzzy index via the version manager.

        The metadata document is small. The opaque binary blob
        (ffuzzy bytes + pickled suffix array) is handed to the manager
        through the ``binary_payload`` hook, which pickles it into
        GridFS and warms the L1/L2 cache in one shot.
        """
        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:fuzzy"

        # binary_data is excluded from model_dump, so the metadata dict
        # stays small even when self.binary_data holds hundreds of MB.
        content = self.model_dump(exclude_none=True)

        if not self.binary_data:
            logger.warning(f"FuzzyIndex.save: no binary_data for {resource_id}")

        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.SEARCH,
            namespace=manager._get_namespace(ResourceType.SEARCH),
            content=content,
            config=config or VersionConfig(),
            metadata={
                "corpus_uuid": self.corpus_uuid,
                "vocabulary_hash": self.vocabulary_hash,
            },
            binary_payload=self.binary_data,
        )

        if self.binary_data:
            binary_mb = sum(len(v) for v in self.binary_data.values()) / (1024 * 1024)
            logger.info(f"Saved fuzzy index for {resource_id} (binary={binary_mb:.1f}MB)")

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
