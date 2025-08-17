"""Search models for corpus and semantic data storage.

Unified models for corpus storage, caching, and semantic indexing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..caching.manager import get_version_manager
from ..corpus.core import Corpus
from ..models.dictionary import Language
from ..models.versioned import ResourceType, VersionConfig
from ..utils.logging import get_logger
from .constants import SearchMethod

logger = get_logger(__name__)


class SearchResult(BaseModel):
    """Unified search result across all search methods."""

    word: str = Field(..., description="Matched word or phrase")
    lemmatized_word: str | None = Field(
        None,
        description="Lemmatized form of the word if applicable",
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    method: SearchMethod = Field(
        ...,
        description="Search method used (exact, fuzzy, semantic)",
    )
    language: Language | None = Field(None, description="Language code if applicable")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    def __lt__(self, other: SearchResult) -> bool:
        """Compare by score for sorting (higher score is better)."""
        return self.score > other.score

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "word": "example",
                "score": 0.95,
                "method": "exact",
                "language": "en",
                "metadata": {"frequency": 1000},
            },
        }


class TrieIndexMetadata(BaseVersionedData):
    """Trie index metadata for prefix search."""

    corpus_ids: list[PydanticObjectId]
    node_count: int
    max_depth: int
    supports_fuzzy: bool = False
    memory_usage_bytes: int

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.TRIE)
        data.setdefault("namespace", CacheNamespace.TRIE)
        super().__init__(**data)


class SearchIndexMetadata(BaseVersionedData):
    """Composite search index metadata."""

    trie_index_id: PydanticObjectId | None = None
    semantic_index_id: PydanticObjectId | None = None
    corpus_id: PydanticObjectId

    # Configuration
    search_config: dict[str, Any] = Field(default_factory=dict)
    supported_languages: list[Language] = Field(default_factory=list)
    max_results: int = 100

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.SEARCH)
        data.setdefault("namespace", CacheNamespace.SEARCH)
        super().__init__(**data)


class TrieIndex(BaseModel):
    """Complete trie index data model for TrieSearch.

    Contains all trie data, frequencies, and search structures.
    """

    # Core identification
    corpus_name: str
    corpus_hash: str
    vocabulary_hash: str

    # Trie data - sorted word list for marisa-trie
    trie_data: list[str] = Field(default_factory=list)

    # Word frequency mapping for ranking
    word_frequencies: dict[str, int] = Field(default_factory=dict)

    # Original vocabulary for diacritic preservation
    original_vocabulary: list[str] = Field(default_factory=list)
    normalized_to_original: dict[str, str] = Field(default_factory=dict)

    # Statistics
    word_count: int = 0
    max_frequency: int = 0
    build_time_seconds: float = 0.0

    @classmethod
    async def get(
        cls,
        corpus_name: str,
        config: VersionConfig | None = None,
    ) -> TrieIndex | None:
        """Get trie index from versioned storage.

        Args:
            corpus_name: Name of the corpus
            config: Version configuration

        Returns:
            TrieIndex instance or None if not found
        """
        manager = get_version_manager()
        index_id = f"{corpus_name}:trie"

        # Get the latest trie index metadata
        metadata = await manager.get_latest(
            resource_id=index_id,
            resource_type=ResourceType.TRIE,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

        if not metadata:
            return None

        # Load content from metadata
        content = await metadata.get_content()
        if not content:
            return None

        return cls.model_validate(content)

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
        import time

        from .utils import calculate_default_frequency

        start_time = time.perf_counter()

        # Build frequency map
        word_frequencies = {}
        max_frequency = 0
        frequencies = getattr(corpus, 'word_frequencies', None)

        for word in corpus.vocabulary:
            if frequencies:
                freq = frequencies.get(word, calculate_default_frequency(word))
            else:
                freq = calculate_default_frequency(word)
            word_frequencies[word] = freq
            max_frequency = max(max_frequency, freq)

        # Build normalized to original mapping
        normalized_to_original = {}
        for norm_word, orig_word in zip(corpus.vocabulary, corpus.original_vocabulary):
            normalized_to_original[norm_word] = orig_word

        build_time = time.perf_counter() - start_time

        return cls(
            corpus_name=corpus.corpus_name,
            corpus_hash=corpus.vocabulary_hash,
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
        # Try to get existing
        existing = await cls.get(corpus.corpus_name, config)
        if existing and existing.vocabulary_hash == corpus.vocabulary_hash:
            logger.debug(f"Using cached trie index for '{corpus.corpus_name}'")
            return existing

        # Create new
        logger.info(f"Building new trie index for '{corpus.corpus_name}'")
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
        """
        manager = get_version_manager()
        index_id = f"{self.corpus_name}:trie"

        # Save using version manager
        await manager.save(
            resource_id=index_id,
            resource_type=ResourceType.TRIE,
            namespace=manager._get_namespace(ResourceType.TRIE),
            content=self.model_dump(),
            config=config or VersionConfig(),
            metadata={
                "corpus_hash": self.corpus_hash,
                "vocabulary_hash": self.vocabulary_hash,
                "word_count": self.word_count,
            },
        )

        logger.debug(f"Saved trie index for {index_id}")


