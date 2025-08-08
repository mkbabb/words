"""
High-performance fuzzy search implementation.

Streamlined fuzzy search using TheFuzz backend with direct corpus vocabulary access.
"""

from __future__ import annotations

from rapidfuzz import fuzz, process

from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod
from .corpus.core import Corpus
from .models import SearchResult
from .utils import apply_length_correction

logger = get_logger(__name__)


class FuzzySearch:
    """
    Streamlined fuzzy search using RapidFuzz backend.

    Optimized with candidate pre-selection for better performance.
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
        High-performance robust fuzzy search with multi-algorithm scoring.
        
        Uses adaptive candidate selection and multiple scoring methods for
        challenging misspellings including multi-phrase words.

        Args:
            query: Search query
            corpus: Corpus containing vocabulary to search
            max_results: Maximum number of results
            min_score: Minimum score threshold (overrides default)

        Returns:
            List of fuzzy search results sorted by relevance
        """
        min_score_threshold = min_score if min_score is not None else self.min_score
        
        # Adaptive candidate selection based on query characteristics
        is_challenging = self._is_challenging_query(query)
        max_candidates = min(max_results * (100 if is_challenging else 50), 3000)
        
        # High-performance signature-based candidate selection (no fallback needed)
        candidates = corpus.get_candidates(query, max_candidates=max_candidates)
        vocabulary = corpus.get_words_by_indices(candidates) if candidates else []
        
        if not vocabulary:
            logger.warning(f"No candidates found for '{query}' - this shouldn't happen with signature selection")
            return []
            
        logger.debug(f"Signature selection found {len(vocabulary)} candidates for '{query}'")

        # Multi-algorithm approach for robustness
        matches = []
        
        # Primary scorer: WRatio for general cases
        primary_results = process.extract(
            query,
            vocabulary,
            limit=min(max_results * 3, len(vocabulary)),
            scorer=fuzz.WRatio,
            score_cutoff=min_score_threshold * 80,  # More inclusive threshold
        )
        
        # Secondary scorer: More permissive algorithms for challenging cases
        secondary_results = []
        if is_challenging:
            # Token-based for phrases
            secondary_results = process.extract(
                query,
                vocabulary,
                limit=min(max_results * 2, len(vocabulary)),
                scorer=fuzz.token_set_ratio,
                score_cutoff=min_score_threshold * 60,
            )
            
            # Additional scorer: partial ratio for single-word misspellings
            partial_results = process.extract(
                query,
                vocabulary,
                limit=min(max_results * 2, len(vocabulary)),
                scorer=fuzz.partial_ratio,
                score_cutoff=min_score_threshold * 50,  # Very permissive
            )
            secondary_results.extend(partial_results)

        # Merge and deduplicate results
        seen_words = set()
        all_results = []
        
        # Process primary results
        for result in primary_results:
            word, score, _ = result if len(result) == 3 else (result[0], result[1], 0)
            if word not in seen_words:
                seen_words.add(word)
                all_results.append((word, score / 100.0, 'primary'))
        
        # Process secondary results with different scoring
        for result in secondary_results:
            word, score, _ = result if len(result) == 3 else (result[0], result[1], 0)
            if word not in seen_words:
                seen_words.add(word)
                # Boost scores for challenging queries with more permissive scaling
                boosted_score = min(1.0, (score / 100.0) * 1.4)
                all_results.append((word, boosted_score, 'secondary'))

        # Apply adaptive length correction and filtering
        is_query_phrase = " " in query
        
        for word, base_score, method in all_results:
            # Adaptive scoring based on query difficulty
            if is_challenging:
                corrected_score = self._adaptive_length_correction(
                    query, word, base_score, is_query_phrase
                )
            else:
                corrected_score = apply_length_correction(
                    query, word, base_score,
                    is_query_phrase=is_query_phrase,
                    is_candidate_phrase=" " in word,
                )

            if corrected_score >= min_score_threshold:
                matches.append(
                    SearchResult(
                        word=word,
                        score=corrected_score,
                        method=SearchMethod.FUZZY,
                        lemmatized_word=None,
                        language=None,
                        metadata={"scoring_method": method} if method == 'secondary' else None,
                    )
                )

        # Sort by score and return top results
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:max_results]
    
    def _is_challenging_query(self, query: str) -> bool:
        """Detect if query is likely challenging (French phrases, complex words, etc.)."""
        # Multi-phrase indicators
        if " " in query and len(query.split()) >= 2:
            return True
        
        # Long words that are often misspelled
        if len(query) >= 10:
            return True
            
        # Common misspelling patterns
        challenging_patterns = [
            'tion', 'sion', 'ence', 'ance', 'ment', 'lle', 'ette',  # French endings
            'eau', 'ieu', 'oeu', 'oi',  # French vowel clusters
            'ph', 'gh', 'ough',  # English difficult patterns
        ]
        
        return any(pattern in query.lower() for pattern in challenging_patterns)
    
    def _adaptive_length_correction(
        self,
        query: str,
        word: str,
        base_score: float,
        is_query_phrase: bool,
    ) -> float:
        """Adaptive length correction for challenging queries."""
        query_len = len(query)
        word_len = len(word)
        length_diff = abs(query_len - word_len)
        
        # Be more lenient with length differences for challenging queries
        if is_query_phrase or query_len >= 10:
            # Reduce length penalty for phrases and long words
            length_penalty = min(0.3, length_diff * 0.02)
        else:
            # Standard penalty for simple words
            length_penalty = min(0.2, length_diff * 0.03)
        
        # Bonus for similar structure (word vs phrase)
        structure_bonus = 0.0
        if is_query_phrase and " " in word:
            structure_bonus = 0.1
        elif not is_query_phrase and " " not in word:
            structure_bonus = 0.05
            
        corrected_score = base_score - length_penalty + structure_bonus
        return max(0.0, min(1.0, corrected_score))
