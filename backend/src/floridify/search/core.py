"""
Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from ..text import normalize_comprehensive
from ..utils.logging import get_logger
from .constants import SearchMethod
from .fuzzy import FuzzySearch
from .semantic_manager import get_semantic_search_manager
from .trie import TrieSearch

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

        # Build search indices (one-time cost)
        self._vocabulary = words + self.phrases  # Combined for search

        # High-performance search components
        self.trie_search = TrieSearch()
        self.trie_search.build_index(self._vocabulary)
        self.fuzzy_search = FuzzySearch(min_score=min_score)

        # Semantic search manager (public access)
        self.semantic_manager = get_semantic_search_manager() if self.enable_semantic else None
        
        logger.info(f"Semantic search {'enabled' if self.enable_semantic else 'disabled'} for SearchEngine")
        logger.debug(
            f"SearchEngine initialized: {len(words)} words, {len(self.phrases)} phrases, semantic={'enabled' if self.enable_semantic else 'disabled'}"
        )

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        semantic: bool | None = None,
    ) -> list[SearchResult]:
        """
        Fast multi-method search.

        Automatically selects optimal search methods based on query.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            semantic: Override semantic search setting (None = use default)
        """
        # Normalize query
        normalized_query = normalize_comprehensive(query)
        if not normalized_query.strip():
            return []

        score_threshold = min_score if min_score is not None else self.min_score

        # Determine if semantic search should be used
        should_semantic = (
            semantic if semantic is not None else self.enable_semantic
        ) and self.semantic_manager is not None and self.corpus_name is not None

        # Build search tasks
        search_tasks = [
            self._search_exact(normalized_query),
            self._search_fuzzy(normalized_query, max_results),
        ]

        # Add semantic search if enabled
        if should_semantic:
            search_tasks.append(self._search_semantic(normalized_query, max_results))

        # Execute all searches in parallel
        search_results = await asyncio.gather(*search_tasks)

        # Combine all results
        all_results = []
        for results in search_results:
            all_results.extend(results)

        # Deduplicate and filter
        unique_results = self._deduplicate_results(all_results)
        filtered = [r for r in unique_results if r.score >= score_threshold]

        # Sort by score and return top results
        return sorted(filtered, key=lambda r: r.score, reverse=True)[:max_results]

    async def find_best_match(self, word: str) -> SearchResult | None:
        """Find single best matching word (for word resolution)."""
        results = await self.search(word, max_results=1, min_score=0.0)
        return results[0] if results else None

    async def _search_exact(self, query: str) -> list[SearchResult]:
        """Exact string matching."""
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

    async def _search_fuzzy(self, query: str, max_results: int) -> list[SearchResult]:
        """Fuzzy matching for typos."""
        matches = self.fuzzy_search.search(
            query=query,
            word_list=self._vocabulary,
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

    async def _search_semantic(self, query: str, max_results: int) -> list[SearchResult]:
        """Semantic similarity search using embeddings."""
        if not self.semantic_manager or not self.corpus_name:
            return []

        # Get or create semantic search instance through manager
        try:
            semantic_search = await self.semantic_manager.get_or_create_semantic_search(
                corpus_name=self.corpus_name,
                vocabulary=self._vocabulary,
                force_rebuild=False,
                ttl_hours=168.0,
            )
        except Exception as e:
            logger.warning(f"Failed to get semantic search instance: {e}")
            return []

        # Perform semantic search
        matches = await semantic_search.search(query, max_results)
        
        # Debug: Log semantic results
        if matches:
            logger.debug(f"Semantic search returned {len(matches)} matches: {matches[:3]}")
        else:
            logger.debug(f"Semantic search returned no matches for '{query}'")

        return [
            SearchResult(
                word=word,
                score=score,
                method=SearchMethod.SEMANTIC,
                is_phrase=" " in word,
            )
            for word, score in matches
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
        return self.enable_semantic and self.semantic_manager is not None

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
        if self.semantic_manager and self.corpus_name and self._vocabulary:
            try:
                await self.semantic_manager.get_or_create_semantic_search(
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
        if self.semantic_manager and self.corpus_name:
            if await self.semantic_manager.invalidate_semantic_search(self.corpus_name):
                return 1
        return 0
