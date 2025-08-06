"""
Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from ..caching.unified import UnifiedCache, get_unified
from ..text import normalize_comprehensive
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod
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
            return

        logger.debug("Initializing SearchEngine components...")

        # Fetch Corpus from corpus manager
        manager = get_corpus_manager()
        
        # Get corpus metadata to check if it exists
        corpus_metadata = await manager.get_corpus_metadata(self.corpus_name)
        
        if corpus_metadata is None:
            raise ValueError(f"Corpus '{self.corpus_name}' not found. Create it first using get_or_create_corpus.")
            
        # Get corpus from cache using metadata
        self.corpus = await manager.get_corpus(
            self.corpus_name,
            vocab_hash=corpus_metadata.vocabulary_hash
        )
        
        if self.corpus is None:
            raise ValueError(f"Corpus '{self.corpus_name}' not found in cache. Create it first using get_or_create_corpus.")
        
        self._vocabulary_hash = self.corpus.vocabulary_hash
        combined_vocab = self.corpus.get_combined_vocabulary()
        
        # High-performance search components
        self.trie_search = TrieSearch()
        await self.trie_search.build_index(combined_vocab)
        self.fuzzy_search = FuzzySearch(min_score=self.min_score)
        
        # Initialize semantic search if enabled
        if self.semantic:
            # Get or create semantic search from manager
            semantic_manager = get_semantic_search_manager()
            self.semantic_search = await semantic_manager.get_semantic_search(
                corpus_name=self.corpus_name,
                vocab_hash=self.corpus.vocabulary_hash
            )
            if not self.semantic_search:
                # Create semantic search if not found in cache
                logger.info(f"Creating semantic search for corpus '{self.corpus_name}'")
                self.semantic_search = await semantic_manager.create_semantic_search(
                    corpus_name=self.corpus_name,
                    corpus=self.corpus,
                    force_rebuild=self.force_rebuild
                )

        self._initialized = True

        logger.info(f"SearchEngine initialized for corpus '{self.corpus_name}'")

    async def _check_and_update_corpus(self) -> None:
        """Check if corpus has changed and update components if needed."""
        if not self.corpus:
            return
            
        # Get latest corpus metadata
        manager = get_corpus_manager()
        corpus_metadata = await manager.get_corpus_metadata(self.corpus_name)
        
        if not corpus_metadata:
            logger.warning(f"Corpus metadata not found for '{self.corpus_name}'")
            return
            
        # Check if vocabulary has changed
        if corpus_metadata.vocabulary_hash != self._vocabulary_hash:
            logger.info(f"Corpus vocabulary changed for '{self.corpus_name}', updating components")
            
            # Get updated corpus
            updated_corpus = await manager.get_corpus(
                self.corpus_name,
                vocab_hash=corpus_metadata.vocabulary_hash
            )
            
            if not updated_corpus:
                logger.error(f"Failed to get updated corpus '{self.corpus_name}'")
                return
                
            # Update corpus and hash
            self.corpus = updated_corpus
            self._vocabulary_hash = updated_corpus.vocabulary_hash
            
            # Update search components
            combined_vocab = updated_corpus.get_combined_vocabulary()
            
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
        semantic: bool | None = None,
    ) -> list[SearchResult]:
        """
        Smart cascading search with early termination optimization and caching.

        Automatically selects optimal search methods based on query.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            semantic: Override semantic search setting (None = use default)
        """
        # Ensure initialization
        await self.initialize()
        
        # Check if corpus has changed and update if needed
        await self._check_and_update_corpus()
        
        # Normalize query
        normalized_query = normalize_comprehensive(query)
        if not normalized_query.strip():
            return []

        min_score_threshold = min_score if min_score is not None else self.min_score

        # Determine if semantic search should be used
        should_semantic = (
            (semantic if semantic is not None else self.semantic)
            and self.semantic  # Only check if semantic is enabled
        )

        # Get unified cache (L1 memory + L2 filesystem)
        if self._cache is None:
            self._cache = await get_unified()

        # Generate cache key
        cache_key = f"{normalized_query}:{max_results}:{min_score_threshold}:{should_semantic}:{self.corpus_name}"
        
        # Try to get from cache
        if self._cache is not None:
            cached_results: list[SearchResult] | None = await self._cache.get("search", cache_key)
            if cached_results is not None:
                logger.debug(f"Search cache hit for query: {query[:50]}")
                return cached_results

        # Perform search
        results = await self._smart_search_cascade(
            normalized_query, max_results, min_score_threshold, should_semantic
        )

        # Cache results (1 hour TTL for search results)
        if self._cache is not None:
            await self._cache.set("search", cache_key, results, ttl=timedelta(hours=1))

        return results

    async def _smart_search_cascade(
        self, query: str, max_results: int, min_score_threshold: float, should_semantic: bool
    ) -> list[SearchResult]:
        """Smart search cascade with early termination."""
        all_results = []

        # Phase 1: Exact search (always fast, <1ms)
        exact_results = await self._search_exact(query)
        exact_filtered = [r for r in exact_results if r.score >= min_score_threshold]
        all_results.extend(exact_filtered)

        # Early exit if we have enough high-quality exact matches
        if len(exact_filtered) >= max_results:
            logger.debug(f"Early exit: {len(exact_filtered)} exact matches found")
            return exact_filtered[
                :max_results
            ]  # No sorting needed - all exact matches have score=1.0

        # Phase 2: Fuzzy search (only if needed)
        fuzzy_needed = max_results - len(exact_filtered)
        fuzzy_results = await self._search_fuzzy(
            query, fuzzy_needed * 2
        )  # Get extra for deduplication
        fuzzy_filtered = [r for r in fuzzy_results if r.score >= min_score_threshold]
        all_results.extend(fuzzy_filtered)

        # Deduplicate after fuzzy
        unique_results = self._deduplicate_results(all_results)

        # Phase 3: Semantic search (only for poor fuzzy coverage)
        if should_semantic and len(unique_results) < max_results * 0.7:
            logger.debug(f"Triggering semantic search: only {len(unique_results)} results so far")
            semantic_results = await self._search_semantic(query, max_results, min_score_threshold)
            semantic_filtered = [r for r in semantic_results if r.score >= min_score_threshold]
            all_results.extend(semantic_filtered)
            unique_results = self._deduplicate_results(all_results)

        # Sort by score and return top results
        return sorted(unique_results, key=lambda r: r.score, reverse=True)[:max_results]

    async def find_best_match(self, word: str) -> SearchResult | None:
        """Find single best matching word (for word resolution)."""
        results = await self.search(word, max_results=1, min_score=0.0)
        return results[0] if results else None

    def _search_exact_sync(self, query: str) -> list[SearchResult]:
        """Exact string matching - synchronous."""
        if self.trie_search is None:
            return []
        matches = self.trie_search.search_exact(query)
        return [
            SearchResult(
                word=match,
                lemmatized_word=None,
                score=1.0,
                method=SearchMethod.EXACT,
                is_phrase=" " in match,
                language=None,
                metadata=None,
            )
            for match in matches
        ]

    async def _search_fuzzy_direct(self, query: str, max_results: int) -> list[SearchResult]:
        """Fuzzy matching using corpus object."""
        if self.fuzzy_search is None or self.corpus is None:
            return []
        
        try:
            matches = await self.fuzzy_search.search(
                query=query,
                corpus=self.corpus,
                max_results=max_results,
            )
            
            return [
                SearchResult(
                    word=match.word,
                    lemmatized_word=None,
                    score=match.score,
                    method=SearchMethod.FUZZY,
                    is_phrase=match.is_phrase,
                    language=None,
                    metadata=None,
                )
                for match in matches
            ]
        except Exception as e:
            logger.warning(f"Fuzzy search failed: {e}")
            return []

    async def _search_exact(self, query: str) -> list[SearchResult]:
        """Exact string matching."""
        return self._search_exact_sync(query)

    async def _search_fuzzy(self, query: str, max_results: int) -> list[SearchResult]:
        """Fuzzy matching using corpus object."""
        return await self._search_fuzzy_direct(query, max_results)

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
                is_phrase=" " in match.word,
                language=None,
                metadata=None,
            )
            for match in matches
        ]

    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicates, preferring exact matches."""
        word_to_result: dict[str, SearchResult] = {}

        # Method priority: EXACT > SEMANTIC > FUZZY
        method_priority = {
            SearchMethod.EXACT: 3,
            SearchMethod.SEMANTIC: 2,
            SearchMethod.FUZZY: 1,
        }

        for result in results:
            word_key = result.word.lower().strip()

            if word_key not in word_to_result:
                word_to_result[word_key] = result
            else:
                existing = word_to_result[word_key]
                # Prefer higher priority methods, then higher scores
                result_priority = method_priority.get(result.method, 0)
                existing_priority = method_priority.get(existing.method, 0)

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
                "vocabulary_size": self.corpus.get_vocabulary_size(),
                "words": len(self.corpus.words),
                "phrases": len(self.corpus.phrases),
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



__all__ = ["SearchEngine", "SearchResult"]
