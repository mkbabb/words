"""TrieIndex active-record model for trie-based search index persistence."""

from __future__ import annotations

import time
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
from ..utils.logging import get_logger

logger = get_logger(__name__)


class TrieIndex(BaseModel):
    """Complete trie index data model for TrieSearch.

    Contains all trie data, frequencies, and search structures.
    """

    # Index identification
    index_id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    corpus_uuid: str  # Stable UUID reference to corpus
    corpus_name: str
    vocabulary_hash: str

    # Trie data - sorted word list for marisa-trie
    trie_data: list[str] = Field(default_factory=list)

    # Word frequency mapping for ranking
    word_frequencies: dict[str, int] = Field(default_factory=dict)

    # Original vocabulary for diacritic preservation
    original_vocabulary: list[str] = Field(default_factory=list)
    normalized_to_original: dict[str, str] = Field(default_factory=dict)

    # Bloom filter persistence
    bloom_bits: bytes | None = None
    bloom_num_bits: int = 0
    bloom_num_hashes: int = 0
    bloom_count: int = 0
    bloom_error_rate: float = 0.01

    # Statistics
    word_count: int = 0
    max_frequency: int = 0
    build_time_seconds: float = 0.0

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.TRIE,
        default_namespace=CacheNamespace.TRIE,
    ):
        """Minimal trie metadata for versioning."""

        # CRITICAL: Override Beanie's default _class_id for polymorphism
        _class_id: ClassVar[str] = "TrieIndex.Metadata"

        class Settings(BaseVersionedData.Settings):
            class_id = "_class_id"

        corpus_uuid: str
        vocabulary_hash: str = ""

    @classmethod
    async def get(
        cls,
        corpus_uuid: str | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> TrieIndex | None:
        """Get trie index from versioned storage by stable ID or name.

        Args:
            corpus_uuid: Corpus stable UUID (preferred)
            corpus_name: Name of the corpus (fallback)
            config: Version configuration

        Returns:
            TrieIndex instance or None if not found

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
            resource_id = f"{corpus_uuid}:trie"
        else:
            # Lookup uuid from corpus_name
            from ..corpus.manager import get_tree_corpus_manager

            corpus_manager = get_tree_corpus_manager()
            corpus = await corpus_manager.get_corpus(
                corpus_name=corpus_name, config=effective_config
            )
            if not corpus or not corpus.corpus_uuid:
                return None
            resource_id = f"{corpus.corpus_uuid}:trie"

        # Get the latest trie index metadata
        metadata: TrieIndex.Metadata | None = await manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.TRIE,
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
    ) -> TrieIndex:
        """Create new trie index from corpus.

        Args:
            corpus: Corpus containing vocabulary and frequencies

        Returns:
            TrieIndex instance with built trie data

        """

        from .utils import calculate_default_frequency

        start_time = time.perf_counter()

        # Build frequency map
        word_frequencies = {}
        max_frequency = 0
        # word_frequencies is typed as dict[str, int] with default_factory in Corpus
        frequencies = corpus.word_frequencies

        for word in corpus.vocabulary:
            if frequencies:
                freq = frequencies.get(word, calculate_default_frequency(word))
            else:
                freq = calculate_default_frequency(word)
            word_frequencies[word] = freq
            max_frequency = max(max_frequency, freq)

        # Build normalized to original mapping using the corpus's index-based mapping
        # (vocabulary is sorted; original_vocabulary is insertion-order — zip is WRONG)
        normalized_to_original = {}
        for norm_idx, orig_indices in corpus.normalized_to_original_indices.items():
            if 0 <= norm_idx < len(corpus.vocabulary) and orig_indices:
                norm_word = corpus.vocabulary[norm_idx]
                orig_word = corpus.original_vocabulary[orig_indices[0]]
                normalized_to_original[norm_word] = orig_word

        build_time = time.perf_counter() - start_time

        if not corpus.corpus_uuid:
            raise ValueError("Corpus must have corpus_uuid set")

        return cls(
            corpus_uuid=corpus.corpus_uuid,
            corpus_name=corpus.corpus_name,
            vocabulary_hash=corpus.vocabulary_hash,
            trie_data=sorted(corpus.vocabulary),  # Sorted for marisa-trie
            word_frequencies=word_frequencies,
            original_vocabulary=corpus.original_vocabulary,
            normalized_to_original=normalized_to_original,
            word_count=len(corpus.vocabulary),
            max_frequency=max_frequency,
            build_time_seconds=build_time,
        )

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        config: VersionConfig | None = None,
    ) -> TrieIndex:
        """Get existing trie index or create new one.

        Args:
            corpus: Corpus containing vocabulary
            config: Version configuration

        Returns:
            TrieIndex instance

        """
        # Try to get existing using corpus uuid if available, otherwise name
        existing = await cls.get(
            corpus_uuid=corpus.corpus_uuid,
            corpus_name=corpus.corpus_name,
            config=config,
        )
        if existing and existing.vocabulary_hash == corpus.vocabulary_hash:
            logger.debug(f"Using cached trie index for corpus '{corpus.corpus_name}'")
            return existing

        # Create new
        logger.info(f"Building new trie index for corpus '{corpus.corpus_name}'")
        index = await cls.create(corpus)

        # Save the new index
        await index.save(config)
        return index

    async def save(
        self,
        config: VersionConfig | None = None,
    ) -> None:
        """Save trie index to versioned storage.

        Args:
            config: Version configuration

        Raises:
            RuntimeError: If save fails

        """
        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:trie"

        await manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.TRIE,
            namespace=manager._get_namespace(ResourceType.TRIE),
            content=self.model_dump(mode="json"),
            config=config or VersionConfig(),
            metadata={
                "corpus_uuid": self.corpus_uuid,
            },
        )

        logger.info(f"Saved trie index for {resource_id}")

    async def delete(self) -> None:
        """Delete trie index from versioned storage.

        Raises:
            ValueError: If corpus_uuid is not set
        """
        if not self.corpus_uuid:
            logger.warning("Cannot delete trie index without corpus_uuid")
            raise ValueError("Cannot delete trie index without corpus_uuid")

        logger.info(f"Deleting TrieIndex for corpus {self.corpus_name} (uuid: {self.corpus_uuid})")

        manager = get_version_manager()
        resource_id = f"{self.corpus_uuid}:trie"

        try:
            # Get the latest version to delete
            metadata = await manager.get_latest(
                resource_id=resource_id,
                resource_type=ResourceType.TRIE,
            )

            if metadata and metadata.version_info:
                await manager.delete_version(
                    resource_id=resource_id,
                    resource_type=ResourceType.TRIE,
                    version=metadata.version_info.version,
                )
                logger.info(
                    f"Successfully deleted TrieIndex for corpus {self.corpus_name} (uuid: {self.corpus_uuid})"
                )
            else:
                logger.warning(
                    f"No metadata found for TrieIndex {resource_id}, may already be deleted"
                )
        except Exception as e:
            logger.error(f"Failed to delete TrieIndex {resource_id}: {e}")
            raise RuntimeError(f"TrieIndex deletion failed for {resource_id}: {e}") from e


__all__ = [
    "TrieIndex",
]
