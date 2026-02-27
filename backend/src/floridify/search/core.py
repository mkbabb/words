"""Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

import asyncio
import itertools
from typing import Any

from ..caching.models import VersionConfig
from ..corpus.core import Corpus
from ..text import normalize
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod, SearchMode
from .fuzzy import FuzzySearch  # Using RapidFuzz implementation
from .models import SearchIndex, SearchResult
from .semantic.constants import DEFAULT_SENTENCE_MODEL, SemanticModel
from .semantic.core import SemanticSearch
from .trie import TrieSearch

logger = get_logger(__name__)

# Module-level cache for Search instances keyed by (corpus_name, semantic_model)
_search_instance_cache: dict[tuple[str, str], Search] = {}


class Search:
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
        index: SearchIndex | None = None,
        corpus: Corpus | None = None,
    ) -> None:
        """Initialize with search index and optional corpus.

        Args:
            index: Pre-loaded SearchIndex containing all configuration
            corpus: Optional corpus for runtime operations

        """
        # Data model
        self.index = index
        self.corpus = corpus

        # Search components (built from index)
        self.trie_search: TrieSearch | None = None
        self.fuzzy_search: FuzzySearch | None = None
        self.semantic_search: SemanticSearch | None = None

        # Track semantic initialization separately with proper synchronization
        self._semantic_ready = False
        self._semantic_init_task: asyncio.Task[None] | None = None
        self._semantic_init_lock: asyncio.Lock = asyncio.Lock()  # CRITICAL FIX: Prevent race conditions
        self._semantic_init_error: str | None = None  # Track initialization errors

        self._initialized = False

        if index:
            logger.debug(
                f"SearchEngine created for corpus '{index.corpus_name}', semantic={'enabled' if index.semantic_enabled else 'disabled'}",
            )

    @classmethod
    async def from_corpus(
        cls,
        corpus_name: str,
        min_score: float = DEFAULT_MIN_SCORE,
        semantic: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
        config: VersionConfig | None = None,
    ) -> Search:
        """Create SearchEngine from corpus name.

        Args:
            corpus_name: Name of corpus to load
            min_score: Minimum score threshold
            semantic: Enable semantic search
            semantic_model: Model for semantic search
            config: Version configuration

        Returns:
            SearchEngine instance with loaded index

        """
        # Get corpus
        from ..corpus.manager import get_tree_corpus_manager

        manager = get_tree_corpus_manager()
        corpus = await manager.get_corpus(
            corpus_name=corpus_name,
            config=config or VersionConfig(),
        )

        if not corpus:
            raise ValueError(f"Corpus '{corpus_name}' not found")

        # Get or create index
        index = await SearchIndex.get_or_create(
            corpus=corpus,
            min_score=min_score,
            semantic=semantic,
            semantic_model=semantic_model,
            config=config or VersionConfig(),
        )

        # Create engine with index
        engine = cls(index=index, corpus=corpus)
        await engine.initialize()

        return engine

    @classmethod
    async def get_or_create(
        cls,
        corpus_name: str,
        min_score: float = DEFAULT_MIN_SCORE,
        semantic: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
        config: VersionConfig | None = None,
    ) -> Search:
        """Get cached Search instance or create and cache a new one."""
        force_rebuild = config.force_rebuild if config else False
        cache_key = (corpus_name, str(semantic_model))

        if not force_rebuild and cache_key in _search_instance_cache:
            cached = _search_instance_cache[cache_key]
            if cached._initialized:
                return cached

        instance = await cls.from_corpus(
            corpus_name=corpus_name,
            min_score=min_score,
            semantic=semantic,
            semantic_model=semantic_model,
            config=config,
        )
        _search_instance_cache[cache_key] = instance
        return instance

    async def initialize(self) -> None:
        """Initialize expensive components lazily with vocab hash-based caching."""
        if not self.index:
            raise ValueError("Index required for initialization")

        # Quick vocab hash check - if unchanged, skip re-initialization
        if (
            self._initialized
            and self.corpus
            and self.index.vocabulary_hash == self.corpus.vocabulary_hash
        ):
            logger.debug(
                f"SearchEngine for '{self.index.corpus_name}' already initialized with hash {self.index.vocabulary_hash[:8]}",
            )
            return

        logger.info(
            f"Initializing SearchEngine for corpus '{self.index.corpus_name}' (hash: {self.index.vocabulary_hash[:8]})",
        )

        # Load corpus if not already loaded - use corpus_uuid for lookup
        if not self.corpus:
            from ..corpus.manager import get_tree_corpus_manager

            manager = get_tree_corpus_manager()
            self.corpus = await manager.get_corpus(
                corpus_uuid=self.index.corpus_uuid,
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )

            if not self.corpus:
                raise ValueError(
                    f"Corpus '{self.index.corpus_name}' (UUID: {self.index.corpus_uuid}) not found. "
                    f"It should have been created by LanguageSearch.initialize() or via get_or_create_corpus()."
                )

        # CRITICAL FIX: Validate UUID consistency between index and corpus
        if self.corpus.corpus_uuid != self.index.corpus_uuid:
            raise ValueError(
                f"UUID MISMATCH: SearchIndex references corpus_uuid={self.index.corpus_uuid}, "
                f"but loaded corpus has corpus_uuid={self.corpus.corpus_uuid}. "
                f"This indicates index corruption or stale cache. "
                f"Solution: Rebuild search index for corpus '{self.corpus.corpus_name}'."
            )

        # CRITICAL FIX: Validate vocabulary hash consistency - auto-rebuild if stale
        if self.corpus.vocabulary_hash != self.index.vocabulary_hash:
            logger.warning(
                f"VOCABULARY HASH MISMATCH: SearchIndex has hash {self.index.vocabulary_hash[:8]}, "
                f"but corpus has hash {self.corpus.vocabulary_hash[:8]}. "
                f"Index will be rebuilt automatically."
            )
            # Preserve semantic settings before rebuild
            semantic_was_enabled = self.index.semantic_enabled

            # Trigger automatic rebuild
            await self.build_indices()
            self.index.vocabulary_hash = self.corpus.vocabulary_hash

            # Restore semantic settings after rebuild
            self.index.semantic_enabled = semantic_was_enabled
            self.index.has_semantic = semantic_was_enabled

            # Save updated index
            # PATHOLOGICAL REMOVAL: No hasattr - direct method call
            # SearchIndex always has save() method
            await self.index.save()
            logger.info(f"✅ Search indices rebuilt for corpus '{self.corpus.corpus_name}'")

            # CRITICAL: Initialize semantic search if it was enabled
            if semantic_was_enabled and not self._semantic_ready:
                logger.info("Re-initializing semantic search after vocabulary rebuild")
                async with self._semantic_init_lock:
                    if not self._semantic_ready and self._semantic_init_task is None:
                        self._semantic_init_task = asyncio.create_task(self._initialize_semantic_background())

            return  # Skip rest of initialization since build_indices() already did it

        combined_vocab = self.corpus.vocabulary
        logger.debug(f"Corpus loaded with {len(combined_vocab)} vocabulary items")

        # High-performance search components - only initialize if needed
        if self.index.has_trie:
            logger.debug("Building/updating Trie index")
            self.trie_search = await TrieSearch.from_corpus(self.corpus)

        if self.index.has_fuzzy:
            logger.debug("Initializing Fuzzy search")
            self.fuzzy_search = FuzzySearch(min_score=self.index.min_score)

        # Initialize semantic search if enabled - non-blocking background task
        if self.index.semantic_enabled and not self._semantic_ready:
            logger.debug("Semantic search enabled - initializing in background")
            # CRITICAL FIX: Use lock to prevent duplicate initialization tasks
            async with self._semantic_init_lock:
                # Double-check after acquiring lock
                if not self._semantic_ready and self._semantic_init_task is None:
                    self._semantic_init_task = asyncio.create_task(self._initialize_semantic_background())

        self._initialized = True

        logger.info(
            f"✅ SearchEngine initialized for corpus '{self.index.corpus_name}' (hash: {self.index.vocabulary_hash[:8]})",
        )

    async def _initialize_semantic_background(self) -> None:
        """Initialize semantic search in background without blocking.

        CRITICAL FIX: Uses lock to ensure thread safety and proper error state management.
        """
        try:
            if not self.corpus or not self.index:
                error_msg = (
                    f"Cannot initialize semantic search: "
                    f"corpus={'present' if self.corpus else 'missing'}, "
                    f"index={'present' if self.index else 'missing'}"
                )
                logger.error(error_msg)
                async with self._semantic_init_lock:
                    self._semantic_ready = False
                    self._semantic_init_error = error_msg
                return

            logger.info(
                f"Starting background semantic initialization for '{self.index.corpus_name}' "
                f"with model '{self.index.semantic_model}'"
            )

            # Create semantic search using from_corpus (this now ensures embeddings are built)
            semantic_search = await SemanticSearch.from_corpus(
                corpus=self.corpus,
                model_name=self.index.semantic_model,  # type: ignore[arg-type]
                config=VersionConfig(),
            )

            # FIX: Verify embeddings were actually built
            # Use `is None` instead of `not` to avoid NumPy array truth value ambiguity
            if (
                semantic_search.sentence_embeddings is None
                or semantic_search.sentence_embeddings.size == 0
            ):
                raise RuntimeError(
                    f"Semantic search initialization completed but no embeddings generated "
                    f"for '{self.index.corpus_name}'"
                )

            if semantic_search.sentence_index is None:
                raise RuntimeError(
                    f"Semantic search initialization completed but no FAISS index created "
                    f"for '{self.index.corpus_name}'"
                )

            # Atomically update state with lock
            async with self._semantic_init_lock:
                self.semantic_search = semantic_search
                self._semantic_ready = True
                self._semantic_init_error = None

            logger.info(
                f"✅ Semantic search ready for '{self.index.corpus_name}' "
                f"({semantic_search.index.num_embeddings:,} embeddings, "
                f"{semantic_search.index.embedding_dimension}D)"
            )

        except Exception as e:
            corpus_name = self.index.corpus_name if self.index else "unknown"
            logger.error(
                f"Failed to initialize semantic search for '{corpus_name}': {e}",
                exc_info=True,  # FIX: Include full traceback for debugging
            )
            # Atomically update error state with lock
            async with self._semantic_init_lock:
                self._semantic_ready = False
                self._semantic_init_error = str(e)

    async def await_semantic_ready(self) -> None:
        """Wait for semantic search to be ready (useful for tests).

        CRITICAL FIX: Properly checks task state with lock to avoid race conditions.
        """
        # Check if initialization is needed
        async with self._semantic_init_lock:
            if self._semantic_ready:
                return  # Already ready
            task = self._semantic_init_task

        # Wait for task outside of lock to avoid deadlock
        if task and not task.done():
            await task

    async def _get_current_vocab_hash(self) -> str | None:
        """Get current vocabulary hash from corpus."""
        if not self.index:
            return None

        try:
            # Try with corpus_uuid first, fallback to corpus_name
            from ..corpus.manager import get_tree_corpus_manager

            manager = get_tree_corpus_manager()
            corpus = await manager.get_corpus(
                corpus_uuid=self.index.corpus_uuid,
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )
            return corpus.vocabulary_hash if corpus else None
        except Exception as e:
            logger.warning(f"Failed to get current vocab hash for '{self.index.corpus_name}': {e}")
            return None

    async def update_corpus(self) -> None:
        """Check if corpus has changed and update components if needed. Optimized with hash check."""
        if not self.corpus or not self.index:
            return

        # Quick vocabulary hash check - if unchanged, skip expensive updates
        current_vocab_hash = await self._get_current_vocab_hash()
        if current_vocab_hash == self.index.vocabulary_hash:
            logger.debug(
                f"Corpus unchanged for '{self.index.corpus_name}' (hash: {current_vocab_hash[:8] if current_vocab_hash else 'none'})",
            )
            return

        logger.info(
            f"Corpus vocabulary changed for '{self.index.corpus_name}': {self.index.vocabulary_hash[:8]} -> {current_vocab_hash[:8] if current_vocab_hash else 'none'}",
        )

        # Get updated corpus - use corpus_uuid and corpus_name
        from ..corpus.manager import get_tree_corpus_manager

        manager = get_tree_corpus_manager()
        updated_corpus = await manager.get_corpus(
            corpus_uuid=self.index.corpus_uuid,
            corpus_name=self.index.corpus_name,
            config=VersionConfig(),
        )

        if not updated_corpus:
            logger.error(
                f"Failed to get updated corpus '{self.index.corpus_name}' (UUID: {self.index.corpus_uuid}). "
                f"Corpus may have been deleted or cache is stale."
            )
            return

        # Update corpus and index hash
        self.corpus = updated_corpus
        self.index.vocabulary_hash = updated_corpus.vocabulary_hash

        # Update search components only if needed
        if self.trie_search:
            self.trie_search = await TrieSearch.from_corpus(updated_corpus)

        # Note: FuzzySearch uses corpus on-demand, no rebuild needed
        # Update semantic search if enabled and hash changed
        if self.semantic_search:
            await self.semantic_search.update_corpus(updated_corpus)

    async def build_indices(self) -> None:
        """Build search indices from corpus.

        Creates trie and fuzzy indices. For semantic, use initialize() instead.
        """
        if not self.corpus:
            raise ValueError("Corpus required to build indices")

        # Create minimal index if not present
        if not self.index:
            from .models import SearchIndex

            self.index = SearchIndex(
                corpus_name=self.corpus.corpus_name,
                corpus_uuid=self.corpus.corpus_uuid or "",  # Use empty string if None
                vocabulary_hash=self.corpus.vocabulary_hash,
                min_score=DEFAULT_MIN_SCORE,
                has_trie=True,
                has_fuzzy=True,
                semantic_enabled=False,
            )

        # Build trie index
        self.trie_search = await TrieSearch.from_corpus(self.corpus)
        self.index.has_trie = True

        # Build fuzzy index
        self.fuzzy_search = FuzzySearch(min_score=self.index.min_score)
        self.index.has_fuzzy = True

        self._initialized = True

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        method: SearchMethod | None = None,
    ) -> list[SearchResult]:
        """Smart cascading search with early termination optimization and caching.

        Automatically selects optimal search methods based on query.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            method: Optional specific search method to use

        """
        # Normalize query once at entry point
        normalized_query = normalize(query)

        # If specific method requested, use it
        if method:
            if method == SearchMethod.EXACT and self.trie_search:
                result = self.trie_search.search_exact(normalized_query)
                if result:
                    # Map back to original form with diacritics if available
                    original = self._get_original_word(result)
                    return [
                        SearchResult(
                            word=original,
                            score=1.0,
                            method=SearchMethod.EXACT,
                            lemmatized_word=None,
                            language=self.corpus.language if self.corpus else None,
                            metadata=None,
                        )
                    ]
                return []
            elif method == SearchMethod.PREFIX and self.trie_search:
                matches = self.trie_search.search_prefix(normalized_query, max_results=max_results)
                # Map back to original forms with diacritics
                results = []
                for match in matches:
                    original = self._get_original_word(match)
                    results.append(
                        SearchResult(
                            word=original,
                            score=1.0,
                            method=SearchMethod.PREFIX,
                            lemmatized_word=None,
                            language=self.corpus.language if self.corpus else None,
                            metadata=None,
                        )
                    )
                return results
            elif method == SearchMethod.FUZZY and self.fuzzy_search and self.corpus:
                results = self.fuzzy_search.search(normalized_query, self.corpus)
                if min_score is not None:
                    results = [r for r in results if r.score >= min_score]
                # Restore diacritics
                for result in results:
                    result.word = self._get_original_word(result.word)
                return results[:max_results]
            elif method == SearchMethod.SEMANTIC and self.semantic_search:
                results = await self.semantic_search.search(
                    normalized_query, max_results=max_results
                )
                # Restore diacritics
                for result in results:
                    result.word = self._get_original_word(result.word)
                return results

        # Otherwise use smart mode
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

        # OPTIMIZATION: Removed update_corpus() from hot path
        # The corpus hash is checked during initialization only
        # This saves ~0.5-1ms per search by avoiding redundant DB queries

        # Normalize query using global normalize function
        normalized_query = normalize(query)
        if not normalized_query:
            return []

        min_score = (
            min_score
            if min_score is not None
            else (self.index.min_score if self.index else DEFAULT_MIN_SCORE)
        )

        # Perform search based on mode
        if mode == SearchMode.SMART:
            results = await self._smart_search_cascade(
                normalized_query,
                max_results,
                min_score,
                self.index.semantic_enabled if self.index else False,
            )
        elif mode == SearchMode.EXACT:
            results = self.search_exact(normalized_query)
        elif mode == SearchMode.FUZZY:
            results = self.search_fuzzy(normalized_query, max_results, min_score)
        elif mode == SearchMode.SEMANTIC:
            # Wait for semantic search to be ready if it's being initialized
            # CRITICAL FIX: Use await_semantic_ready for proper synchronization
            await self.await_semantic_ready()

            if not self.semantic_search:
                raise ValueError("Semantic search is not enabled for this SearchEngine instance")

            results = await self.search_semantic(normalized_query, max_results, min_score)
        else:
            raise ValueError(f"Unsupported search mode: {mode}")

        return results

    def search_exact(
        self,
        query: str,
    ) -> list[SearchResult]:
        """Search using only exact matching.

        PERFORMANCE OPTIMIZED: This is the hot path for exact searches.
        Every microsecond counts here.

        Args:
            query: Search query (will be normalized)

        """
        if self.trie_search is None:
            return []

        # Normalize at entry point (cached via LRU)
        normalized_query = normalize(query)

        # Fast path: marisa-trie lookup (O(m) where m = query length)
        match = self.trie_search.search_exact(normalized_query)

        if match is None:
            return []

        # Inline _get_original_word for performance (avoid function call overhead)
        # This is the second hottest path after trie lookup
        original_word = match  # Default to normalized word
        if self.corpus:
            # O(1) dict lookup - pre-built index
            idx = self.corpus.vocabulary_to_index.get(match)
            if idx is not None:
                # Get original form with diacritics (O(1) list access + dict lookup)
                if original_indices := self.corpus.normalized_to_original_indices.get(idx):
                    original_word = self.corpus.original_vocabulary[original_indices[0]]

        # Construct result inline to avoid function call
        return [
            SearchResult(
                word=original_word,
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
            query: Search query (will be normalized)
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        if self.fuzzy_search is None or self.corpus is None:
            return []

        try:
            # Normalize at entry point
            normalized_query = normalize(query)
            matches = self.fuzzy_search.search(
                query=normalized_query,
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

    def search_prefix(
        self,
        prefix: str,
        max_results: int = 20,
    ) -> list[str]:
        """Search for words starting with the given prefix.

        Args:
            prefix: Prefix to search for
            max_results: Maximum results to return

        Returns:
            List of words starting with prefix (plain strings, not SearchResults)

        """
        if self.trie_search is None:
            return []

        # Normalize at entry point
        normalized_prefix = normalize(prefix)
        matches = self.trie_search.search_prefix(normalized_prefix, max_results=max_results)

        # Return original words with diacritics
        return [self._get_original_word(match) for match in matches]

    async def search_semantic(
        self,
        query: str,
        max_results: int = 20,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> list[SearchResult]:
        """Search using only semantic matching.

        Args:
            query: Search query (will be normalized)
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        # Check if semantic search is ready
        if not self._semantic_ready or not self.semantic_search:
            logger.debug("Semantic search not ready yet - returning empty results")
            return []

        # Perform semantic search
        try:
            # Normalize at entry point
            normalized_query = normalize(query)
            results = await self.semantic_search.search(normalized_query, max_results, min_score)
            # Restore diacritics in semantic results
            for result in results:
                result.word = self._get_original_word(result.word)
            return results
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def cascade_search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Cascading search with automatic method fallback.

        Tries methods in order: exact → fuzzy → semantic (if enabled).

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold

        Returns:
            List of search results from the first method that finds matches
        """
        # Try exact match first
        results = await self.search(query, method=SearchMethod.EXACT, max_results=max_results)
        if results:
            return results

        # Fall back to fuzzy
        results = await self.search(
            query, method=SearchMethod.FUZZY, max_results=max_results, min_score=min_score
        )
        if results:
            return results

        # Finally try semantic if enabled
        if self.semantic_search:
            results = await self.search(
                query, method=SearchMethod.SEMANTIC, max_results=max_results, min_score=min_score
            )

        return results if results else []

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

        # 3. Semantic search - quality-based gating for optimal performance
        semantic_results = []
        if semantic:
            # CRITICAL FIX: In SMART mode, only use semantic if already ready - don't block!
            # This allows search to return immediately with exact/fuzzy results
            # while semantic builds in background
            if self._semantic_ready and self.semantic_search:
                # Quality-based gating: skip semantic if fuzzy found high-quality results
                high_quality_fuzzy = [r for r in fuzzy_results if r.score >= 0.7]
                sufficient_high_quality = len(high_quality_fuzzy) >= max_results // 3

                if sufficient_high_quality:
                    # Skip semantic - fuzzy found enough high-quality matches
                    logger.debug(
                        f"Skipping semantic search: {len(high_quality_fuzzy)} high-quality fuzzy matches (≥0.7 score)"
                    )
                elif len(fuzzy_results) >= max_results // 2:
                    # Fuzzy found results but lower quality - supplement with semantic
                    semantic_limit = max_results // 2
                    semantic_results = await self.search_semantic(query, semantic_limit, min_score)
                    logger.debug(
                        f"Supplementing {len(fuzzy_results)} fuzzy results with semantic search"
                    )
                else:
                    # Fuzzy struggled - rely on semantic
                    semantic_limit = max_results
                    semantic_results = await self.search_semantic(query, semantic_limit, min_score)
                    logger.debug(
                        f"Fuzzy found only {len(fuzzy_results)} results, using full semantic search"
                    )

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
        """Convert normalized word to original word with diacritics preserved.

        Args:
            normalized_word: The normalized word from search results

        Returns:
            Original word with diacritics if available

        """
        if not self.corpus:
            return normalized_word

        # Use O(1) dict lookup instead of O(n) list.index()
        idx = self.corpus.vocabulary_to_index.get(normalized_word)
        if idx is not None:
            original = self.corpus.get_original_word_by_index(idx)
            if original:
                return original

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
        if not self.index:
            return {
                "vocabulary_size": 0,
                "min_score": DEFAULT_MIN_SCORE,
                "semantic_enabled": False,
                "semantic_ready": False,
                "corpus_name": "",
            }

        return {
            "vocabulary_size": self.index.vocabulary_size,
            "min_score": self.index.min_score,
            "semantic_enabled": self.index.semantic_enabled,
            "semantic_ready": self._semantic_ready,
            "semantic_model": (self.index.semantic_model if self.index.semantic_enabled else None),
            "corpus_name": self.index.corpus_name,
        }


def reset_search_cache() -> None:
    """Clear the search instance cache."""
    _search_instance_cache.clear()


__all__ = ["Search", "SearchMode", "SearchResult", "reset_search_cache"]
