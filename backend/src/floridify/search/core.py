"""
Core search engine for arbitrary lexicons.

Performance-optimized for 100k-1M word searches with KISS principles.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logging import get_logger
from .constants import SearchMethod
from .fuzzy import FuzzySearch
from .lexicon.core import Lexicon
from .phrase import PhraseNormalizer
from .trie import TrieSearch

logger = get_logger(__name__)


class SearchResult(BaseModel):
    """Simple search result."""
    
    word: str = Field(..., description="Matched word or phrase")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: SearchMethod = Field(..., description="Search method used")
    is_phrase: bool = Field(default=False, description="Is multi-word phrase")


class GeneralizedSearch:
    """
    High-performance search engine for arbitrary lexicons.
    
    Optimized for 100k-1M word searches with minimal overhead.
    """
    
    def __init__(self, lexicon: Lexicon, min_score: float = 0.6) -> None:
        """Initialize with lexicon and minimum score threshold."""
        self.lexicon = lexicon
        self.min_score = min_score
        self.phrase_normalizer = PhraseNormalizer()
        
        # Build search indices (one-time cost)
        words = lexicon.get_all_words()
        phrases = lexicon.get_all_phrases()
        self._vocabulary = words + phrases  # Combined for search
        
        # High-performance search components
        self.trie_search = TrieSearch()
        self.trie_search.build_index(self._vocabulary)
        self.fuzzy_search = FuzzySearch(min_score=min_score)
        
        logger.debug(f"GeneralizedSearch initialized: {len(words)} words, {len(phrases)} phrases")
    
    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """
        Fast multi-method search.
        
        Automatically selects optimal search methods based on query.
        """
        # Normalize query
        normalized_query = self.phrase_normalizer.normalize(query)
        if not normalized_query.strip():
            return []
        
        score_threshold = min_score if min_score is not None else self.min_score
        
        # Run searches in parallel for performance
        exact_task = self._search_exact(normalized_query)
        fuzzy_task = self._search_fuzzy(normalized_query, max_results)
        
        # Execute in parallel
        exact_results, fuzzy_results = await asyncio.gather(exact_task, fuzzy_task)
        
        # Combine and deduplicate
        all_results = exact_results + fuzzy_results
        unique_results = self._deduplicate_results(all_results)
        
        # Filter by score and return top results
        filtered = [r for r in unique_results if r.score >= score_threshold]
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
    
    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicates, preferring exact matches."""
        word_to_result: dict[str, SearchResult] = {}
        
        for result in results:
            word_key = result.word.lower().strip()
            
            if word_key not in word_to_result:
                word_to_result[word_key] = result
            else:
                existing = word_to_result[word_key]
                # Prefer exact matches, then higher scores
                if (result.method == SearchMethod.EXACT and existing.method != SearchMethod.EXACT) or \
                   (result.method == existing.method and result.score > existing.score):
                    word_to_result[word_key] = result
        
        return list(word_to_result.values())
    
    def get_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        return {
            "vocabulary_size": len(self._vocabulary),
            "words": len(self.lexicon.get_all_words()),
            "phrases": len(self.lexicon.get_all_phrases()),
            "min_score": self.min_score,
        }