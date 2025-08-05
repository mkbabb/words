"""
Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..core.semantic_manager import get_semantic_search_manager
from ..text import normalize_comprehensive
from ..utils.logging import get_logger
from .constants import SearchMethod
from .fuzzy import FuzzySearch
from .trie import TrieSearch
from .vocabulary import SharedVocabularyStore

logger = get_logger(__name__)


class SearchResult(BaseModel):
    """Simple search result."""

    word: str = Field(..., description="Matched word or phrase")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: SearchMethod = Field(..., description="Search method used")
    is_phrase: bool = Field(default=False, description="Is multi-word phrase")


class SearchEngine:
    """
    High-performance search engine using corpus-based vocabulary.

    Optimized for 100k-1M word searches with minimal overhead.
    """

    def __init__(
        self,
        words: list[str],
        phrases: list[str] | None = None,
        min_score: float = 0.6,
        semantic: bool = False,
        corpus_name: str | None = None,
    ) -> None:
        """Initialize with vocabulary and configuration.

        Args:
            words: List of words to search
            phrases: List of phrases to search
            min_score: Minimum score threshold for results
            semantic: Enable semantic search (requires ML dependencies)
            corpus_name: Name for corpus identification
        """
        self.words = words
        self.phrases = phrases or []
        self.min_score = min_score
        self.enable_semantic = semantic
        self.corpus_name = corpus_name

        # Build vocabulary list
        self._vocabulary = words + self.phrases
        
        # Initialize components as None - will be lazy loaded
        self.vocab_store: SharedVocabularyStore | None = None
        self.vocab_hash: str | None = None
        self.trie_search: TrieSearch | None = None
        self.fuzzy_search: FuzzySearch | None = None
        self.semantic_manager = None  # Lazy load only when needed
        
        self._initialized = False

        logger.debug(
            f"SearchEngine created: {len(words)} words, {len(self.phrases)} phrases, semantic={'enabled' if self.enable_semantic else 'disabled'}"
        )

    async def initialize(self) -> None:
        """Initialize expensive components lazily."""
        if self._initialized:
            return
            
        logger.debug("Initializing SearchEngine components...")
        
        # Build shared vocabulary store (eliminates word_list copying)
        self.vocab_store = SharedVocabularyStore()
        self.vocab_hash = self.vocab_store.create_vocabulary(self._vocabulary)

        # High-performance search components
        self.trie_search = TrieSearch()
        self.trie_search.build_index(self._vocabulary)
        self.fuzzy_search = FuzzySearch(min_score=self.min_score)
        
        self._initialized = True
        
        logger.info(
            f"SearchEngine initialized: {len(self.words)} words, {len(self.phrases)} phrases, semantic={'enabled' if self.enable_semantic else 'disabled'}"
        )

    def _get_semantic_manager(self):
        """Get semantic manager only when needed."""
        if self.enable_semantic and self.semantic_manager is None:
            self.semantic_manager = get_semantic_search_manager()
        return self.semantic_manager

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        semantic: bool | None = None,
    ) -> list[SearchResult]:
        """
        Smart cascading search with early termination optimization.

        Automatically selects optimal search methods based on query.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            semantic: Override semantic search setting (None = use default)
        """
        # Ensure initialization
        await self.initialize()
        # Normalize query
        normalized_query = normalize_comprehensive(query)
        if not normalized_query.strip():
            return []

        min_score_threshold = min_score if min_score is not None else self.min_score

        # Determine if semantic search should be used
        should_semantic = (
            (semantic if semantic is not None else self.enable_semantic)
            and self.enable_semantic  # Only check if semantic is enabled
            and self.corpus_name is not None
        )

        return await self._smart_search_cascade(
            normalized_query, max_results, min_score_threshold, should_semantic
        )

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
            return exact_filtered[:max_results]  # No sorting needed - all exact matches have score=1.0

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
                score=1.0,
                method=SearchMethod.EXACT,
                is_phrase=" " in match,
            )
            for match in matches
        ]

    def _search_fuzzy_sync(self, query: str, max_results: int) -> list[SearchResult]:
        """Fuzzy matching using shared vocabulary store - synchronous."""
        if self.fuzzy_search is None or self.vocab_store is None:
            return []
        matches = self.fuzzy_search.search(
            query=query,
            vocab_store=self.vocab_store,
            max_results=max_results,
        )

        return [
            SearchResult(
                word=match.word,
                score=match.score,
                method=SearchMethod.FUZZY,
                is_phrase=" " in match.word,
            )
            for match in matches
        ]

    async def _search_exact(self, query: str) -> list[SearchResult]:
        """Exact string matching."""
        return self._search_exact_sync(query)

    async def _search_fuzzy(self, query: str, max_results: int) -> list[SearchResult]:
        """Fuzzy matching using shared vocabulary store."""
        return self._search_fuzzy_sync(query, max_results)

    async def _search_semantic(self, query: str, max_results: int, min_score: float) -> list[SearchResult]:
        """Semantic similarity search using embeddings."""
        semantic_manager = self._get_semantic_manager()
        if not semantic_manager or not self.corpus_name:
            return []

        # Get or create semantic search instance through manager
        try:
            semantic_search = await semantic_manager.get_or_create_semantic_search(
                corpus_name=self.corpus_name,
                vocabulary=self._vocabulary,
                force_rebuild=False,
                ttl_hours=168.0,
            )
        except Exception as e:
            logger.warning(f"Failed to get semantic search instance: {e}")
            return []

        # Perform semantic search
        matches = await semantic_search.search(query, max_results, min_score)

        # Debug: Log semantic results
        if matches:
            logger.debug(f"Semantic search returned {len(matches)} matches: {matches[:3]}")
        else:
            logger.debug(f"Semantic search returned no matches for '{query}'")

        return [
            SearchResult(
                word=match.word,
                score=match.score,
                method=SearchMethod.SEMANTIC,
                is_phrase=" " in match.word,
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
    def semantic_search(self) -> bool:
        """Check if semantic search is available and enabled."""
        return self.enable_semantic

    def get_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        return {
            "vocabulary_size": len(self._vocabulary),
            "words": len(self.words),
            "phrases": len(self.phrases),
            "min_score": self.min_score,
            "semantic_enabled": self.enable_semantic,
            "semantic_available": True,
        }

    async def initialize_semantic(self) -> None:
        """Initialize semantic search indices through manager."""
        semantic_manager = self._get_semantic_manager()
        if semantic_manager and self.corpus_name and self._vocabulary:
            try:
                await semantic_manager.get_or_create_semantic_search(
                    corpus_name=self.corpus_name,
                    vocabulary=self._vocabulary,
                    force_rebuild=False,
                    ttl_hours=168.0,
                )
                logger.info(f"Semantic search initialized with {len(self._vocabulary)} items")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic search: {e}")

    async def invalidate_semantic_cache(self) -> int:
        """Invalidate semantic search cache through manager."""
        semantic_manager = self._get_semantic_manager()
        if semantic_manager and self.corpus_name:
            if await semantic_manager.invalidate_semantic_search(self.corpus_name):
                return 1
        return 0
