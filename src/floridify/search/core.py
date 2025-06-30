"""
Core search engine implementation.

Provides a unified interface for exact, fuzzy, and semantic search operations
with first-class support for phrases and multi-word expressions.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .fuzzy import FuzzySearch, FuzzySearchMethod
from .lexicon import Language, LexiconLoader
from .phrase import PhraseNormalizer
from .semantic import SemanticSearch
from .trie import TrieSearch


class SearchMethod(Enum):
    """Available search methods with performance characteristics."""

    EXACT = "exact"  # Fastest: ~0.001ms - exact string matching
    PREFIX = "prefix"  # Fast: ~0.001ms - prefix/autocomplete matching
    FUZZY = "fuzzy"  # Fast: ~0.01ms - typo tolerance, abbreviations
    SEMANTIC = "semantic"  # Slower: ~0.1ms - meaning-based similarity
    AUTO = "auto"  # Automatic method selection based on query


class SearchResult(BaseModel):
    """Search result with relevance scoring and metadata."""

    word: str = Field(..., description="The matched word or phrase")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    method: SearchMethod = Field(..., description="Method that found this result")
    is_phrase: bool = Field(
        default=False, description="Whether this is a multi-word expression"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional search metadata"
    )

    model_config = {"frozen": True}


class SearchEngine:
    """
    Unified search interface with multiple algorithms.

    Implements KISS principles with clean APIs and robust phrase handling.
    Performance optimized through caching and efficient data structures.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        languages: list[Language] | None = None,
        min_score: float = 0.6,
        enable_semantic: bool = True,
    ) -> None:
        """
        Initialize the search engine.

        Args:
            cache_dir: Directory for caching lexicons and embeddings
            languages: Languages to load (defaults to English)
            min_score: Minimum relevance score for results
            enable_semantic: Whether to load semantic search capabilities
        """
        self.cache_dir = cache_dir or Path("data/search")
        self.languages = languages or [Language.ENGLISH]
        self.min_score = min_score
        self.enable_semantic = enable_semantic

        # Core components
        self.phrase_normalizer = PhraseNormalizer()
        self.lexicon_loader: LexiconLoader | None = None
        self.trie_search: TrieSearch | None = None
        self.fuzzy_search: FuzzySearch | None = None
        self.semantic_search: SemanticSearch | None = None

        # Performance tracking
        self._search_stats: dict[str, dict[str, Any]] = {
            "exact": {"count": 0, "total_time": 0.0},
            "prefix": {"count": 0, "total_time": 0.0},
            "fuzzy": {"count": 0, "total_time": 0.0},
            "semantic": {"count": 0, "total_time": 0.0},
        }

        # Initialization flag
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize search components asynchronously."""
        if self._initialized:
            return

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load lexicons
        self.lexicon_loader = LexiconLoader(self.cache_dir)
        await self.lexicon_loader.load_languages(self.languages)

        # Initialize search components
        words = self.lexicon_loader.get_all_words()
        phrases = self.lexicon_loader.get_all_phrases()

        self.trie_search = TrieSearch()
        self.trie_search.build_index(words + phrases)

        self.fuzzy_search = FuzzySearch(min_score=self.min_score)

        if self.enable_semantic:
            self.semantic_search = SemanticSearch(self.cache_dir)
            await self.semantic_search.initialize(words + phrases)

        self._initialized = True

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        methods: list[SearchMethod] | None = None,
    ) -> list[SearchResult]:
        """
        Universal search method handling words, phrases, typos, and semantics.

        Args:
            query: Search term (word or phrase)
            max_results: Maximum number of results to return
            min_score: Minimum relevance score (overrides default)
            methods: Search methods to use (defaults to AUTO)

        Returns:
            List of search results ranked by relevance
        """
        if not self._initialized:
            await self.initialize()

        # Normalize and validate query
        normalized_query = self.phrase_normalizer.normalize(query)
        if not normalized_query.strip():
            return []

        # Use provided min_score or default
        score_threshold = min_score if min_score is not None else self.min_score

        # Determine search methods
        if methods is None or SearchMethod.AUTO in methods:
            methods = self._select_optimal_methods(normalized_query)

        # Execute searches in parallel for better performance
        search_tasks = []
        for method in methods:
            if method == SearchMethod.EXACT:
                search_tasks.append(self._search_exact(normalized_query))
            elif method == SearchMethod.PREFIX:
                search_tasks.append(self._search_prefix(normalized_query, max_results))
            elif method == SearchMethod.FUZZY:
                search_tasks.append(self._search_fuzzy(normalized_query, max_results))
            elif method == SearchMethod.SEMANTIC and self.semantic_search:
                search_tasks.append(
                    self._search_semantic(normalized_query, max_results)
                )

        # Collect all results
        all_results: list[SearchResult] = []
        if search_tasks:
            results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)
            for results in results_lists:
                if isinstance(results, list):
                    all_results.extend(results)

        # Remove duplicates and filter by score
        unique_results = self._deduplicate_results(all_results)
        filtered_results = [r for r in unique_results if r.score >= score_threshold]

        # Sort by score (descending) and return top results
        sorted_results = sorted(filtered_results, key=lambda r: r.score, reverse=True)
        return sorted_results[:max_results]

    def _select_optimal_methods(self, query: str) -> list[SearchMethod]:
        """
        Automatically select optimal search methods based on query characteristics.

        Strategy:
        - Short queries (≤3 chars): Prefix for autocomplete
        - Medium queries (4-8 chars): Exact + Fuzzy for typos
        - Long queries (>8 chars): All methods for comprehensive results
        - Phrases (contains spaces): Exact + Semantic for meaning
        """
        query_len = len(query.strip())
        has_spaces = " " in query.strip()

        if has_spaces:
            # Phrases: prioritize exact and semantic matching
            return [SearchMethod.EXACT, SearchMethod.SEMANTIC, SearchMethod.FUZZY]
        elif query_len <= 3:
            # Short queries: focus on prefix matching
            return [SearchMethod.PREFIX, SearchMethod.EXACT]
        elif query_len <= 8:
            # Medium queries: exact and fuzzy for typos
            return [SearchMethod.EXACT, SearchMethod.FUZZY]
        else:
            # Long queries: comprehensive search
            return [SearchMethod.EXACT, SearchMethod.FUZZY, SearchMethod.SEMANTIC]

    async def _search_exact(self, query: str) -> list[SearchResult]:
        """Execute exact string matching."""
        start_time = time.perf_counter()

        try:
            if not self.trie_search:
                return []

            matches = self.trie_search.search_exact(query)
            results = [
                SearchResult(
                    word=match,
                    score=1.0,  # Exact matches get perfect score
                    method=SearchMethod.EXACT,
                    is_phrase=" " in match,
                )
                for match in matches
            ]

            return results

        finally:
            elapsed = time.perf_counter() - start_time
            self._search_stats["exact"]["count"] += 1
            self._search_stats["exact"]["total_time"] += elapsed

    async def _search_prefix(self, query: str, max_results: int) -> list[SearchResult]:
        """Execute prefix matching for autocomplete."""
        start_time = time.perf_counter()

        try:
            if not self.trie_search:
                return []

            matches = self.trie_search.search_prefix(query, max_results)
            results = [
                SearchResult(
                    word=match,
                    score=0.9,  # High score for prefix matches
                    method=SearchMethod.PREFIX,
                    is_phrase=" " in match,
                )
                for match in matches
            ]

            return results

        finally:
            elapsed = time.perf_counter() - start_time
            self._search_stats["prefix"]["count"] += 1
            self._search_stats["prefix"]["total_time"] += elapsed

    async def _search_fuzzy(self, query: str, max_results: int) -> list[SearchResult]:
        """Execute fuzzy string matching."""
        start_time = time.perf_counter()

        try:
            if not self.fuzzy_search or not self.lexicon_loader:
                return []

            # Get vocabulary for fuzzy matching
            words = self.lexicon_loader.get_all_words()
            phrases = self.lexicon_loader.get_all_phrases()
            vocabulary = words + phrases

            # Use automatic method selection for fuzzy search
            matches = self.fuzzy_search.search(
                query=query,
                word_list=vocabulary,
                max_results=max_results,
                method=FuzzySearchMethod.AUTO,
            )

            results = [
                SearchResult(
                    word=match.word,
                    score=match.score,
                    method=SearchMethod.FUZZY,
                    is_phrase=" " in match.word,
                    metadata={
                        "fuzzy_method": match.method.value if match.method else None
                    },
                )
                for match in matches
            ]

            return results

        finally:
            elapsed = time.perf_counter() - start_time
            self._search_stats["fuzzy"]["count"] += 1
            self._search_stats["fuzzy"]["total_time"] += elapsed

    async def _search_semantic(
        self, query: str, max_results: int
    ) -> list[SearchResult]:
        """Execute semantic similarity search."""
        start_time = time.perf_counter()

        try:
            if not self.semantic_search:
                return []

            matches = await self.semantic_search.search(query, max_results)
            results = [
                SearchResult(
                    word=word,
                    score=score,
                    method=SearchMethod.SEMANTIC,
                    is_phrase=" " in word,
                )
                for word, score in matches
            ]

            return results

        finally:
            elapsed = time.perf_counter() - start_time
            self._search_stats["semantic"]["count"] += 1
            self._search_stats["semantic"]["total_time"] += elapsed

    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """
        Remove duplicate results, keeping the highest-scoring version.

        Priority order: EXACT > PREFIX > FUZZY > SEMANTIC
        """
        method_priority = {
            SearchMethod.EXACT: 4,
            SearchMethod.PREFIX: 3,
            SearchMethod.FUZZY: 2,
            SearchMethod.SEMANTIC: 1,
        }

        word_to_result: dict[str, SearchResult] = {}

        for result in results:
            word = result.word.lower()

            if word not in word_to_result:
                word_to_result[word] = result
            else:
                existing = word_to_result[word]

                # Keep result with higher priority method, or higher score if same method
                existing_priority = method_priority.get(existing.method, 0)
                new_priority = method_priority.get(result.method, 0)

                if new_priority > existing_priority or (
                    new_priority == existing_priority and result.score > existing.score
                ):
                    word_to_result[word] = result

        return list(word_to_result.values())

    def get_search_stats(self) -> dict[str, dict[str, Any]]:
        """Get performance statistics for search methods."""
        stats = {}
        for method, data in self._search_stats.items():
            count = data["count"]
            total_time = data["total_time"]

            stats[method] = {
                "count": count,
                "total_time": total_time,
                "avg_time": total_time / count if count > 0 else 0.0,
            }

        return stats
