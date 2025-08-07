"""
High-performance fuzzy search implementation.

Streamlined fuzzy search using TheFuzz backend with direct corpus vocabulary access.
"""

from __future__ import annotations

from thefuzz import fuzz, process

from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE
from .corpus.core import Corpus
from .models import SearchResult
from .utils import apply_length_correction

logger = get_logger(__name__)


class FuzzySearch:
    """
    Streamlined fuzzy search using TheFuzz backend.

    Directly searches the corpus vocabulary without candidate pre-selection
    for simplicity and consistent performance.
    """

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE) -> None:
        """
        Initialize fuzzy search engine.

        Args:
            min_score: Minimum similarity score to include in results
        """
        self.min_score = min_score

    def search(
        self,
        query: str,
        corpus: Corpus,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """
        Fuzzy search using corpus vocabulary directly.
        
        Simplified implementation without candidate pre-selection.
        
        Args:
            query: Search query
            corpus: Corpus containing vocabulary to search
            max_results: Maximum number of results
            min_score: Minimum score threshold (overrides default)
        
        Returns:
            List of fuzzy search results
        """
        min_score_threshold = min_score if min_score is not None else self.min_score
        
        # Smart candidate selection using corpus indices
        candidates = self._select_candidates(query, corpus, max_results)
        if not candidates:
            return []
        # Get candidate words from corpus using batch retrieval  
        candidate_words = corpus.get_words_by_indices(candidates)
        
        # Use candidate words for better performance
        vocabulary = candidate_words
        
        if not vocabulary:
            return []
        
        # Use TheFuzz with score_cutoff for early termination
        results = process.extractBests(
            query,
            vocabulary,
            limit=min(max_results, len(vocabulary)),
            scorer=fuzz.WRatio,
            score_cutoff=min_score_threshold * 100,  # Convert to 0-100 scale
        )
        
        matches = []
        
        for word, score, _ in results:
            # Convert 0-100 score to 0.0-1.0
            base_score = score / 100.0
            
            # Apply length-aware scoring correction
            corrected_score = apply_length_correction(query, word, base_score)
            
            if corrected_score >= min_score_threshold:
                matches.append(
                    SearchResult(
                        word=word,
                        score=corrected_score,
                        method=None,  # Will be set by caller
                        lemmatized_word=None,
                        language=None,
                        metadata=None,
                    )
                )
        
        # Sort by corrected scores
        matches.sort(key=lambda m: m.score, reverse=True)
        
        return matches[:max_results]
    
    def _select_candidates(
        self, query: str, corpus: Corpus, max_results: int
    ) -> list[int]:
        """Select promising candidates using optimized corpus indices."""
        query_len = len(query)
        max_candidates = 1000

        # Use optimized single-call candidate selection
        candidates = corpus.get_candidates_optimized(
            query_len=query_len,
            prefix=query[:2] if query_len <= 4 else None,
            length_tolerance=2,
            max_candidates=max_candidates,
        )

        return candidates