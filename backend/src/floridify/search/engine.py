"""Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

import asyncio
import itertools
from difflib import SequenceMatcher
from typing import Any

from ..caching.models import VersionConfig
from ..corpus.core import Corpus
from ..text import normalize
from ..utils.logging import get_logger
from .config import (
    HIGH_QUALITY_FUZZY_SCORE,
    LEXICAL_GATE_SCORE_MARGIN,
    LEXICAL_SANITY_THRESHOLD,
    SEMANTIC_FALLBACK_MIN_SCORE,
    SEMANTIC_PHRASE_MIN_SCORE,
    SEMANTIC_SINGLE_WORD_MIN_SCORE,
    SEMANTIC_SMALL_CORPUS_PHRASE_FLOOR,
    SEMANTIC_SMALL_CORPUS_SIZE,
    SEMANTIC_SMALL_CORPUS_WORD_FLOOR,
)
from .constants import DEFAULT_MIN_SCORE, SearchError, SearchMethod, SearchMode
from .fuzzy.bk_tree import BKTree
from .fuzzy.index import FuzzyIndex
from .fuzzy.search import FuzzySearch  # Multi-strategy fuzzy pipeline
from .fuzzy.suffix_array import SuffixArray
from .index import SearchIndex
from .phonetic.index import PhoneticIndex
from .result import MatchDetail, SearchResult
from .semantic.constants import DEFAULT_SENTENCE_MODEL, SemanticModel
from .semantic.search import SemanticSearch
from .cache import get_cached_search, put_cached_search
from .trie.search import TrieSearch

logger = get_logger(__name__)


class Search:
    """High-performance search engine using corpus-based vocabulary.

    Optimized for 100k-1M word searches with minimal overhead.
    """

    # Method priority for deduplication (higher = preferred when same word appears)
    METHOD_PRIORITY = {
        SearchMethod.EXACT: 5,
        SearchMethod.PREFIX: 4,
        SearchMethod.SUBSTRING: 3,
        SearchMethod.SEMANTIC: 2,
        SearchMethod.FUZZY: 1,
    }

    # Small bonus added to score for sorting — tiebreaker only, never overrides score.
    # A fuzzy match at 0.95 still beats a semantic match at 0.80.
    METHOD_SORT_BONUS = {
        SearchMethod.EXACT: 0.03,
        SearchMethod.PREFIX: 0.02,
        SearchMethod.SUBSTRING: 0.015,
        SearchMethod.SEMANTIC: 0.01,
        SearchMethod.FUZZY: 0.0,
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
        self.suffix_array: SuffixArray | None = None

        # Track semantic initialization separately with proper synchronization
        self._semantic_ready = False
        self._semantic_init_task: asyncio.Task[None] | None = None
        self._semantic_init_lock: asyncio.Lock = (
            asyncio.Lock()
        )  # CRITICAL FIX: Prevent race conditions
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

        if not force_rebuild:
            cached = get_cached_search(cache_key)
            if cached is not None:
                return cached

        instance = await cls.from_corpus(
            corpus_name=corpus_name,
            min_score=min_score,
            semantic=semantic,
            semantic_model=semantic_model,
            config=config,
        )
        put_cached_search(cache_key, instance)
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
                        self._semantic_init_task = asyncio.create_task(
                            self._initialize_semantic_background()
                        )

            return  # Skip rest of initialization since build_indices() already did it

        combined_vocab = self.corpus.vocabulary
        logger.debug(f"Corpus loaded with {len(combined_vocab)} vocabulary items")
        index_linkage_changed = False

        # Always build trie + fuzzy when corpus has vocabulary.
        # The trie is cheap (<1ms for small corpora) and required for exact/prefix/fuzzy.
        if combined_vocab:
            logger.debug("Building Trie index")
            self.trie_search = await TrieSearch.from_corpus(self.corpus)
            if self.trie_search and self.trie_search.index:
                trie_index_id = self.trie_search.index.index_id
                if self.index.trie_index_id != trie_index_id:
                    self.index.trie_index_id = trie_index_id
                    index_linkage_changed = True

            logger.debug("Initializing Fuzzy search (multi-strategy)")
            self.fuzzy_search = FuzzySearch(min_score=self.index.min_score)

            # Load or build fuzzy structures (BK-tree, phonetic, suffix array)
            # Uses versioned storage with vocabulary_hash for cache invalidation.
            try:
                fuzzy_index = await FuzzyIndex.get_or_create(
                    self.corpus,
                    config=VersionConfig(),
                )
                bk_tree, phonetic_index, suffix_array = fuzzy_index.deserialize()
                self.fuzzy_search.bk_tree = bk_tree
                self.fuzzy_search.phonetic_index = phonetic_index
                self.suffix_array = suffix_array

                # Persist linkage in SearchIndex
                if self.index.fuzzy_index_id != fuzzy_index.index_id:
                    self.index.fuzzy_index_id = fuzzy_index.index_id
                    index_linkage_changed = True

                logger.debug(
                    f"Loaded fuzzy structures from cache "
                    f"(BK={'yes' if bk_tree else 'no'}, "
                    f"phonetic={'yes' if phonetic_index else 'no'}, "
                    f"suffix={'yes' if suffix_array else 'no'})"
                )
            except Exception as e:
                # Fallback: build in-memory without persistence (e.g., no DB connection)
                logger.warning(f"FuzzyIndex cache unavailable, building in-memory: {e}")
                self.fuzzy_search.bk_tree = BKTree.build(combined_vocab)
                self.fuzzy_search.phonetic_index = PhoneticIndex(combined_vocab)
                self.suffix_array = SuffixArray(combined_vocab)

        # Initialize semantic search if enabled
        # If semantic is already "ready" but from a stale vocabulary (different hash),
        # invalidate it and rebuild. This prevents serving misaligned embeddings.
        if self.index.semantic_enabled:
            needs_semantic_init = not self._semantic_ready
            if (
                self._semantic_ready
                and self.semantic_search
                and self.semantic_search.index
                and self.semantic_search.index.vocabulary_hash != self.index.vocabulary_hash
            ):
                logger.warning(
                    f"Semantic index vocab hash mismatch "
                    f"(index={self.semantic_search.index.vocabulary_hash[:8]}, "
                    f"corpus={self.index.vocabulary_hash[:8]}), invalidating stale semantic search"
                )
                async with self._semantic_init_lock:
                    self.semantic_search = None
                    self._semantic_ready = False
                    self._semantic_init_task = None
                needs_semantic_init = True

            if needs_semantic_init:
                logger.debug("Semantic search enabled - initializing in background")
                async with self._semantic_init_lock:
                    if not self._semantic_ready and self._semantic_init_task is None:
                        self._semantic_init_task = asyncio.create_task(
                            self._initialize_semantic_background()
                        )

        self._initialized = True

        # Persist component linkage updates so metadata reflects current trie/semantic relationships.
        if index_linkage_changed:
            await self.index.save()

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

            # Persist semantic index linkage after successful background initialization.
            if self.index and semantic_search.index:
                semantic_index_id = semantic_search.index.index_id
                if self.index.semantic_index_id != semantic_index_id:
                    self.index.semantic_index_id = semantic_index_id
                    await self.index.save()

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
            from ..corpus.manager import get_tree_corpus_manager  # Lazy: heavyweight module

            manager = get_tree_corpus_manager()
            corpus = await manager.get_corpus(
                corpus_uuid=self.index.corpus_uuid,
                corpus_name=self.index.corpus_name,
                config=VersionConfig(),
            )
            return corpus.vocabulary_hash if corpus else None
        except Exception as e:
            logger.warning(f"Failed to get current vocab hash for '{self.index.corpus_name}': {e}")
            raise SearchError("hash_check", str(e)) from e

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

        # Rebuild fuzzy structures (BK-tree, phonetic, suffix array)
        if self.fuzzy_search:
            try:
                fuzzy_index = await FuzzyIndex.get_or_create(
                    updated_corpus,
                    config=VersionConfig(force_rebuild=True),
                )
                bk_tree, phonetic_index, suffix_array = fuzzy_index.deserialize()
                self.fuzzy_search.bk_tree = bk_tree
                self.fuzzy_search.phonetic_index = phonetic_index
                self.suffix_array = suffix_array
            except Exception as e:
                logger.warning(f"FuzzyIndex rebuild failed, building in-memory: {e}")
                self.fuzzy_search.bk_tree = BKTree.build(updated_corpus.vocabulary)
                self.fuzzy_search.phonetic_index = PhoneticIndex(updated_corpus.vocabulary)
                self.suffix_array = SuffixArray(updated_corpus.vocabulary)

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
            from .index import SearchIndex

            self.index = SearchIndex(
                corpus_name=self.corpus.corpus_name,
                corpus_uuid=self.corpus.corpus_uuid or "",  # Use empty string if None
                vocabulary_hash=self.corpus.vocabulary_hash,
                min_score=DEFAULT_MIN_SCORE,
                semantic_enabled=False,
            )

        # Build trie index
        self.trie_search = await TrieSearch.from_corpus(self.corpus)
        # Store trie index ID reference
        if self.trie_search.index:
            self.index.trie_index_id = self.trie_search.index.index_id

        # Build fuzzy index (always available when trie is built)
        self.fuzzy_search = FuzzySearch(min_score=self.index.min_score)

        self._initialized = True

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        method: SearchMethod | None = None,
        collect_all_matches: bool = False,
    ) -> list[SearchResult]:
        """Smart cascading search with early termination optimization and caching.

        Automatically selects optimal search methods based on query.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            method: Optional specific search method to use
            collect_all_matches: If True, collect all (method, score) pairs per word

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
            elif method == SearchMethod.SUBSTRING:
                return self.search_substring(normalized_query, max_results)
            elif method == SearchMethod.FUZZY and self.fuzzy_search and self.corpus:
                results = self.fuzzy_search.search(normalized_query, self.corpus, suffix_array=self.suffix_array)
                if min_score is not None:
                    results = [r for r in results if r.score >= min_score]
                # Restore diacritics
                for result in results:
                    result.word = self._get_original_word(result.word)
                return results[:max_results]
            elif method == SearchMethod.SEMANTIC:
                # If semantic was explicitly requested but still initializing, await it
                if not self.semantic_search and self._semantic_init_task:
                    try:
                        await self._semantic_init_task
                    except Exception:
                        pass  # Fall through to smart mode on failure
                if self.semantic_search:
                    # Route through search_semantic() which applies strict floor
                    # thresholds and lexical sanity gating
                    effective_min_score = min_score if min_score is not None else DEFAULT_MIN_SCORE
                    return await self.search_semantic(
                        normalized_query, max_results, effective_min_score
                    )
                # Semantic unavailable — fall through to smart mode

        # Otherwise use smart mode (pass already-normalized query)
        return await self.search_with_mode(
            query=normalized_query,
            mode=SearchMode.SMART,
            max_results=max_results,
            min_score=min_score,
            collect_all_matches=collect_all_matches,
        )

    async def search_with_mode(
        self,
        query: str,
        mode: SearchMode,
        max_results: int = 20,
        min_score: float | None = None,
        collect_all_matches: bool = False,
    ) -> list[SearchResult]:
        """Search with explicit mode selection.

        Args:
            query: Search query
            mode: Search mode (SMART, EXACT, FUZZY, SEMANTIC)
            max_results: Maximum results to return
            min_score: Minimum score threshold
            collect_all_matches: If True, collect all (method, score) pairs per word

        """
        # Ensure initialization
        await self.initialize()

        # OPTIMIZATION: Removed update_corpus() from hot path
        # The corpus hash is checked during initialization only
        # This saves ~0.5-1ms per search by avoiding redundant DB queries

        # Normalize query (idempotent — LRU-cached if already normalized by caller)
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
                collect_all_matches=collect_all_matches,
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

        if self.corpus:
            for result in results:
                if result.language is None:
                    result.language = self.corpus.language

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
                suffix_array=self.suffix_array,
            )

            # Set method and get original words with diacritics
            for match in matches:
                match.method = SearchMethod.FUZZY
                match.word = self._get_original_word(match.word)

            return matches
        except Exception as e:
            logger.warning(f"Fuzzy search failed: {e}")
            return []

    def search_substring(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[SearchResult]:
        """Search for words containing the query as a substring/infix.

        Uses suffix array for large corpora, trigram-based fallback for small ones.

        Args:
            query: Substring to search for (>= 3 chars for meaningful results)
            max_results: Maximum results to return

        """
        if not query or len(query) < 2:
            return []

        normalized_query = normalize(query)
        results: list[SearchResult] = []

        # Primary: suffix array (O(m log n), available for all corpus sizes)
        if self.suffix_array:
            matches = self.suffix_array.search(normalized_query, max_results=max_results)
            for word_idx, coverage in matches:
                original_word = self._get_original_word(
                    self.corpus.vocabulary[word_idx] if self.corpus else str(word_idx)
                )
                # Score: 70% coverage ratio + 30% position bonus (earlier = better)
                if self.corpus:
                    word = self.corpus.vocabulary[word_idx]
                    pos = word.find(normalized_query)
                    position_bonus = 1.0 - (pos / max(1, len(word))) if pos >= 0 else 0.0
                else:
                    position_bonus = 0.0
                score = 0.7 * coverage + 0.3 * position_bonus
                results.append(
                    SearchResult(
                        word=original_word,
                        score=score,
                        method=SearchMethod.SUBSTRING,
                        lemmatized_word=None,
                        language=self.corpus.language if self.corpus else None,
                        metadata=None,
                    )
                )
        # Fallback: trigram-based substring search
        elif self.corpus:
            candidates = self.corpus.get_substring_candidates(
                normalized_query, max_results=max_results
            )
            for word_idx in candidates:
                word = self.corpus.vocabulary[word_idx]
                original_word = self._get_original_word(word)
                coverage = len(normalized_query) / len(word)
                pos = word.find(normalized_query)
                position_bonus = 1.0 - (pos / max(1, len(word))) if pos >= 0 else 0.0
                score = 0.7 * coverage + 0.3 * position_bonus
                results.append(
                    SearchResult(
                        word=original_word,
                        score=score,
                        method=SearchMethod.SUBSTRING,
                        lemmatized_word=None,
                        language=self.corpus.language if self.corpus else None,
                        metadata=None,
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

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
            strict_floor = (
                self.SEMANTIC_PHRASE_MIN_SCORE
                if " " in normalized_query
                else self.SEMANTIC_SINGLE_WORD_MIN_SCORE
            )
            # For small corpora (<2000 words), the semantic space is too sparse —
            # unrelated words can score 0.80+ simply because there aren't enough
            # neighbours to push them down.  Raise the floor to compensate.
            if self.corpus and len(self.corpus.vocabulary) < SEMANTIC_SMALL_CORPUS_SIZE:
                strict_floor = max(strict_floor, SEMANTIC_SMALL_CORPUS_WORD_FLOOR if " " not in normalized_query else SEMANTIC_SMALL_CORPUS_PHRASE_FLOOR)
            effective_min_score = max(min_score, strict_floor)
            results = await self.semantic_search.search(
                normalized_query,
                max_results,
                effective_min_score,
            )

            # Lexical sanity gate — reject semantic matches that are textually
            # unrelated.  The previous gate (lexical < 0.2) was too permissive:
            # most real words exceed 0.2 against each other so they sailed
            # through unchecked.  Raise the bar to 0.35 and widen the score
            # margin so that only genuinely close results survive.
            filtered_results: list[SearchResult] = []
            for result in results:
                candidate = normalize(result.word)
                if candidate == normalized_query:
                    filtered_results.append(result)
                    continue

                lexical_similarity = SequenceMatcher(None, normalized_query, candidate).ratio()
                # For small corpora, require higher lexical overlap
                if lexical_similarity < LEXICAL_SANITY_THRESHOLD and result.score < effective_min_score + LEXICAL_GATE_SCORE_MARGIN:
                    continue
                filtered_results.append(result)

            results = filtered_results[:max_results]
            # Restore diacritics in semantic results
            for result in results:
                result.word = self._get_original_word(result.word)
            return results
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            raise SearchError("semantic", str(e)) from e

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

    # Minimum semantic score when there are no exact/fuzzy/prefix results to anchor to.
    # Prevents garbage semantic results for partial words like "exampl" → "table" (0.73)
    # while keeping useful matches like "wise" → "acute" (0.81).
    SEMANTIC_FALLBACK_MIN_SCORE = SEMANTIC_FALLBACK_MIN_SCORE
    SEMANTIC_SINGLE_WORD_MIN_SCORE = SEMANTIC_SINGLE_WORD_MIN_SCORE
    SEMANTIC_PHRASE_MIN_SCORE = SEMANTIC_PHRASE_MIN_SCORE

    async def _smart_search_cascade(
        self,
        query: str,
        max_results: int,
        min_score: float,
        semantic: bool,
        collect_all_matches: bool = False,
    ) -> list[SearchResult]:
        """Sequential search cascade that always includes prefix results for autocomplete.

        Unlike a pure cascade with early termination, this always runs prefix search
        alongside exact search. For a search dropdown/autocomplete, users expect to see
        words that START WITH their query, not just an exact match.

        Order: exact → prefix → substring → fuzzy → semantic.
        """
        # 1. Exact search (fastest — marisa-trie O(m))
        exact_results = self.search_exact(query)

        # 2. ALWAYS run prefix search — this is cheap (marisa-trie) and essential for
        #    autocomplete UX. "de" should show "deer", "dear", "deep", etc.
        prefix_results: list[SearchResult] = []
        prefix_words = self.search_prefix(query, max_results=max_results)
        if prefix_words:
            # Build a set of exact-match words to avoid duplicating them in prefix results
            exact_words = {r.word.lower() for r in exact_results}

            prefix_results = [
                SearchResult(
                    word=word,
                    lemmatized_word=None,
                    score=max(0.85, 1.0 - 0.02 * abs(len(word) - len(query))),
                    method=SearchMethod.PREFIX,
                    language=None,
                    metadata=None,
                )
                for word in prefix_words
                if word.lower() not in exact_words
            ]

        # Early exit: if exact + prefix already fill max_results, no need for fuzzy/semantic
        combined_count = len(exact_results) + len(prefix_results)
        if combined_count >= max_results:
            logger.debug(
                f"Early exit: {len(exact_results)} exact + {len(prefix_results)} prefix matches"
            )
            all_results = list(itertools.chain(exact_results, prefix_results))
            dedup = self._deduplicate_results_multi if collect_all_matches else self._deduplicate_results
            unique_results = dedup(all_results)
            return sorted(
                unique_results,
                key=lambda r: r.score + self.METHOD_SORT_BONUS.get(r.method, 0.0),
                reverse=True,
            )[:max_results]

        # 3. Substring search (for infix matches like "graph" → "paragraph")
        substring_results: list[SearchResult] = []
        if len(query) >= 3:
            substring_results = self.search_substring(query, max_results=max_results)

        # 4. Fuzzy search (most comprehensive for misspellings)
        fuzzy_results = self.search_fuzzy(query, max_results, min_score)

        # 5. Semantic search — quality-based gating
        # Only supplement when exact/fuzzy/prefix provide some anchor results.
        # When there are NO text-based results, require a much higher semantic
        # score to avoid garbage (e.g., "exampl" → "table" at 73%).
        semantic_results = []
        has_text_results = bool(exact_results or prefix_results or substring_results or fuzzy_results)
        if semantic and self._semantic_ready and self.semantic_search:
            high_quality = [r for r in fuzzy_results if r.score >= HIGH_QUALITY_FUZZY_SCORE]
            semantic_limit = max(
                0, max_results - len(high_quality) - len(prefix_results) - len(exact_results)
            )
            if semantic_limit > 0:
                semantic_min = min_score if has_text_results else self.SEMANTIC_FALLBACK_MIN_SCORE
                semantic_results = await self.search_semantic(query, semantic_limit, semantic_min)

        # 6. Merge and deduplicate with memory-efficient generators
        fuzzy_gen = (r for r in fuzzy_results if r.score >= min_score)
        semantic_gen = (r for r in semantic_results if r.score >= min_score)

        # Chain all results without creating intermediate lists
        all_results = list(itertools.chain(
            exact_results, prefix_results, substring_results, fuzzy_gen, semantic_gen
        ))

        # Deduplicate and sort
        dedup = self._deduplicate_results_multi if collect_all_matches else self._deduplicate_results
        unique_results = dedup(all_results)

        return sorted(
            unique_results,
            key=lambda r: r.score + self.METHOD_SORT_BONUS.get(r.method, 0.0),
            reverse=True,
        )[:max_results]

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
        """Remove duplicates, preferring exact matches. Case-insensitive dedup keys."""
        word_to_result: dict[str, SearchResult] = {}

        for result in results:
            key = result.word.lower()
            if key not in word_to_result:
                word_to_result[key] = result
            else:
                existing = word_to_result[key]
                # Prefer higher priority methods, then higher scores
                result_priority = self.METHOD_PRIORITY.get(result.method, 0)
                existing_priority = self.METHOD_PRIORITY.get(existing.method, 0)

                if (result_priority > existing_priority) or (
                    result_priority == existing_priority and result.score > existing.score
                ):
                    word_to_result[key] = result

        return list(word_to_result.values())

    def _deduplicate_results_multi(self, results: list[SearchResult]) -> list[SearchResult]:
        """Deduplicate results, collecting all (method, score) pairs per word.

        Keeps the highest-priority method as primary but stores all matches.
        """
        word_to_result: dict[str, SearchResult] = {}
        word_to_matches: dict[str, dict[SearchMethod, float]] = {}

        for result in results:
            key = result.word.lower()

            # Collect match detail (keep best score per method)
            if key not in word_to_matches:
                word_to_matches[key] = {}
            method_scores = word_to_matches[key]
            if result.method not in method_scores or result.score > method_scores[result.method]:
                method_scores[result.method] = result.score

            # Track best primary result (same logic as _deduplicate_results)
            if key not in word_to_result:
                word_to_result[key] = result
            else:
                existing = word_to_result[key]
                result_priority = self.METHOD_PRIORITY.get(result.method, 0)
                existing_priority = self.METHOD_PRIORITY.get(existing.method, 0)
                if (result_priority > existing_priority) or (
                    result_priority == existing_priority and result.score > existing.score
                ):
                    word_to_result[key] = result

        # Attach collected matches to each result
        for key, result in word_to_result.items():
            method_scores = word_to_matches[key]
            result.matches = sorted(
                [MatchDetail(method=m, score=s) for m, s in method_scores.items()],
                key=lambda md: (self.METHOD_PRIORITY.get(md.method, 0), md.score),
                reverse=True,
            )

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
