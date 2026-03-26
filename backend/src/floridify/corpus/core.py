"""Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic and base corpus source configuration.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, ClassVar

import coolname
import numpy as np
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_validator

from ..caching.manager import get_version_manager
from ..caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ContentLocation,
    ResourceType,
    VersionInfo,
)
import unicodedata

from ..models.base import Language
from ..text.normalize import batch_normalize
from ..utils.logging import get_logger
from ..search.fuzzy.candidates import (
    LengthBuckets,
    TrigramIndex,
    build_candidate_index,
    get_candidates,
    get_substring_candidates,
    word_trigrams,
)
from .models import CorpusType
from .utils import get_vocabulary_hash
from .vocabulary import (
    create_lemmatization_maps,
    filter_words,
    merge_words,
    normalize_vocabulary,
    rebuild_original_indices,
)

logger = get_logger(__name__)


class Corpus(BaseModel):
    """Represents a corpus of vocabulary with semantic and search capabilities.

    Now uses PydanticObjectId as primary key with optional corpus_name that
    defaults to a generated slug using coolname.
    """

    # Identity
    corpus_name: str = ""  # Optional name, will be generated if empty
    corpus_type: CorpusType = CorpusType.LEXICON
    language: Language = Language.ENGLISH

    @field_validator("corpus_type", mode="before")
    @classmethod
    def validate_corpus_type(cls, v):
        """Handle both enum objects and string values."""
        if isinstance(v, CorpusType):
            return v  # Already an enum, return as-is
        if isinstance(v, str):
            return CorpusType(v)  # Convert string to enum
        return v

    @field_validator("language", mode="before")
    @classmethod
    def validate_language(cls, v):
        """Handle both enum objects and string values."""
        if isinstance(v, Language):
            return v  # Already an enum, return as-is
        if isinstance(v, str):
            return Language(v)  # Convert string to enum
        return v

    # Core vocabulary data - sorted normalized vocabulary
    vocabulary: list[str]
    original_vocabulary: list[str] = Field(
        default_factory=list,
        description="Original forms of words",
    )

    # Normalized to original indices (for mapping back to original forms)
    normalized_to_original_indices: dict[int, list[int]] = Field(default_factory=dict)
    vocabulary_to_index: dict[str, int] = Field(default_factory=dict)

    # Lemmatization maps
    lemmatized_vocabulary: list[str] = Field(default_factory=list)
    lemma_text_to_index: dict[str, int] = Field(default_factory=dict)
    word_to_lemma_indices: dict[int, int] = Field(default_factory=dict)
    lemma_to_word_indices: dict[int, list[int]] = Field(default_factory=dict)

    # Trigram inverted index for fuzzy candidate selection (transient, rebuilt on load).
    # Typed as Any to accept both numpy arrays (runtime) and plain lists (from old cached data).
    # Always rebuilt via _build_candidate_index() after load.
    trigram_index: Any = Field(default_factory=dict, exclude=True)
    length_buckets: Any = Field(default_factory=dict, exclude=True)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    vocabulary_stats: dict[str, Any] = Field(default_factory=dict)
    vocabulary_hash: str = ""
    # Sources
    sources: list[str] = Field(default_factory=list)
    total_word_count: int = 0
    last_updated: float = Field(default_factory=time.time)

    # Tree structure references
    corpus_id: PydanticObjectId | None = None  # MongoDB _id (changes with versions)
    corpus_uuid: str | None = None  # Immutable UUID that never changes
    parent_uuid: str | None = None  # Parent's UUID
    child_uuids: list[str] = Field(default_factory=list)  # Children's UUIDs
    is_master: bool = False

    # Semantic policy (explicit setting + computed effective state)
    semantic_enabled_explicit: bool | None = None
    semantic_enabled_effective: bool = False
    semantic_model: str | None = None

    # Word frequency data
    word_frequencies: dict[str, int] = Field(default_factory=dict)

    @property
    def unique_word_count(self) -> int:
        """Computed from vocabulary length."""
        return len(self.vocabulary)

    # Version tracking (populated from metadata when loaded)
    version_info: VersionInfo | None = None
    _metadata_id: PydanticObjectId | None = None  # Internal reference to metadata document

    model_config = {
        "arbitrary_types_allowed": True,
        "ser_json_inf_nan": "constants",
        # "use_enum_values": True,  # REMOVED: Let Pydantic keep enum objects
        # Field validators (lines 45-63) handle enum/string conversion as needed
    }

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.CORPUS,
        default_namespace=CacheNamespace.CORPUS,
    ):
        """Corpus metadata for versioned persistence.

        Note: This Metadata class serves as the persistence layer for corpus versioning.
        It contains identification and tree structure fields needed to reconstruct
        the corpus state from storage. This is different from pure cache validation
        metadata in other classes like TrieIndex.Metadata.
        """

        # CRITICAL: Override Beanie's default _class_id to use the correct nested class name
        # Beanie incorrectly uses "BaseVersionedData.Metadata" for all Metadata subclasses
        _class_id: ClassVar[str] = "Corpus.Metadata"

        class Settings(BaseVersionedData.Settings):
            class_id = "_class_id"

        # Corpus identification (needed for persistence)
        corpus_name: str = ""
        corpus_type: CorpusType = CorpusType.LEXICON
        language: Language = Language.ENGLISH

        # Tree structure using UUIDs (stable across versions)
        parent_uuid: str | None = None
        child_uuids: list[str] = Field(default_factory=list)
        is_master: bool = False
        semantic_enabled_explicit: bool | None = None
        semantic_enabled_effective: bool = False
        semantic_model: str | None = None

        # Vocabulary metadata (versioning)
        vocabulary_size: int = 0
        vocabulary_hash: str = ""

        # Usage tracking (persisted to MongoDB)
        ttl_hours: float = 1.0
        search_count: int = 0
        last_accessed: datetime | None = None

        # Storage configuration
        content_location: ContentLocation | None = None

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to inject slug name and compute vocabulary_hash."""
        super().model_post_init(__context)

        # Generate slug name if not provided
        if not self.corpus_name:
            self.corpus_name = coolname.generate_slug(2)
            logger.info(f"Generated corpus slug name: {self.corpus_name}")

        # Compute vocabulary_hash if not set and vocabulary exists
        if not self.vocabulary_hash and self.vocabulary:
            self.vocabulary_hash = get_vocabulary_hash(self.vocabulary)

    @classmethod
    async def create(
        cls,
        corpus_name: str | None = None,
        vocabulary: list[str] | None = None,
        semantic: bool = False,
        model_name: str | None = None,
        language: Language = Language.ENGLISH,
    ) -> Corpus:
        """Create a new corpus instance with optional name generation.

        Args:
            corpus_name: Optional name of the corpus (will generate slug if None)
            vocabulary: List of words to include
            semantic: Whether to enable semantic search
            model_name: Model name for semantic search
            language: Language of the corpus

        Returns:
            Corpus instance

        """
        if not vocabulary:
            vocabulary = []

        # CRITICAL FIX #9: Validate vocabulary size to prevent OOM
        max_vocabulary_size = 1_000_000  # 1 million words
        if len(vocabulary) > max_vocabulary_size:
            raise ValueError(
                f"Vocabulary size ({len(vocabulary):,} words) exceeds maximum allowed "
                f"({max_vocabulary_size:,} words). This prevents potential out-of-memory errors. "
                f"Consider splitting into multiple corpora or filtering the vocabulary."
            )

        # Log incoming vocabulary
        logger.info(
            f"Creating corpus with {len(vocabulary)} words"
            f"{f' named {corpus_name}' if corpus_name else ''}",
        )

        # NFC-normalize the raw input so decomposed and precomposed forms
        # (e.g. cafe\u0301 vs café) resolve to the same string.
        vocabulary = [unicodedata.normalize("NFC", w) for w in vocabulary]

        # Normalize, sort, deduplicate, and build index mappings
        unique_normalized, vocabulary_to_index, normalized_to_original_indices = (
            normalize_vocabulary(vocabulary)
        )

        # Create the corpus instance
        corpus = cls(
            corpus_name=corpus_name or "",  # Will be generated in post_init if empty
            vocabulary=unique_normalized,
            original_vocabulary=vocabulary,
            normalized_to_original_indices=normalized_to_original_indices,
            vocabulary_to_index=vocabulary_to_index,
            language=language,
            total_word_count=len(vocabulary),
            vocabulary_hash=get_vocabulary_hash(unique_normalized),
            semantic_enabled_explicit=semantic,
            semantic_enabled_effective=semantic,
            semantic_model=model_name,
        )

        # Create unified indices
        await corpus._create_unified_indices()

        # Build signature index
        corpus._build_candidate_index()

        # Create semantic index if requested
        if semantic:
            from ..search.semantic.constants import DEFAULT_SENTENCE_MODEL
            from ..search.semantic.index import SemanticIndex

            model_name = model_name or DEFAULT_SENTENCE_MODEL
            logger.info(f"Creating semantic index with model {model_name}")

            try:
                await SemanticIndex.get_or_create(
                    corpus=corpus,
                    model_name=model_name,
                    batch_size=None,  # Use default batch size
                )
                logger.info("Semantic index created successfully")
            except Exception as e:
                logger.warning(f"Failed to create semantic index: {e}")

        return corpus

    async def _rebuild_indices(self) -> None:
        """Rebuild all indices from vocabulary."""
        # Rebuild vocabulary_to_index
        self.vocabulary_to_index = {word: i for i, word in enumerate(self.vocabulary)}

        # Rebuild normalized_to_original_indices if needed
        if self.original_vocabulary and not self.normalized_to_original_indices:
            self.normalized_to_original_indices = rebuild_original_indices(
                self.vocabulary, self.original_vocabulary, self.vocabulary_to_index
            )

        # Rebuild signature index
        self._build_candidate_index()

        # Rebuild lemmatization
        await self._create_unified_indices()

        # Update metadata
        self.vocabulary_hash = get_vocabulary_hash(self.vocabulary)

        logger.info(f"Rebuilt indices for corpus {self.corpus_name}")

    async def _create_unified_indices(self) -> None:
        """Create unified indexing and lemmatization maps."""
        # Skip if already created AND vocabulary is empty (nothing to lemmatize)
        if self.lemmatized_vocabulary and not self.vocabulary:
            return

        # Clear stale lemmatization data before rebuild
        self.lemmatized_vocabulary = []
        self.lemma_text_to_index = {}
        self.word_to_lemma_indices = {}
        self.lemma_to_word_indices = {}

        (
            self.lemmatized_vocabulary,
            self.lemma_text_to_index,
            self.word_to_lemma_indices,
            self.lemma_to_word_indices,
        ) = create_lemmatization_maps(self.vocabulary)

    async def add_words(self, words: list[str]) -> int:
        """Add words to the corpus incrementally.

        Args:
            words: List of words to add

        Returns:
            Number of new unique words added

        """
        if not words:
            return 0

        logger.info(f"Adding {len(words)} words to corpus {self.corpus_name}")

        original_unique_count = len(self.vocabulary)

        # Add to original_vocabulary
        self.original_vocabulary.extend(words)

        # Merge and rebuild
        self.vocabulary, normalized_new = merge_words(self.vocabulary, words)
        await self._rebuild_indices()

        # Update word frequencies
        for word in normalized_new:
            self.word_frequencies[word] = self.word_frequencies.get(word, 0) + 1

        # Update counts
        new_unique_count = len(self.vocabulary)
        added_count = new_unique_count - original_unique_count
        self.total_word_count = len(self.original_vocabulary)
        self.last_updated = time.time()

        logger.info(
            f"Added {added_count} unique words to corpus {self.corpus_name} "
            f"(total: {new_unique_count})",
        )

        return added_count

    async def remove_words(self, words: list[str]) -> int:
        """Remove words from the corpus incrementally.

        Args:
            words: List of words to remove

        Returns:
            Number of unique words removed

        """
        if not words:
            return 0

        logger.info(f"Removing {len(words)} words from corpus {self.corpus_name}")

        original_unique_count = len(self.vocabulary)

        # Filter both vocabularies and rebuild
        self.vocabulary, self.original_vocabulary = filter_words(
            self.vocabulary, self.original_vocabulary, words
        )
        await self._rebuild_indices()

        # Remove from word frequencies
        normalized_remove = set(batch_normalize(words))
        for word in normalized_remove:
            self.word_frequencies.pop(word, None)

        # Update counts
        new_unique_count = len(self.vocabulary)
        removed_count = original_unique_count - new_unique_count
        self.total_word_count = len(self.original_vocabulary)
        self.last_updated = time.time()

        logger.info(
            f"Removed {removed_count} unique words from corpus {self.corpus_name} "
            f"(remaining: {new_unique_count})",
        )

        return removed_count

    def get_word_by_index(self, index: int) -> str | None:
        """Get a word by its index in the normalized vocabulary."""
        return self.vocabulary[index] if 0 <= index < len(self.vocabulary) else None

    def get_original_word_by_index(self, normalized_index: int) -> str | None:
        """Get original form of a word by its normalized index.

        When multiple original forms exist, returns the first (preferred) form.
        The indices are pre-sorted to prefer diacritics over ASCII equivalents.

        Args:
            normalized_index: Index in the normalized vocabulary

        Returns:
            Original form of the word or None if not found

        """
        if original_indices := self.normalized_to_original_indices.get(normalized_index):
            # Return the first original form (pre-sorted by preference)
            return self.original_vocabulary[original_indices[0]]
        # If no mapping exists, return the normalized word itself
        return self.get_word_by_index(normalized_index)

    def get_words_by_indices(self, indices: list[int] | np.ndarray) -> list[str]:
        """Get multiple words by their indices."""
        return [word for idx in indices if (word := self.get_word_by_index(int(idx))) is not None]

    def get_original_words_by_indices(self, normalized_indices: list[int] | np.ndarray) -> list[str]:
        """Get original forms of words by their normalized indices."""
        return [
            word
            for idx in normalized_indices
            if (word := self.get_original_word_by_index(idx)) is not None
        ]

    @staticmethod
    def _word_trigrams(word: str) -> list[str]:
        """Extract character trigrams from a word with sentinel padding.

        Delegates to candidate_index.word_trigrams().
        """
        return word_trigrams(word)

    def get_candidates(
        self,
        query: str,
        max_results: int = 50,
        use_lemmas: bool = True,
        use_trigrams: bool = True,
        length_tolerance: int = 2,
    ) -> list[int]:
        """Get candidate word indices for a query.

        Delegates to candidate_index.get_candidates() with instance data.

        Args:
            query: Search query
            max_results: Maximum number of results
            use_lemmas: Whether to include lemma matches
            use_trigrams: Whether to use trigram index matching
            length_tolerance: Length difference tolerance

        Returns:
            List of vocabulary indices

        """
        return get_candidates(
            query=query,
            vocabulary=self.vocabulary,
            vocabulary_to_index=self.vocabulary_to_index,
            trigram_index=self.trigram_index,
            length_buckets=self.length_buckets,
            lemma_text_to_index=self.lemma_text_to_index if use_lemmas else None,
            lemma_to_word_indices=self.lemma_to_word_indices if use_lemmas else None,
            max_results=max_results,
            use_lemmas=use_lemmas,
            use_trigrams=use_trigrams,
            length_tolerance=length_tolerance,
        )

    def get_substring_candidates(
        self,
        query: str,
        max_results: int = 50,
    ) -> list[int]:
        """Get candidate word indices for substring/infix matching.

        Delegates to candidate_index.get_substring_candidates().

        Args:
            query: Substring to search for
            max_results: Maximum number of results

        Returns:
            List of vocabulary indices containing the query as a substring

        """
        return get_substring_candidates(
            query=query,
            vocabulary=self.vocabulary,
            trigram_index=self.trigram_index,
            max_results=max_results,
        )

    def _build_candidate_index(self) -> None:
        """Build trigram inverted index and length buckets for candidate selection.

        Delegates to candidate_index.build_candidate_index().
        """
        self.trigram_index, self.length_buckets = build_candidate_index(self.vocabulary)

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> Corpus:
        """Load corpus from dict data.

        Args:
            data: Dictionary data to load

        Returns:
            Corpus instance

        """
        return cls.model_validate(data)

    def update_version(self, change_description: str = "") -> None:
        """Mark the corpus for version update on next save.

        Args:
            change_description: Description of changes made

        """
        if not self.version_info:
            # Initialize version info if it doesn't exist
            self.version_info = VersionInfo(
                version="1.0.0",
                data_hash="",  # Will be computed on save
                is_latest=True,
            )

        # Set a flag that the manager will recognize for version increment
        self._needs_version_update = True
        # Store change description for metadata
        if change_description:
            self._change_description = change_description

    async def delete(self) -> None:
        """Delete corpus from storage with cascade deletion of dependent indices.

        Deletion order:
        1. Find all SearchIndex documents for this corpus
        2. For each SearchIndex, delete its dependent TrieIndex and SemanticIndex
        3. Delete all SearchIndex documents
        4. Delete the Corpus document itself

        Raises:
            ValueError: If corpus_id is not set
        """
        if not self.corpus_id:
            logger.warning("Cannot delete corpus without ID")
            raise ValueError("Cannot delete corpus without corpus_id")

        logger.info(
            f"Starting cascade deletion for corpus {self.corpus_name} (ID: {self.corpus_id})"
        )

        # Step 1: Delete all dependent SearchIndex documents (which will cascade to their indices)
        from ..search.index import SearchIndex

        try:
            # Get the SearchIndex for this corpus
            search_index = await SearchIndex.get(
                corpus_uuid=self.corpus_uuid,
                corpus_name=self.corpus_name,
            )

            if search_index:
                logger.info(f"Found SearchIndex for corpus {self.corpus_name}, deleting...")
                await search_index.delete()
            else:
                logger.debug(f"No SearchIndex found for corpus {self.corpus_name}")

        except Exception as e:
            logger.error(f"Error deleting SearchIndex for corpus {self.corpus_name}: {e}")
            # Continue with corpus deletion even if SearchIndex deletion fails

        # Step 2: Delete the corpus itself through version manager
        vm = get_version_manager()

        # Get the latest version to delete
        metadata = await vm.get_latest(
            resource_id=self.corpus_name,
            resource_type=ResourceType.CORPUS,
        )

        if metadata and metadata.version_info:
            await vm.delete_version(
                resource_id=self.corpus_name,
                resource_type=ResourceType.CORPUS,
                version=metadata.version_info.version,
            )
            logger.info(f"Successfully deleted corpus {self.corpus_name} (ID: {self.corpus_id})")
        else:
            logger.warning(
                f"No metadata found for corpus {self.corpus_name}, may already be deleted"
            )

    async def save(self) -> Corpus:
        """Persist corpus via TreeCorpusManager (convenience wrapper).

        Delegates to TreeCorpusManager.save_corpus() which handles versioning,
        metadata creation, and MongoDB persistence.
        """
        from .manager import get_tree_corpus_manager

        manager = get_tree_corpus_manager()
        saved = await manager.save_corpus(self)
        if saved:
            self.corpus_id = saved.corpus_id
            self.corpus_uuid = saved.corpus_uuid
        return self
