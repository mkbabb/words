"""Core corpus implementation with in-memory vocabulary data.

Contains the actual vocabulary processing and storage logic and base corpus source configuration.
"""

from __future__ import annotations

import time
from typing import Any

import coolname  # type: ignore
from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ContentLocation,
    ResourceType,
    VersionConfig,
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

    # Core vocabulary data - sorted normalized vocabulary
    vocabulary: list[str]
    original_vocabulary: list[str] = Field(
        default_factory=list, description="Original forms of words"
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

    model_config = {"arbitrary_types_allowed": True}

    class Metadata(BaseVersionedData):
        # Corpus identification
        corpus_name: str = ""
        corpus_type: CorpusType = CorpusType.LEXICON
        language: Language = Language.ENGLISH

        # Tree structure
        parent_corpus_id: PydanticObjectId | None = None
        child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
        is_master: bool = False

        # Vocabulary reference
        content_location: ContentLocation | None = None

        def __init__(self, **data: Any) -> None:
            data.setdefault("resource_type", ResourceType.CORPUS)
            data.setdefault("namespace", CacheNamespace.CORPUS)

            super().__init__(**data)

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
            f"{f' named {corpus_name}' if corpus_name else ''}"
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
        normalized_to_original_indices: dict[int, list[int]] = {}
        for orig_idx, (orig_word, norm_word) in enumerate(zip(vocabulary, normalized_vocabulary)):
            if norm_word in vocabulary_to_index:
                sorted_idx = vocabulary_to_index[norm_word]
                if sorted_idx not in normalized_to_original_indices:
                    normalized_to_original_indices[sorted_idx] = []
                normalized_to_original_indices[sorted_idx].append(orig_idx)

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
            from ..search.semantic.models import SemanticIndex

            model_name = model_name or "all-MiniLM-L6-v2"
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
            self.normalized_to_original_indices = {}
            normalized_orig = batch_normalize(self.original_vocabulary)
            for orig_idx, norm_word in enumerate(normalized_orig):
                if norm_word in self.vocabulary_to_index:
                    sorted_idx = self.vocabulary_to_index[norm_word]
                    if sorted_idx not in self.normalized_to_original_indices:
                        self.normalized_to_original_indices[sorted_idx] = []
                    self.normalized_to_original_indices[sorted_idx].append(orig_idx)

        # Rebuild signature index
        self._build_signature_index()

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
        for word_idx, (word, lemma) in enumerate(zip(self.vocabulary, lemmas)):
            lemma_idx = lemma_to_idx[lemma]

            # Map word index to lemma index
            self.word_to_lemma_indices[word_idx] = lemma_idx

            # Map lemma index to word indices
            if lemma_idx not in self.lemma_to_word_indices:
                self.lemma_to_word_indices[lemma_idx] = []
            self.lemma_to_word_indices[lemma_idx].append(word_idx)

        logger.info(
            f"Created lemmatization maps: {len(unique_lemmas)} lemmas "
            f"from {len(self.vocabulary)} words"
        )

    def get_word_by_index(self, index: int) -> str | None:
        """Get a word by its index in the normalized vocabulary."""
        return self.vocabulary[index] if 0 <= index < len(self.vocabulary) else None

    def get_original_word_by_index(self, normalized_index: int) -> str | None:
        """Get the first original form of a word by its normalized index.

        Args:
            normalized_index: Index in the normalized vocabulary

        Returns:
            Original form of the word or None if not found
        """
        if original_indices := self.normalized_to_original_indices.get(normalized_index):
            # Return the first original form
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
        normalized_query = batch_normalize([query])[0]

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
            f"{len(self.length_buckets)} length buckets"
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

        return bool(saved)

    async def delete(self) -> None:
        """Delete corpus from storage."""
        if not self.corpus_id:
            logger.warning("Cannot delete corpus without ID")
            return

        # Delete through version manager
        from ..caching.manager import get_version_manager
        from ..caching.models import ResourceType

        vm = get_version_manager()

        # Get the latest version to delete
        metadata = await vm.get_latest(
            resource_id=self.corpus_name, resource_type=ResourceType.CORPUS
        )

        if metadata and metadata.version_info:
            await vm.delete_version(
                resource_id=self.corpus_name,
                resource_type=ResourceType.CORPUS,
                version=metadata.version_info.version,
            )

        logger.info(f"Deleted corpus {self.corpus_name} (ID: {self.corpus_id})")
