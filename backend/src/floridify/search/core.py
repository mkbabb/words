"""
Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

import itertools
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

from ..caching.unified import UnifiedCache, get_unified
from ..text import normalize_comprehensive
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod, SearchMode
from .corpus.core import Corpus
from .corpus.manager import get_corpus_manager
from .fuzzy import FuzzySearch
from .models import SearchResult
from .semantic.core import SemanticSearch
from .semantic.manager import get_semantic_search_manager
from .trie import TrieSearch

logger = get_logger(__name__)


class SearchEngine:
    """
    High-performance search engine using corpus-based vocabulary.

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
        force_rebuild: bool = False,
    ) -> None:
        """Initialize with corpus name and configuration.

        Args:
            corpus_name: Name of corpus to fetch from corpus manager
            min_score: Minimum score threshold for results
            semantic: Enable semantic search (requires ML dependencies)
            force_rebuild: Force rebuild of indices and semantic search
        """
        self.corpus_name = corpus_name
        self.min_score = min_score
        self.semantic = semantic
        self.force_rebuild = force_rebuild

        # Corpus will be fetched lazily
        self.corpus: Corpus | None = None
        self._vocabulary_hash: str = ""

        # Initialize components as None - will be lazy loaded
        self.trie_search: TrieSearch | None = None
        self.fuzzy_search: FuzzySearch | None = None
        self.semantic_search: SemanticSearch | None = None
        self._cache: UnifiedCache | None = None

        self._initialized = False

        logger.debug(
            f"SearchEngine created for corpus '{corpus_name}', semantic={'enabled' if self.semantic else 'disabled'}"
        )

    async def initialize(self) -> None:
        """Initialize expensive components lazily."""
        if self._initialized:
            logger.debug(f"SearchEngine for '{self.corpus_name}' already initialized")
            return

        logger.info(f"Initializing SearchEngine for corpus '{self.corpus_name}'")

        # Fetch Corpus from corpus manager
        manager = get_corpus_manager()

        # First try to get corpus metadata to get the vocab_hash
        logger.debug(f"Fetching corpus metadata for '{self.corpus_name}'")
        metadata = await manager.get_corpus_metadata(self.corpus_name)

        if metadata is not None:
            logger.info(f"Found metadata for '{self.corpus_name}', fetching corpus with metadata hash: {metadata.vocabulary_hash}")
            # Get corpus from cache using the vocab_hash
            self.corpus = await manager.get_corpus(
                self.corpus_name, vocab_hash=metadata.vocabulary_hash
            )
            if self.corpus:
                logger.info(f"Successfully loaded corpus '{self.corpus_name}' from cache")
            else:
                logger.warning("Could not load corpus from cache despite metadata existing")
        else:
            logger.warning(f"No metadata found for corpus '{self.corpus_name}'")

        if self.corpus is None:
            logger.error(f"Failed to load corpus '{self.corpus_name}' - not found in cache or metadata")
            raise ValueError(
                f"Corpus '{self.corpus_name}' not found. It should have been created by LanguageSearch.initialize() or via get_or_create_corpus()."
            )

        self._vocabulary_hash = self.corpus.vocabulary_hash
        combined_vocab = self.corpus.vocabulary
        logger.info(f"Corpus loaded with {len(combined_vocab)} vocabulary items, corpus hash: {self._vocabulary_hash}")

        # High-performance search components
        logger.debug("Building Trie index")
        self.trie_search = TrieSearch()
        await self.trie_search.build_index(combined_vocab)
        logger.debug("Building Fuzzy search")
        self.fuzzy_search = FuzzySearch(min_score=self.min_score)

        # Initialize semantic search if enabled
        if self.semantic:
            logger.debug("Initializing semantic search")
            # Get or create semantic search from manager
            semantic_manager = get_semantic_search_manager()
            self.semantic_search = await semantic_manager.get_semantic_search(
                corpus_name=self.corpus_name, vocab_hash=self.corpus.vocabulary_hash
            )
            if not self.semantic_search:
                # Create semantic search if not found in cache
                logger.info(f"Creating new semantic search for corpus '{self.corpus_name}'")
                self.semantic_search = await semantic_manager.create_semantic_search(
                    corpus_name=self.corpus_name,
                    corpus=self.corpus,
                    force_rebuild=self.force_rebuild,
                )
            else:
                logger.debug(f"Using cached semantic search for '{self.corpus_name}'")

        self._initialized = True

        logger.info(f"✅ SearchEngine fully initialized for corpus '{self.corpus_name}' with hash {self._vocabulary_hash} (semantic={'enabled' if self.semantic else 'disabled'})")

    async def _check_and_update_corpus(self) -> None:
        """Check if corpus has changed and update components if needed."""
        if not self.corpus:
            return

        # Get latest corpus metadata
        manager = get_corpus_manager()
        corpus_metadata = await manager.get_corpus_metadata(self.corpus_name)

        if not corpus_metadata:
            logger.debug(f"Corpus metadata not found for '{self.corpus_name}' during update check")
            return

        # Check if vocabulary has changed
        if corpus_metadata.vocabulary_hash != self._vocabulary_hash:
            logger.info(f"Corpus vocabulary changed for '{self.corpus_name}': {self._vocabulary_hash} -> {corpus_metadata.vocabulary_hash}, updating components")

            # Get updated corpus
            updated_corpus = await manager.get_corpus(
                self.corpus_name, vocab_hash=corpus_metadata.vocabulary_hash
            )

            if not updated_corpus:
                logger.error(f"Failed to get updated corpus '{self.corpus_name}'")
                return

            # Update corpus and hash
            self.corpus = updated_corpus
            self._vocabulary_hash = updated_corpus.vocabulary_hash

            # Update search components
            combined_vocab = updated_corpus.vocabulary

            if self.trie_search:
                await self.trie_search.build_index(combined_vocab)

            # Update semantic search if enabled
            if self.semantic_search and updated_corpus:
                await self.semantic_search.update_corpus(updated_corpus)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """
        Smart cascading search with early termination optimization and caching.

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
        """
        Search with explicit mode selection.

        Args:
            query: Search query
            mode: Search mode (SMART, EXACT, FUZZY, SEMANTIC)
            max_results: Maximum results to return
            min_score: Minimum score threshold
        """
        # Ensure initialization
        await self.initialize()

        # Check if corpus has changed and update if needed
        await self._check_and_update_corpus()

        # Normalize query - use comprehensive to match corpus normalization
        normalized_query = normalize_comprehensive(query)
        if not normalized_query:
            return []

        min_score_threshold = min_score if min_score is not None else self.min_score

        # Determine if semantic search should be used (for SMART mode)
        should_semantic = self.semantic

        # # Get unified cache (L1 memory + L2 filesystem)
        # if self._cache is None:
        #     self._cache = await get_unified()

        # # Generate cache key
        # cache_key = f"{normalized_query}:{mode.value}:{max_results}:{min_score_threshold}:{self.corpus_name}"

        # # Try to get from cache
        # if self._cache is not None:
        #     cached_results: list[SearchResult] | None = await self._cache.get("search", cache_key)
        #     if cached_results is not None:
        #         logger.debug(f"Search cache hit for query: {query[:50]} mode: {mode.value}")
        #         return cached_results

        # Perform search based on mode
        if mode == SearchMode.SMART:
            results = await self._smart_search_cascade(
                normalized_query, max_results, min_score_threshold, should_semantic
            )
        elif mode == SearchMode.EXACT:
            results = await self.search_exact(normalized_query, max_results)
        elif mode == SearchMode.FUZZY:
            results = await self.search_fuzzy(normalized_query, max_results, min_score_threshold)
        elif mode == SearchMode.SEMANTIC:
            results = await self.search_semantic(normalized_query, max_results, min_score_threshold)
        else:
            logger.warning(f"Unknown search mode: {mode}, falling back to SMART")
            results = await self._smart_search_cascade(
                normalized_query, max_results, min_score_threshold, should_semantic
            )

        # # Cache results (1 hour TTL for search results)
        # if self._cache is not None:
        #     await self._cache.set("search", cache_key, results, ttl=timedelta(hours=1))

        return results

    async def search_exact(self, query: str, max_results: int = 20) -> list[SearchResult]:
        """
        Search using only exact matching.

        Args:
            query: Normalized search query
            max_results: Maximum results to return
        """
        if self.trie_search is None:
            return []
        matches = self.trie_search.search_exact(query)
        return [
            SearchResult(
                word=self._get_original_word(match),  # Return original word with diacritics
                lemmatized_word=None,
                score=1.0,
                method=SearchMethod.EXACT,
                language=None,
                metadata=None,
            )
            for match in matches[:max_results]
        ]

    async def search_fuzzy(
        self, query: str, max_results: int = 20, min_score: float = DEFAULT_MIN_SCORE
    ) -> list[SearchResult]:
        """
        Search using only fuzzy matching.

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

    async def search_semantic(
        self, query: str, max_results: int = 20, min_score: float = DEFAULT_MIN_SCORE
    ) -> list[SearchResult]:
        """
        Search using only semantic matching.

        Args:
            query: Normalized search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
        """
        if not self.semantic_search:
            logger.debug("Semantic search not available")
            return []

        # Perform semantic search
        try:
            matches = await self.semantic_search.search(query, max_results, min_score)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

        # Debug: Log semantic results
        if matches:
            logger.debug(f"Semantic search returned {len(matches)} matches: {matches[:3]}")
        else:
            logger.debug(f"Semantic search returned no matches for '{query}'")

        return [
            SearchResult(
                word=match.word,
                lemmatized_word=None,
                score=match.score,
                method=SearchMethod.SEMANTIC,
                language=None,
                metadata=None,
            )
            for match in matches
        ]

    async def _smart_search_cascade(
        self, query: str, max_results: int, min_score_threshold: float, should_semantic: bool
    ) -> list[SearchResult]:
        """Parallel search cascade using ThreadPoolExecutor for CPU-bound operations."""

        # Execute CPU-bound searches in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit exact and fuzzy searches to thread pool
            exact_future = executor.submit(self._search_exact_sync, query)
            fuzzy_future = executor.submit(self._search_fuzzy_sync, query, max_results * 2)

            # Get exact results first for early termination check
            exact_results = exact_future.result(timeout=0.1)  # 100ms timeout for exact
            exact_filtered = [r for r in exact_results if r.score >= min_score_threshold]

            # Early termination for perfect exact matches
            if len(exact_filtered) >= max_results and all(
                r.score >= 0.99 for r in exact_filtered[:max_results]
            ):
                logger.debug(f"Early exit: {len(exact_filtered)} perfect exact matches found")
                # Cancel fuzzy if still running (though it should be fast)
                fuzzy_future.cancel()
                return exact_filtered[:max_results]

            # Get fuzzy results
            fuzzy_results = fuzzy_future.result(timeout=0.5)  # 500ms timeout for fuzzy

        # Semantic search remains async (I/O-bound model inference)
        semantic_results = []
        if should_semantic and self.semantic_search is not None:
            semantic_results = await self._search_semantic(query, max_results, min_score_threshold)

        # Use generators with itertools.chain for memory efficiency
        exact_gen = (r for r in exact_filtered)
        fuzzy_gen = (r for r in fuzzy_results if r.score >= min_score_threshold)
        semantic_gen = (r for r in semantic_results if r.score >= min_score_threshold)

        # Chain all results without creating intermediate lists
        all_results = list(itertools.chain(exact_gen, fuzzy_gen, semantic_gen))

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

    def _search_exact_sync(self, query: str) -> list[SearchResult]:
        """Exact string matching - synchronous."""
        if self.trie_search is None:
            return []
        matches = self.trie_search.search_exact(query)
        return [
            SearchResult(
                word=self._get_original_word(match),  # Return original word with diacritics
                lemmatized_word=None,
                score=1.0,
                method=SearchMethod.EXACT,
                language=None,
                metadata=None,
            )
            for match in matches
        ]

    def _search_fuzzy_sync(self, query: str, max_results: int) -> list[SearchResult]:
        """Fuzzy matching using corpus object."""
        if self.fuzzy_search is None or self.corpus is None:
            return []

        try:
            matches = self.fuzzy_search.search(
                query=query,
                corpus=self.corpus,
                max_results=max_results,
            )

            return [
                SearchResult(
                    word=self._get_original_word(
                        match.word
                    ),  # Return original word with diacritics
                    lemmatized_word=None,
                    score=match.score,
                    method=SearchMethod.FUZZY,
                    language=None,
                    metadata=None,
                )
                for match in matches
            ]
        except Exception as e:
            logger.warning(f"Fuzzy search failed: {e}")
            return []

    async def _search_semantic(
        self, query: str, max_results: int, min_score: float
    ) -> list[SearchResult]:
        """Semantic similarity search using embeddings."""
        if not self.semantic_search:
            logger.debug("Semantic search not available")
            return []

        # Perform semantic search
        try:
            matches = await self.semantic_search.search(query, max_results, min_score)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

        # Debug: Log semantic results
        if matches:
            logger.debug(f"Semantic search returned {len(matches)} matches: {matches[:3]}")
        else:
            logger.debug(f"Semantic search returned no matches for '{query}'")

        return [
            SearchResult(
                word=match.word,
                lemmatized_word=None,
                score=match.score,
                method=SearchMethod.SEMANTIC,
                language=None,
                metadata=None,
            )
            for match in matches
        ]

    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicates, preferring exact matches."""
        word_to_result: dict[str, SearchResult] = {}

        for result in results:
            word_key = result.word.lower().strip()

            if word_key not in word_to_result:
                word_to_result[word_key] = result
            else:
                existing = word_to_result[word_key]
                # Prefer higher priority methods, then higher scores
                result_priority = self.METHOD_PRIORITY.get(result.method, 0)
                existing_priority = self.METHOD_PRIORITY.get(existing.method, 0)

                if (result_priority > existing_priority) or (
                    result_priority == existing_priority and result.score > existing.score
                ):
                    word_to_result[word_key] = result

        return list(word_to_result.values())

    @property
    def semantic_enabled(self) -> bool:
        """Check if semantic search is available and enabled."""
        return self.semantic

    def get_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        if self.corpus:
            return {
                "vocabulary_size": len(self.corpus.vocabulary),
                "min_score": self.min_score,
                "semantic_enabled": self.semantic,
                "semantic_available": True,
                "corpus_name": self.corpus_name,
            }
        else:
            return {
                "vocabulary_size": 0,
                "words": 0,
                "phrases": 0,
                "min_score": self.min_score,
                "semantic_enabled": self.semantic,
                "semantic_available": True,
                "corpus_name": self.corpus_name,
            }


__all__ = ["SearchEngine", "SearchResult", "SearchMode"]
