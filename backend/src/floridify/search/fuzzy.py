"""
High-performance fuzzy search implementation.

Multiple fuzzy algorithms with automatic method selection for optimal results.
Supports typo tolerance, abbreviations, and phonetic matching.
"""

from __future__ import annotations

import re

import jellyfish
import polyleven  # type: ignore[import-not-found]
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from .constants import DEFAULT_MIN_SCORE, FuzzySearchMethod
from .corpus.core import Corpus


class FuzzyMatch(BaseModel):
    """Result from fuzzy search with method metadata."""

    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    method: FuzzySearchMethod = Field(..., description="Method used for matching")
    edit_distance: int = Field(default=0, ge=0, description="Edit distance (if applicable)")

    model_config = {"frozen": True}


class FuzzySearch:
    """
    High-performance fuzzy search with multiple algorithms.

    Implements automatic method selection based on query characteristics:
    - Short queries (≤3 chars): Jaro-Winkler for abbreviations
    - Medium queries (4-8 chars): RapidFuzz for general typos
    - Long queries (>8 chars): Hybrid approach with phonetic fallback

    Methods Explained:
    - RapidFuzz: Uses C++ optimized Levenshtein with ratio scoring
    - Jaro-Winkler: String similarity focusing on prefix matching (good for names)
    - Soundex: Phonetic algorithm grouping words by pronunciation
    - Levenshtein: Classic edit distance (insertions, deletions, substitutions)
    - Metaphone: Advanced phonetic matching with better accuracy than Soundex
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
        method: FuzzySearchMethod = FuzzySearchMethod.AUTO,
        min_score: float | None = None,
    ) -> list[FuzzyMatch]:
        """
        Fuzzy search using corpus object directly. 
        Synchronous for better performance - no async overhead for CPU-bound operations.
        """
        if not query.strip():
            return []
        
        return self._perform_search(query, corpus, max_results, method, min_score)

    def _perform_search(
        self,
        query: str,
        corpus: Corpus,
        max_results: int = 20,
        method: FuzzySearchMethod = FuzzySearchMethod.AUTO,
        min_score: float | None = None,
    ) -> list[FuzzyMatch]:
        """Internal search implementation with Corpus."""
        query = query.strip().lower()
        min_score_threshold = min_score if min_score is not None else self.min_score

        # Select method automatically if needed
        if method == FuzzySearchMethod.AUTO:
            method = self._select_optimal_method(query)

        # Smart candidate selection using corpus indices
        candidates = self._select_candidates(query, corpus, max_results)

        if not candidates:
            return []

        # Perform search with selected method on filtered candidates
        matches = self._search_with_method(
            query, candidates, corpus, method, max_results * 2, min_score_threshold
        )

        # Filter by score and limit results
        filtered_matches = [m for m in matches if m.score >= min_score_threshold]
        filtered_matches.sort(key=lambda m: m.score, reverse=True)

        return filtered_matches[:max_results]

    def _select_candidates(
        self, query: str, corpus: Corpus, max_results: int
    ) -> list[int]:
        """Select promising candidates using optimized corpus indices - 2-3x faster."""
        query_len = len(query)
        max_candidates = 1000
        
        # Use optimized single-call candidate selection
        candidates = corpus.get_candidates_optimized(
            query_len=query_len,
            prefix=query[:2] if query_len <= 4 else None,
            length_tolerance=2,
            max_candidates=max_candidates
        )
        
        return candidates

    def _search_with_method(
        self,
        query: str,
        candidate_indices: list[int],
        corpus: Corpus,
        method: FuzzySearchMethod,
        max_results: int,
        min_score_threshold: float,
    ) -> list[FuzzyMatch]:
        """Execute search with a specific method on candidate indices."""

        # Get candidate words from corpus using batch retrieval - 3-5x faster
        candidate_word_list = corpus.get_words_by_indices(candidate_indices)
        candidate_words = [(idx, word) for idx, word in zip(candidate_indices, candidate_word_list)]

        if method == FuzzySearchMethod.RAPIDFUZZ:
            return self._search_rapidfuzz(query, candidate_words, corpus, max_results, min_score_threshold)
        elif method == FuzzySearchMethod.JARO_WINKLER:
            return self._search_jaro_winkler(
                query, candidate_words, corpus, max_results, min_score_threshold
            )
        else:
            # Default to RapidFuzz for all other methods
            return self._search_rapidfuzz(query, candidate_words, corpus, max_results, min_score_threshold)

    def _search_rapidfuzz(
        self,
        query: str,
        candidate_words: list[tuple[int, str]],
        corpus: Corpus,
        max_results: int,
        min_score_threshold: float,
    ) -> list[FuzzyMatch]:
        """RapidFuzz search on pre-filtered candidates."""

        if not candidate_words:
            return []

        # Extract words for RapidFuzz (it expects strings)
        words = [word for _, word in candidate_words]
        
        # Use RapidFuzz on filtered candidates (much smaller search space)
        results = process.extract(
            query,
            words,
            limit=min(max_results * 2, len(words)),
            scorer=fuzz.WRatio,
            processor=lambda s: s.lower(),
        )

        matches = []
        is_query_phrase = " " in query.strip()

        for result in results:
            if len(result) == 3:
                word, score, _ = result
            else:
                word, score = result

            # Convert 0-100 score to 0.0-1.0
            base_score = score / 100.0

            # Apply length-aware scoring correction
            corrected_score = self._apply_length_correction(
                query, word, base_score, is_query_phrase
            )

            matches.append(
                FuzzyMatch(
                    word=word,
                    score=corrected_score,
                    method=FuzzySearchMethod.RAPIDFUZZ,
                )
            )

        # Sort by corrected scores
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _search_jaro_winkler(
        self,
        query: str,
        candidate_words: list[tuple[int, str]],
        corpus: Corpus,
        max_results: int,
        min_score_threshold: float,
    ) -> list[FuzzyMatch]:
        """Jaro-Winkler search on pre-filtered candidates."""

        matches = []

        for _, word in candidate_words:
            try:
                word_lower = word.lower()
                score = jellyfish.jaro_winkler_similarity(query, word_lower)

                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=score,
                        method=FuzzySearchMethod.JARO_WINKLER,
                        )
                )

            except Exception:
                continue

        # Sort and return top results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _select_optimal_method(self, query: str) -> FuzzySearchMethod:
        """
        Automatically select the best fuzzy method for a query.

        Strategy:
        - Very short (≤2): Jaro-Winkler (good for abbreviations)
        - Short (3): Jaro-Winkler or RapidFuzz
        - Medium (4-8): RapidFuzz (general typos)
        - Long (>8): RapidFuzz with phonetic fallback
        - Contains numbers: Exact matching preferred
        """
        query_len = len(query)
        has_numbers = bool(re.search(r"\d", query))

        if has_numbers:
            # Numbers: RapidFuzz handles mixed alphanumeric content well
            return FuzzySearchMethod.RAPIDFUZZ
        elif query_len <= 2:
            # Very short: Jaro-Winkler for abbreviations
            return FuzzySearchMethod.JARO_WINKLER
        elif query_len <= 3:
            # Short: Jaro-Winkler excels at short strings
            return FuzzySearchMethod.JARO_WINKLER
        elif query_len <= 8:
            # Medium: RapidFuzz (C++ optimized) for general typos
            return FuzzySearchMethod.RAPIDFUZZ
        else:
            # Long: RapidFuzz with potential phonetic fallback
            return FuzzySearchMethod.RAPIDFUZZ

    def _apply_length_correction(
        self, query: str, candidate: str, base_score: float, is_query_phrase: bool
    ) -> float:
        """Apply length-aware correction to prevent short fragment bias."""
        # No correction needed for perfect matches
        if base_score >= 0.99:
            return base_score

        # Pre-compute lengths and lowercase versions (minimize string operations)
        query_len = len(query)
        candidate_len = len(candidate)
        is_candidate_phrase = " " in candidate
        
        # Only compute lowercase versions when needed
        query_lower = query.lower()
        candidate_lower = candidate.lower()

        # Check if query is a prefix of the candidate (important for phrases)
        is_prefix_match = candidate_lower.startswith(query_lower)

        # Check if query matches the first word of a phrase exactly
        first_word_match = False
        if is_candidate_phrase and not is_query_phrase:
            # Find first space index instead of split() to avoid list allocation
            space_idx = candidate_lower.find(' ')
            if space_idx > 0:
                first_word_match = query_lower == candidate_lower[:space_idx]

        # Length ratio penalty for very different lengths
        min_len = min(query_len, candidate_len)
        max_len = max(query_len, candidate_len)
        length_ratio = min_len / max_len if max_len > 0 else 1.0

        # Phrase matching bonus/penalty
        phrase_penalty = 1.0
        if is_query_phrase and not is_candidate_phrase:
            # Query is phrase but candidate is not - significant penalty
            phrase_penalty = 0.7
        elif not is_query_phrase and is_candidate_phrase:
            # Query is word but candidate is phrase
            if is_prefix_match or first_word_match:
                # Strong bonus for prefix or first word matches
                phrase_penalty = 1.2
            else:
                # Only slight penalty for non-prefix matches
                phrase_penalty = 0.95
        elif is_query_phrase and is_candidate_phrase:
            # Both phrases - bonus for length similarity
            phrase_penalty = 1.1 if length_ratio > 0.6 else 1.0

        # Short fragment penalty (aggressive for very short candidates)
        if candidate_len <= 3 and query_len > 6:
            # Very short candidates for longer queries get heavy penalty
            short_penalty = 0.5
        elif candidate_len < query_len * 0.5:
            # Moderately short candidates get moderate penalty
            short_penalty = 0.75
        else:
            short_penalty = 1.0

        # Prefix match bonus
        prefix_bonus = 1.3 if is_prefix_match else 1.0

        # First word match bonus (for phrases)
        first_word_bonus = 1.2 if first_word_match else 1.0

        # Combined correction
        corrected_score = (
            base_score
            * length_ratio
            * phrase_penalty
            * short_penalty
            * prefix_bonus
            * first_word_bonus
        )

        # Ensure we don't exceed 1.0 or go below 0.0
        return max(0.0, min(1.0, corrected_score))

    def _calculate_string_similarity(self, s1: str, s2: str) -> float:
        """Calculate basic string similarity for phonetic matches."""
        if s1 == s2:
            return 1.0

        # Use Levenshtein distance for similarity
        distance: float = polyleven.levenshtein(s1.lower(), s2.lower())

        max_len = max(len(s1), len(s2))

        if max_len == 0:
            return 1.0

        return 1.0 - (distance / max_len)