class SearchIndex(BaseModel):
    """Complete search index data model for SearchEngine.

    Contains all configuration, references, and state for multi-method search.
    """

    # Core identification
    corpus_name: str
    corpus_hash: str
    vocabulary_hash: str

    # Search configuration
    min_score: float = 0.75
    semantic_enabled: bool = True
    semantic_model: str = "all-MiniLM-L6-v2"

    # Component indices (embedded or referenced)
    trie_index_id: str | None = None
    semantic_index_id: str | None = None

    # Component states
    has_trie: bool = False
    has_fuzzy: bool = False
    has_semantic: bool = False

    # Statistics
    vocabulary_size: int = 0
    total_indices: int = 0

    @classmethod
    async def get(
        cls,
        corpus_name: str,
        config: VersionConfig | None = None,
    ) -> SearchIndex | None:
        """Get search index from versioned storage.

        Args:
            corpus_name: Name of the corpus
            config: Version configuration

        Returns:
            SearchIndex instance or None if not found
        """
        manager = get_version_manager()
        index_id = f"{corpus_name}:search"

        # Get the latest search index metadata
        metadata = await manager.get_latest(
            resource_id=index_id,
            resource_type=ResourceType.SEARCH,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

        if not metadata:
            return None

        # Load content from metadata
        content = await metadata.get_content()
        if not content:
            return None

        return cls.model_validate(content)

    @classmethod
    async def create(
        cls,
        corpus: Corpus,
        min_score: float = 0.75,
        semantic: bool = True,
        semantic_model: str = "all-MiniLM-L6-v2",
    ) -> SearchIndex:
        """Create new search index from corpus.

        Args:
            corpus: Corpus containing vocabulary
            min_score: Minimum score threshold for results
            semantic: Enable semantic search
            semantic_model: Model for semantic search

        Returns:
            SearchIndex instance with initialized configuration
        """
        from ..corpus.utils import get_vocabulary_hash

        return cls(
            corpus_name=corpus.corpus_name,
            corpus_hash=corpus.vocabulary_hash,
            vocabulary_hash=get_vocabulary_hash(corpus.vocabulary),
            min_score=min_score,
            semantic_enabled=semantic,
            semantic_model=semantic_model,
            vocabulary_size=len(corpus.vocabulary),
            has_trie=True,  # Always build trie for exact/prefix search
            has_fuzzy=True,  # Always enable fuzzy
            has_semantic=semantic,
        )

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        min_score: float = 0.75,
        semantic: bool = True,
        semantic_model: str = "all-MiniLM-L6-v2",
        config: VersionConfig | None = None,
    ) -> SearchIndex:
        """Get existing search index or create new one.

        Args:
            corpus: Corpus containing vocabulary
            min_score: Minimum score threshold
            semantic: Enable semantic search
            semantic_model: Model for semantic search
            config: Version configuration

        Returns:
            SearchIndex instance
        """
        # Try to get existing
        existing = await cls.get(corpus.corpus_name, config)
        if existing and existing.vocabulary_hash == corpus.vocabulary_hash:
            return existing

        # Create new
        index = await cls.create(
            corpus=corpus,
            min_score=min_score,
            semantic=semantic,
            semantic_model=semantic_model,
        )

        # Save the new index
        await index.save(config)
        return index

    async def save(
        self,
        config: VersionConfig | None = None,
    ) -> None:
        """Save search index to versioned storage.

        Args:
            config: Version configuration
        """
        manager = get_version_manager()
        index_id = f"{self.corpus_name}:search"

        # Save using version manager
        await manager.save(
            resource_id=index_id,
            resource_type=ResourceType.SEARCH,
            namespace=manager._get_namespace(ResourceType.SEARCH),
            content=self.model_dump(),
            config=config or VersionConfig(),
            metadata={
                "corpus_hash": self.corpus_hash,
                "vocabulary_size": self.vocabulary_size,
            },
        )

        logger.debug(f"Saved search index for {index_id}")


__all__ = [
    "SearchResult",
    "SearchIndex",
    "TrieIndex",
    "SemanticIndex",
]
