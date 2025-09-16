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

        # Track semantic initialization separately
        self._semantic_ready = False
        self._semantic_init_task: asyncio.Task[None] | None = None

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
        corpus = await Corpus.get(
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

        # Load corpus if not already loaded
        if not self.corpus:
            self.corpus = await Corpus.get(
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )

            if not self.corpus:
                raise ValueError(
                    f"Corpus '{self.index.corpus_name}' not found. It should have been created by LanguageSearch.initialize() or via get_or_create_corpus().",
                )

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
            # Fire and forget - semantic search initializes in background
            self._semantic_init_task = asyncio.create_task(self._initialize_semantic_background())

        self._initialized = True

        logger.info(
            f"✅ SearchEngine initialized for corpus '{self.index.corpus_name}' (hash: {self.index.vocabulary_hash[:8]})",
        )

    async def _initialize_semantic_background(self) -> None:
        """Initialize semantic search in background without blocking."""
        try:
            if not self.corpus or not self.index:
                logger.warning("Cannot initialize semantic search without corpus and index")
                return

            logger.info(
                f"Starting background semantic initialization for '{self.index.corpus_name}'"
            )

            # Create semantic search using from_corpus
            logger.info(
                f"Creating semantic search for corpus '{self.index.corpus_name}' with {self.index.semantic_model} (background)",
            )
            self.semantic_search = await SemanticSearch.from_corpus(
                corpus=self.corpus,
                model_name=self.index.semantic_model,  # type: ignore[arg-type]
                config=VersionConfig(),
            )

            self._semantic_ready = True
            logger.info(f"✅ Semantic search ready for '{self.index.corpus_name}'")

        except Exception as e:
            logger.error(f"Failed to initialize semantic search: {e}")
            self._semantic_ready = False

    async def _get_current_vocab_hash(self) -> str | None:
        """Get current vocabulary hash from corpus."""
        if not self.index:
            return None

        try:
            corpus = await Corpus.get(
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )
            return corpus.vocabulary_hash if corpus else None
        except Exception:
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

        # Get updated corpus
        updated_corpus = await Corpus.get(
            corpus_name=self.index.corpus_name,
            config=VersionConfig(),
        )

        if not updated_corpus:
            logger.error(f"Failed to get updated corpus '{self.index.corpus_name}'")
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
                corpus_id=self.corpus.corpus_id,
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
        # If specific method requested, use it
        if method:
            if method == SearchMethod.EXACT and self.trie_search:
                result = self.trie_search.search_exact(query)
                if result:
                    return [SearchResult(word=result, score=1.0, method=SearchMethod.EXACT)]
                return []
            elif method == SearchMethod.FUZZY and self.fuzzy_search and self.corpus:
                results = self.fuzzy_search.search(query, self.corpus)
                return results[:max_results]
            elif method == SearchMethod.SEMANTIC and self.semantic_search:
                return self.semantic_search.search(query, max_results=max_results)

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

        # Check if corpus has changed and update if needed
        await self.update_corpus()

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


__all__ = ["Search", "SearchMode", "SearchResult"]
