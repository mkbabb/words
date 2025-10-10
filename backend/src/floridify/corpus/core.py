"""Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic and base corpus source configuration.
"""

from __future__ import annotations

import time
from typing import Any, ClassVar

import coolname
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, field_validator

from ..caching.manager import get_version_manager
from ..caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ContentLocation,
    ResourceType,
    VersionConfig,
    VersionInfo,
)
from ..models.base import Language
from ..text.normalize import batch_lemmatize, batch_normalize
from ..utils.logging import get_logger
from .models import CorpusType
from .utils import get_vocabulary_hash

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
    word_to_lemma_indices: dict[int, int] = Field(default_factory=dict)
    lemma_to_word_indices: dict[int, list[int]] = Field(default_factory=dict)

    # Signature maps for efficient searching
    signature_buckets: dict[str, list[int]] = Field(default_factory=dict)
    length_buckets: dict[int, list[int]] = Field(default_factory=dict)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    vocabulary_stats: dict[str, Any] = Field(default_factory=dict)
    vocabulary_hash: str = ""
    vocabulary_indices: list[int] | None = None

    # Sources
    sources: list[str] = Field(default_factory=list)
    unique_word_count: int = 0
    total_word_count: int = 0
    last_updated: float = Field(default_factory=time.time)

    # Tree structure references
    corpus_id: PydanticObjectId | None = None  # Primary key
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False

    # Word frequency data
    word_frequencies: dict[str, int] = Field(default_factory=dict)

    # Version tracking (populated from metadata when loaded)
    version_info: VersionInfo | None = None
    _metadata_id: PydanticObjectId | None = None  # Internal reference to metadata document

    model_config = {
        "arbitrary_types_allowed": True,
        "use_enum_values": True,
        "ser_json_inf_nan": "constants",
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

        # Corpus identification (needed for persistence)
        corpus_name: str = ""
        corpus_type: CorpusType = CorpusType.LEXICON
        language: Language = Language.ENGLISH

        # Tree structure (part of versioned state)
        parent_corpus_id: PydanticObjectId | None = None
        child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
        is_master: bool = False

        # Vocabulary metadata (versioning)
        vocabulary_size: int = 0
        vocabulary_hash: str = ""

        # Storage configuration
        content_location: ContentLocation | None = None

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to inject slug name if needed."""
        super().model_post_init(__context)

        # Generate slug name if not provided
        if not self.corpus_name:
            self.corpus_name = coolname.generate_slug(2)
            logger.info(f"Generated corpus slug name: {self.corpus_name}")

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

        # Log incoming vocabulary
        logger.info(
            f"Creating corpus with {len(vocabulary)} words"
            f"{f' named {corpus_name}' if corpus_name else ''}",
        )

        # Normalize the vocabulary
        normalized_vocabulary = batch_normalize(vocabulary)
        logger.info(f"Normalized to {len(normalized_vocabulary)} unique words")

        # Sort and deduplicate normalized vocabulary
        unique_normalized = sorted(set(normalized_vocabulary))
        logger.info(f"Final vocabulary: {len(unique_normalized)} unique normalized words")

        # Create vocabulary-to-index mapping
        vocabulary_to_index = {word: i for i, word in enumerate(unique_normalized)}

        # Build normalized_to_original_indices AFTER sorting
        # Maps from index in sorted vocabulary to indices in original_vocabulary
        # Sort indices by preference: diacritics > ASCII
        def has_diacritics(word: str) -> bool:
            """Check if word contains non-ASCII characters (diacritics)."""
            return any(ord(c) > 127 for c in word)

        normalized_to_original_indices: dict[int, list[int]] = {}
        for orig_idx, (orig_word, norm_word) in enumerate(
            zip(vocabulary, normalized_vocabulary, strict=False)
        ):
            if norm_word in vocabulary_to_index:
                sorted_idx = vocabulary_to_index[norm_word]
                if sorted_idx not in normalized_to_original_indices:
                    normalized_to_original_indices[sorted_idx] = []
                normalized_to_original_indices[sorted_idx].append(orig_idx)

        # Sort each list of indices by preference: words with diacritics first
        for sorted_idx, orig_indices in normalized_to_original_indices.items():
            if len(orig_indices) > 1:
                # Sort by: has_diacritics (True first), then by original index
                orig_indices.sort(key=lambda idx: (not has_diacritics(vocabulary[idx]), idx))

        # Create the corpus instance
        corpus = cls(
            corpus_name=corpus_name or "",  # Will be generated in post_init if empty
            vocabulary=unique_normalized,
            original_vocabulary=vocabulary,
            normalized_to_original_indices=normalized_to_original_indices,
            vocabulary_to_index=vocabulary_to_index,
            language=language,
            unique_word_count=len(unique_normalized),
            total_word_count=len(vocabulary),
            vocabulary_hash=get_vocabulary_hash(unique_normalized),
        )

        # Create unified indices
        await corpus._create_unified_indices()

        # Build signature index
        corpus._build_signature_index()

        # Create semantic index if requested
        if semantic:
            from ..search.semantic.constants import DEFAULT_SENTENCE_MODEL
            from ..search.semantic.models import SemanticIndex

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

            def has_diacritics(word: str) -> bool:
                """Check if word contains non-ASCII characters (diacritics)."""
                return any(ord(c) > 127 for c in word)

            self.normalized_to_original_indices = {}
            normalized_orig = batch_normalize(self.original_vocabulary)
            for orig_idx, norm_word in enumerate(normalized_orig):
                if norm_word in self.vocabulary_to_index:
                    sorted_idx = self.vocabulary_to_index[norm_word]
                    if sorted_idx not in self.normalized_to_original_indices:
                        self.normalized_to_original_indices[sorted_idx] = []
                    self.normalized_to_original_indices[sorted_idx].append(orig_idx)

            # Sort each list by preference: words with diacritics first
            for sorted_idx, orig_indices in self.normalized_to_original_indices.items():
                if len(orig_indices) > 1:
                    orig_indices.sort(
                        key=lambda idx: (
                            not has_diacritics(self.original_vocabulary[idx]),
                            idx,
                        )
                    )

        # Rebuild signature index
        self._build_signature_index()

        # Clear lemmatization data to force rebuild
        self.lemmatized_vocabulary = []
        self.word_to_lemma_indices = {}
        self.lemma_to_word_indices = {}

        # Rebuild unified indices (lemmatization)
        await self._create_unified_indices()

        # Update metadata
        self.unique_word_count = len(self.vocabulary)
        self.vocabulary_hash = get_vocabulary_hash(self.vocabulary)

        logger.info(f"Rebuilt indices for corpus {self.corpus_name}")

    async def _create_unified_indices(self) -> None:
        """Create unified indexing and lemmatization maps."""
        # Skip if already created
        if self.lemmatized_vocabulary:
            return

        # Create lemmatized versions
        lemmas, _, _ = batch_lemmatize(self.vocabulary)

        # Build lemma vocabulary (unique lemmas in order)
        unique_lemmas: list[str] = []
        seen_lemmas: set[str] = set()
        for lemma in lemmas:
            if lemma not in seen_lemmas:
                unique_lemmas.append(lemma)
                seen_lemmas.add(lemma)

        self.lemmatized_vocabulary = unique_lemmas

        # Create lemma index mapping
        lemma_to_idx = {lemma: i for i, lemma in enumerate(unique_lemmas)}

        # Build word-to-lemma and lemma-to-words mappings
        for word_idx, (word, lemma) in enumerate(zip(self.vocabulary, lemmas, strict=False)):
            lemma_idx = lemma_to_idx[lemma]

            # Map word index to lemma index
            self.word_to_lemma_indices[word_idx] = lemma_idx

            # Map lemma index to word indices
            if lemma_idx not in self.lemma_to_word_indices:
                self.lemma_to_word_indices[lemma_idx] = []
            self.lemma_to_word_indices[lemma_idx].append(word_idx)

        logger.info(
            f"Created lemmatization maps: {len(unique_lemmas)} lemmas "
            f"from {len(self.vocabulary)} words",
        )

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

        # Normalize new words
        normalized_new = batch_normalize(words)

        # Track original count
        original_unique_count = len(self.vocabulary)

        # Add to original_vocabulary
        self.original_vocabulary.extend(words)

        # Merge with existing vocabulary (set-based deduplication)
        merged_vocab = set(self.vocabulary) | set(normalized_new)

        # Sort and update
        self.vocabulary = sorted(merged_vocab)

        # Rebuild all indices to maintain consistency
        await self._rebuild_indices()

        # Update word frequencies if provided
        for word in normalized_new:
            if word in self.word_frequencies:
                self.word_frequencies[word] += 1
            else:
                self.word_frequencies[word] = 1

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

        # Normalize words to remove
        normalized_remove = set(batch_normalize(words))

        # Track original count
        original_unique_count = len(self.vocabulary)

        # Remove from vocabulary
        self.vocabulary = sorted([w for w in self.vocabulary if w not in normalized_remove])

        # Remove from original_vocabulary and rebuild mapping
        # This is trickier - we need to track which original words map to removed normalized words
        normalized_orig = batch_normalize(self.original_vocabulary)
        keep_indices = [
            i for i, norm_word in enumerate(normalized_orig) if norm_word not in normalized_remove
        ]
        self.original_vocabulary = [self.original_vocabulary[i] for i in keep_indices]

        # Rebuild all indices to maintain consistency
        await self._rebuild_indices()

        # Remove from word frequencies
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

    def get_words_by_indices(self, indices: list[int]) -> list[str]:
        """Get multiple words by their indices."""
        return [word for idx in indices if (word := self.get_word_by_index(idx)) is not None]

    def get_original_words_by_indices(self, normalized_indices: list[int]) -> list[str]:
        """Get original forms of words by their normalized indices."""
        return [
            word
            for idx in normalized_indices
            if (word := self.get_original_word_by_index(idx)) is not None
        ]

    def get_candidates(
        self,
        query: str,
        max_results: int = 50,
        use_lemmas: bool = True,
        use_signatures: bool = True,
        length_tolerance: int = 2,
    ) -> list[int]:
        """Get candidate word indices for a query.

        Args:
            query: Search query
            max_results: Maximum number of results
            use_lemmas: Whether to include lemma matches
            use_signatures: Whether to use signature matching
            length_tolerance: Length difference tolerance

        Returns:
            List of vocabulary indices

        """
        candidates = set()

        # Handle empty query
        if not query or not query.strip():
            return []

        normalized_queries = batch_normalize([query])
        if not normalized_queries:
            return []
        normalized_query = normalized_queries[0]

        # Direct lookup
        if normalized_query in self.vocabulary_to_index:
            candidates.add(self.vocabulary_to_index[normalized_query])
            if len(candidates) >= max_results:
                return list(candidates)[:max_results]

        # Lemma-based lookup
        if use_lemmas and self.lemmatized_vocabulary:
            query_lemmas, _, _ = batch_lemmatize([normalized_query])
            query_lemma: str = query_lemmas[0]

            # Find all words with the same lemma
            for lemma_idx, lemma in enumerate(self.lemmatized_vocabulary):
                if lemma == query_lemma:
                    # Add all words that have this lemma
                    if word_indices := self.lemma_to_word_indices.get(lemma_idx):
                        candidates.update(word_indices)
                        if len(candidates) >= max_results:
                            return list(candidates)[:max_results]

        # Signature-based candidates
        if use_signatures and self.signature_buckets:
            from ..text.normalize import get_word_signature

            query_sig = get_word_signature(normalized_query)
            if query_sig in self.signature_buckets:
                sig_candidates = self.signature_buckets[query_sig]
                candidates.update(sig_candidates[:max_results])
                if len(candidates) >= max_results:
                    return list(candidates)[:max_results]

        # Length-based candidates
        query_len = len(normalized_query)
        for length_diff in range(length_tolerance + 1):
            for length in [query_len - length_diff, query_len + length_diff]:
                if length > 0 and length in self.length_buckets:
                    length_candidates = self.length_buckets[length]
                    candidates.update(length_candidates)
                    if len(candidates) >= max_results:
                        return list(candidates)[:max_results]

        return list(candidates)[:max_results]

    def _build_signature_index(self) -> None:
        """Build signature-based index for efficient searching."""
        from ..text.normalize import get_word_signature

        self.signature_buckets.clear()
        self.length_buckets.clear()

        for idx, word in enumerate(self.vocabulary):
            # Signature bucket
            signature = get_word_signature(word)
            if signature not in self.signature_buckets:
                self.signature_buckets[signature] = []
            self.signature_buckets[signature].append(idx)

            # Length bucket
            length = len(word)
            if length not in self.length_buckets:
                self.length_buckets[length] = []
            self.length_buckets[length].append(idx)

        # Sort buckets for consistent ordering
        for bucket in self.signature_buckets.values():
            bucket.sort()
        for bucket in self.length_buckets.values():
            bucket.sort()

        logger.info(
            f"Built signature index: {len(self.signature_buckets)} signatures, "
            f"{len(self.length_buckets)} length buckets",
        )

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Dump model to dict, handling special fields."""
        return super().model_dump(exclude={"vocabulary_indices"}, **kwargs)

    @classmethod
    def model_load(cls, data: dict[str, Any]) -> Corpus:
        """Load corpus from dict data.

        Args:
            data: Dictionary data to load

        Returns:
            Corpus instance

        """
        return cls.model_validate(data)

    @classmethod
    async def get(
        cls,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus | None:
        """Get corpus from versioned storage by ID or name.

        Args:
            corpus_id: ObjectId of the corpus (preferred)
            corpus_name: Name of the corpus (fallback)
            config: Version configuration

        Returns:
            Corpus instance or None if not found

        """
        if not corpus_id and not corpus_name:
            raise ValueError("Either corpus_id or corpus_name must be provided")

        from .manager import get_tree_corpus_manager

        manager = get_tree_corpus_manager()

        # Get the corpus directly from manager
        # The manager already returns a Corpus object, not metadata
        corpus = await manager.get_corpus(
            corpus_id=corpus_id,
            corpus_name=corpus_name,
            config=config,
        )

        return corpus

    @classmethod
    async def get_or_create(
        cls,
        corpus_id: PydanticObjectId | None = None,
        corpus_name: str | None = None,
        vocabulary: list[str] | None = None,
        language: Language = Language.ENGLISH,
        corpus_type: CorpusType = CorpusType.LEXICON,
        semantic: bool = True,
        model_name: str | None = None,
        config: VersionConfig | None = None,
    ) -> Corpus:
        """Get existing corpus or create new one.

        Args:
            corpus_id: ObjectId of the corpus (preferred for lookup)
            corpus_name: Name of the corpus (optional, will generate slug if not provided)
            vocabulary: List of words if creating new
            language: Language of the corpus
            corpus_type: Type of corpus
            semantic: Enable semantic search
            model_name: Embedding model name
            config: Version configuration

        Returns:
            Corpus instance

        """
        # Try to get existing by ID or name
        existing = await cls.get(corpus_id, corpus_name, config)
        if existing:
            return existing

        # Create new corpus
        corpus = await cls.create(
            corpus_name=corpus_name,
            vocabulary=vocabulary or [],
            semantic=semantic,
            model_name=model_name,
            language=language,
        )

        # Set the corpus type
        corpus.corpus_type = corpus_type

        # Save the new corpus
        await corpus.save(config)

        return corpus

    @classmethod
    async def get_many_by_ids(
        cls,
        corpus_ids: list[PydanticObjectId],
        config: VersionConfig | None = None,
    ) -> list[Corpus]:
        """Get multiple corpora by their IDs in batch.

        Args:
            corpus_ids: List of corpus IDs to retrieve
            config: Version configuration

        Returns:
            List of Corpus instances (may be shorter than input if some IDs don't exist)

        """
        from .manager import get_tree_corpus_manager

        manager = get_tree_corpus_manager()
        return await manager.get_corpora_by_ids(corpus_ids, config)

    async def save(self, config: VersionConfig | None = None, update_metadata: bool = True) -> bool:
        """Save corpus to versioned storage.

        Args:
            config: Version configuration
            update_metadata: Whether to update metadata

        Returns:
            True if saved successfully

        """
        from .manager import get_tree_corpus_manager

        manager = get_tree_corpus_manager()

        # Update metadata if requested
        if update_metadata:
            self.last_updated = time.time()
            self.unique_word_count = len(self.vocabulary)
            self.vocabulary_hash = get_vocabulary_hash(self.vocabulary)

        # Handle versioning - create or update config for version increment
        if not config:
            config = VersionConfig()

        # Version updates should be handled through explicit config params
        # No more private attribute magic

        # Save through manager (which will set the corpus_id)
        saved = await manager.save_corpus(
            corpus_id=self.corpus_id,
            corpus_name=self.corpus_name,
            corpus_type=self.corpus_type,
            language=self.language,
            content=self.model_dump(),
            config=config,
            parent_corpus_id=self.parent_corpus_id,
            child_corpus_ids=self.child_corpus_ids,
            is_master=self.is_master,
        )

        if saved and saved.corpus_id:
            self.corpus_id = saved.corpus_id

            # Update version info from the saved metadata
            # We need to get the metadata to access version_info
            try:
                metadata = await manager.vm.get_latest(
                    resource_id=self.corpus_name,
                    resource_type=ResourceType.CORPUS,
                )
                if metadata and metadata.version_info:
                    self.version_info = metadata.version_info
                    self._metadata_id = metadata.id
            except Exception as e:
                logger.warning(f"Failed to update version info: {e}")

        return bool(saved)

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
        from ..search.models import SearchIndex

        try:
            # Get the SearchIndex for this corpus
            search_index = await SearchIndex.get(
                corpus_id=self.corpus_id,
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
