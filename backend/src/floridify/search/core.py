"""Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

import asyncio
import itertools
from typing import Any

from ..corpus.core import Corpus
from ..corpus.manager import get_corpus_manager
from ..text import normalize
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod, SearchMode
from .fuzzy import FuzzySearch  # Using RapidFuzz implementation
from .models import SearchResult
from .semantic.constants import DEFAULT_SENTENCE_MODEL, SemanticModel
from .semantic.core import SemanticSearch

# Semantic manager removed - using direct SemanticSearch creation
from .trie import TrieSearch

logger = get_logger(__name__)


class SearchIndex:
    """Encapsulates search index data and configurations.

    This class manages the trie index, fuzzy search configuration, and
    semantic search references for efficient multi-method search.
    """

    def __init__(
        self,
        corpus: Corpus,
        semantic_enabled: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
    ):
        """Initialize search index.

        Args:
            corpus: Corpus containing vocabulary data
            semantic_enabled: Whether semantic search is enabled
            semantic_model: Model to use for semantic search
        """
        self.corpus = corpus
        self.semantic_enabled = semantic_enabled
        self.semantic_model = semantic_model

        # Search components (initialized lazily)
        self.trie_search: TrieSearch | None = None
        self.fuzzy_search: FuzzySearch | None = None

        # References to semantic index
        self.semantic_index_id: str | None = None
        self.has_semantic_index: bool = False

        # Metadata
        self.build_time_seconds: float = 0.0
        self.memory_usage_mb: float = 0.0
        self.index_type: str = "composite"

    def build_trie_index(self) -> None:
        """Build trie index for prefix search."""
        if self.corpus and self.corpus.vocabulary:
            self.trie_search = TrieSearch()

    def build_fuzzy_index(self) -> None:
        """Build fuzzy search index."""
        if self.corpus:
            self.fuzzy_search = FuzzySearch()

    @classmethod
    async def get(
        cls,
        corpus: Corpus,
        semantic_enabled: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
        config: Any | None = None,
    ) -> SearchIndex | None:
        """Get search index from versioned storage.

        Args:
            corpus: Corpus containing vocabulary
            semantic_enabled: Whether semantic search is enabled
            semantic_model: Model for semantic search
            config: Version configuration

        Returns:
            SearchIndex instance or None if not found
        """
        from ..caching.manager import get_version_manager
        from ..models.versioned import ResourceType, VersionConfig

        manager = get_version_manager()

        # Create index ID based on corpus
        index_id = f"{corpus.corpus_name}:search"

        # Get the latest search index metadata
        search_metadata = await manager.get_latest(
            resource_id=index_id,
            resource_type=ResourceType.SEARCH,
            use_cache=config.use_cache if config else True,
            config=config or VersionConfig(),
        )

        if not search_metadata:
            return None

        # Load content from metadata
        content = await search_metadata.get_content()
        if not content:
            return None

        # Create index instance
        index = cls(
            corpus=corpus,
            semantic_enabled=semantic_enabled,
            semantic_model=semantic_model,
        )

        # Restore configuration from content
        if "semantic_index_id" in content:
            index.semantic_index_id = content["semantic_index_id"]
            index.has_semantic_index = True

        # Rebuild indices
        index.build_trie_index()
        index.build_fuzzy_index()

        return index

    async def save(
        self,
        config: Any | None = None,
    ) -> None:
        """Save search index to versioned storage.

        Args:
            config: Version configuration
        """
        from ..caching.manager import get_version_manager
        from ..models.versioned import ResourceType, VersionConfig

        manager = get_version_manager()

        # Create index ID
        index_id = f"{self.corpus.corpus_name}:search"

        # Prepare content to save
        content = {
            "corpus_name": self.corpus.corpus_name,
            "semantic_enabled": self.semantic_enabled,
            "semantic_model": self.semantic_model,
            "semantic_index_id": self.semantic_index_id,
            "has_semantic_index": self.has_semantic_index,
        }

        # Save using version manager
        await manager.save(
            resource_id=index_id,
            resource_type=ResourceType.SEARCH,
            namespace=manager._get_namespace(ResourceType.SEARCH),
            content=content,
            config=config or VersionConfig(),
            metadata={
                "corpus_id": self.corpus.corpus_id,
                "corpus_version": self.corpus.vocabulary_hash,
                "index_type": self.index_type,
            },
        )

        logger.info(f"Saved search index for {index_id}")

    @classmethod
    async def get_or_create(
        cls,
        corpus: Corpus,
        semantic_enabled: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
        force_rebuild: bool = False,
        config: Any | None = None,
    ) -> SearchIndex:
        """Get existing search index or create new one.

        Args:
            corpus: Corpus containing vocabulary
            semantic_enabled: Whether semantic search is enabled
            semantic_model: Model for semantic search
            force_rebuild: Force rebuilding even if exists
            config: Version configuration

        Returns:
            SearchIndex instance
        """
        # Try to get existing unless forced rebuild
        if not force_rebuild:
            existing = await cls.get(corpus, semantic_enabled, semantic_model, config)
            if existing:
                return existing

        # Create new index
        index = cls(
            corpus=corpus,
            semantic_enabled=semantic_enabled,
            semantic_model=semantic_model,
        )

        # Build indices
        index.build_trie_index()
        index.build_fuzzy_index()

        # Save the index
        await index.save(config)

        return index


class SearchEngine:
    """High-performance search engine using corpus-based vocabulary.

    Optimized for 100k-1M word searches with minimal overhead.
    """

    # Method priority for deduplication (higher = preferred)
    METHOD_PRIORITY = {
        SearchMethod.EXACT: 3,
        SearchMethod.SEMANTIC: 2,
        SearchMethod.FUZZY: 1,
    }

    def __init__(
        self,
        corpus_name: str,
        min_score: float = DEFAULT_MIN_SCORE,
        semantic: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
        force_rebuild: bool = False,
    ) -> None:
        """Initialize with corpus name and configuration.

        Args:
            corpus_name: Name of corpus to fetch from corpus manager
            min_score: Minimum score threshold for results
            semantic: Enable semantic search (requires ML dependencies)
            semantic_model: Model to use for semantic search (BGE-M3 or MiniLM)
            force_rebuild: Force rebuild of indices and semantic search

        """
        self.corpus_name = corpus_name
        self.min_score = min_score
        self.semantic = semantic
        self.semantic_model = semantic_model
        self.force_rebuild = force_rebuild

        # Corpus will be fetched lazily
        self.corpus: Corpus | None = None
        self._vocabulary_hash: str = ""

        # Initialize components as None - will be lazy loaded
        self.trie_search: TrieSearch | None = None
        self.fuzzy_search: FuzzySearch | None = None
        self.semantic_search: SemanticSearch | None = None

        # Track semantic initialization separately
        self._semantic_ready = False
        self._semantic_init_task: asyncio.Task[None] | None = None

        self._initialized = False

        logger.debug(
            f"SearchEngine created for corpus '{corpus_name}', semantic={'enabled' if self.semantic else 'disabled'}",
        )

    async def initialize(self) -> None:
        """Initialize expensive components lazily with vocab hash-based caching."""
        # Quick vocab hash check - if unchanged, skip re-initialization
        current_vocab_hash = await self._get_current_vocab_hash()
        if (
            self._initialized
            and self._vocabulary_hash == current_vocab_hash
            and self.corpus is not None
        ):
            logger.debug(
                f"SearchEngine for '{self.corpus_name}' already initialized with hash {current_vocab_hash[:8]}",
            )
            return

        logger.info(
            f"Initializing SearchEngine for corpus '{self.corpus_name}' (hash: {current_vocab_hash[:8] if current_vocab_hash else 'unknown'})",
        )

        # Fetch Corpus from corpus manager
        manager = get_corpus_manager()

        # First try to get corpus metadata to get the vocab_hash
        logger.debug(f"Fetching corpus metadata for '{self.corpus_name}'")
        metadata = await manager.get_corpus_metadata(self.corpus_name)

        if metadata is not None:
            logger.debug(
                f"Found metadata for '{self.corpus_name}', vocab hash: {metadata.vocabulary_hash[:8]}",
            )
            # Get corpus from cache using the vocab_hash
            self.corpus = await manager.get_corpus(
                self.corpus_name,
                vocab_hash=metadata.vocabulary_hash,
            )
            if self.corpus:
                logger.debug(f"Successfully loaded corpus '{self.corpus_name}' from cache")
            else:
                logger.warning("Could not load corpus from cache despite metadata existing")
        else:
            logger.warning(f"No metadata found for corpus '{self.corpus_name}'")

        if self.corpus is None:
            logger.error(
                f"Failed to load corpus '{self.corpus_name}' - not found in cache or metadata",
            )
            raise ValueError(
                f"Corpus '{self.corpus_name}' not found. It should have been created by LanguageSearch.initialize() or via get_or_create_corpus().",
            )

        self._vocabulary_hash = self.corpus.vocabulary_hash
        combined_vocab = self.corpus.vocabulary
        logger.debug(f"Corpus loaded with {len(combined_vocab)} vocabulary items")

        # High-performance search components - only initialize if needed
        if not self.trie_search or self.trie_search._vocabulary_hash != self._vocabulary_hash:
            logger.debug("Building/updating Trie index")
            self.trie_search = TrieSearch()
            await self.trie_search.build_index(self.corpus)

        if not self.fuzzy_search:
            logger.debug("Initializing Fuzzy search")
            self.fuzzy_search = FuzzySearch(min_score=self.min_score)

        # Initialize semantic search if enabled - non-blocking background task
        if self.semantic and not self._semantic_ready:
            logger.debug("Semantic search enabled - initializing in background")
            # Fire and forget - semantic search initializes in background
            self._semantic_init_task = asyncio.create_task(self._initialize_semantic_background())

        self._initialized = True

        logger.info(
            f"✅ SearchEngine initialized for corpus '{self.corpus_name}' (hash: {self._vocabulary_hash[:8]})",
        )

    async def _initialize_semantic_background(self) -> None:
        """Initialize semantic search in background without blocking."""
        try:
            if not self.corpus:
                logger.warning("Cannot initialize semantic search without corpus")
                return

            logger.info(f"Starting background semantic initialization for '{self.corpus_name}'")

            # Create semantic search directly
            logger.info(
                f"Creating semantic search for corpus '{self.corpus_name}' with {self.semantic_model} (background)",
            )
            self.semantic_search = SemanticSearch(
                corpus=self.corpus,
                model_name=self.semantic_model,
                force_rebuild=self.force_rebuild,
            )
            await self.semantic_search.initialize()

            self._semantic_ready = True
            logger.info(f"✅ Semantic search ready for '{self.corpus_name}'")

        except Exception as e:
            logger.error(f"Failed to initialize semantic search: {e}")
            self._semantic_ready = False

    async def _get_current_vocab_hash(self) -> str | None:
        """Get current vocabulary hash from corpus manager."""
        try:
            manager = get_corpus_manager()
            metadata = await manager.get_corpus_metadata(self.corpus_name)
            return metadata.vocabulary_hash if metadata else None
        except Exception:
            return None

    async def update_corpus(self) -> None:
        """Check if corpus has changed and update components if needed. Optimized with hash check."""
        if not self.corpus:
            return

        # Quick vocabulary hash check - if unchanged, skip expensive updates
        current_vocab_hash = await self._get_current_vocab_hash()
        if current_vocab_hash == self._vocabulary_hash:
            logger.debug(
                f"Corpus unchanged for '{self.corpus_name}' (hash: {current_vocab_hash[:8] if current_vocab_hash else 'none'})",
            )
            return

        logger.info(
            f"Corpus vocabulary changed for '{self.corpus_name}': {self._vocabulary_hash[:8] if self._vocabulary_hash else 'none'} -> {current_vocab_hash[:8] if current_vocab_hash else 'none'}",
        )

        # Get updated corpus
        manager = get_corpus_manager()
        updated_corpus = await manager.get_corpus(self.corpus_name, vocab_hash=current_vocab_hash)

        if not updated_corpus:
            logger.error(f"Failed to get updated corpus '{self.corpus_name}'")
            return

        # Update corpus and hash
        self.corpus = updated_corpus
        self._vocabulary_hash = updated_corpus.vocabulary_hash

        # Update search components only if needed
        if self.trie_search and self.trie_search._vocabulary_hash != self._vocabulary_hash:
            await self.trie_search.build_index(updated_corpus)

        # Note: FuzzySearch uses corpus on-demand, no rebuild needed
        # Update semantic search if enabled and hash changed
        if (
            self.semantic_search
            and getattr(self.semantic_search, "_vocabulary_hash", None) != self._vocabulary_hash
        ):
            await self.semantic_search.update_corpus(updated_corpus)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Smart cascading search with early termination optimization and caching.

        Automatically selects optimal search methods based on query.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        # Use the new search_with_mode method with SMART mode
        return await self.search_with_mode(
            query=query,
            mode=SearchMode.SMART,
            max_results=max_results,
            min_score=min_score,
        )

    async def search_with_mode(
        self,
        query: str,
        mode: SearchMode,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Search with explicit mode selection.

        Args:
            query: Search query
            mode: Search mode (SMART, EXACT, FUZZY, SEMANTIC)
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        # Ensure initialization
        await self.initialize()

        # Check if corpus has changed and update if needed
        await self.update_corpus()

        # Normalize query using global normalize function
        normalized_query = normalize(query)
        if not normalized_query:
            return []

        min_score = min_score if min_score is not None else self.min_score

        # Perform search based on mode
        if mode == SearchMode.SMART:
            results = await self._smart_search_cascade(
                normalized_query,
                max_results,
                min_score,
                self.semantic,
            )
        elif mode == SearchMode.EXACT:
            results = self.search_exact(normalized_query)
        elif mode == SearchMode.FUZZY:
            results = self.search_fuzzy(normalized_query, max_results, min_score)
        elif mode == SearchMode.SEMANTIC:
            if not self.semantic_search:
                raise ValueError("Semantic search is not enabled for this SearchEngine instance")

            results = self.search_semantic(normalized_query, max_results, min_score)
        else:
            raise ValueError(f"Unsupported search mode: {mode}")

        return results

    def search_exact(
        self,
        query: str,
    ) -> list[SearchResult]:
        """Search using only exact matching.

        Args:
            query: Normalized search query
            max_results: Maximum results to return

        """
        if self.trie_search is None:
            return []

        match = self.trie_search.search_exact(query)

        if match is None:
            return []

        return [
            SearchResult(
                word=self._get_original_word(match),  # Return original word with diacritics
                lemmatized_word=None,
                score=1.0,
                method=SearchMethod.EXACT,
                language=None,
                metadata=None,
            ),
        ]

    def search_fuzzy(
        self,
        query: str,
        max_results: int = 20,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[SearchResult]:
        """Search using only fuzzy matching.

        Args:
            query: Normalized search query
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        if self.fuzzy_search is None or self.corpus is None:
            return []

        try:
            matches = self.fuzzy_search.search(
                query=query,
                corpus=self.corpus,
                max_results=max_results,
                min_score=min_score,
            )

            # Set method and get original words with diacritics
            for match in matches:
                match.method = SearchMethod.FUZZY
                match.word = self._get_original_word(match.word)

            return matches
        except Exception as e:
            logger.warning(f"Fuzzy search failed: {e}")
            return []

    def search_semantic(
        self,
        query: str,
        max_results: int = 20,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[SearchResult]:
        """Search using only semantic matching.

        Args:
            query: Normalized search query
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        # Check if semantic search is ready
        if not self._semantic_ready or not self.semantic_search:
            logger.debug("Semantic search not ready yet - returning empty results")
            return []

        # Perform semantic search
        try:
            return self.semantic_search.search(query, max_results, min_score)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def _smart_search_cascade(
        self,
        query: str,
        max_results: int,
        min_score: float,
        semantic: bool,
    ) -> list[SearchResult]:
        """Sequential search cascade with smart early termination for optimal performance."""
        # 1. Exact search first (fastest) - perfect match early termination
        exact_results = self.search_exact(query)
        if exact_results:
            logger.debug(f"Early exit: {len(exact_results)} exact matches found")
            return exact_results

        # 2. Fuzzy search (most comprehensive for misspellings)
        fuzzy_results = self.search_fuzzy(query, max_results, min_score)

        # 3. Semantic search - adaptive threshold based on fuzzy quality
        semantic_results = []
        if semantic and self.semantic_search:
            # If fuzzy found good results, be more selective with semantic
            semantic_limit = (
                max_results // 2 if len(fuzzy_results) >= max_results // 2 else max_results
            )
            semantic_results = self.search_semantic(query, semantic_limit, min_score)

        # 4. Merge and deduplicate with memory-efficient generators
        fuzzy_gen = (r for r in fuzzy_results if r.score >= min_score)
        semantic_gen = (r for r in semantic_results if r.score >= min_score)

        # Chain all results without creating intermediate lists
        all_results = list(itertools.chain(exact_results, fuzzy_gen, semantic_gen))

        # Deduplicate and sort
        unique_results = self._deduplicate_results(all_results)

        return sorted(unique_results, key=lambda r: r.score, reverse=True)[:max_results]

    async def find_best_match(self, word: str) -> SearchResult | None:
        """Find single best matching word (for word resolution)."""
        results = await self.search(word, max_results=1, min_score=0.0)
        return results[0] if results else None

    def _get_original_word(self, normalized_word: str) -> str:
        """Convert normalized word to original word with diacritics preserved."""
        if not self.corpus:
            return normalized_word

        # Use O(1) dict lookup instead of O(n) list.index()
        idx = self.corpus.vocabulary_to_index.get(normalized_word)
        if idx is not None:
            return self.corpus.get_original_word_by_index(idx)

        return normalized_word

    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicates, preferring exact matches."""
        word_to_result: dict[str, SearchResult] = {}

        for result in results:
            if result.word not in word_to_result:
                word_to_result[result.word] = result
            else:
                existing = word_to_result[result.word]
                # Prefer higher priority methods, then higher scores
                result_priority = self.METHOD_PRIORITY.get(result.method, 0)
                existing_priority = self.METHOD_PRIORITY.get(existing.method, 0)

                if (result_priority > existing_priority) or (
                    result_priority == existing_priority and result.score > existing.score
                ):
                    word_to_result[result.word] = result

        return list(word_to_result.values())

    def get_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        if self.corpus:
            return {
                "vocabulary_size": len(self.corpus.vocabulary),
                "min_score": self.min_score,
                "semantic_enabled": self.semantic,
                "semantic_ready": self._semantic_ready,
                "semantic_model": self.semantic_model if self.semantic else None,
                "corpus_name": self.corpus_name,
            }
        return {
            "vocabulary_size": 0,
            "words": 0,
            "phrases": 0,
            "min_score": self.min_score,
            "semantic_enabled": self.semantic,
            "semantic_ready": False,
            "corpus_name": self.corpus_name,
        }


__all__ = ["SearchEngine", "SearchMode", "SearchResult"]
