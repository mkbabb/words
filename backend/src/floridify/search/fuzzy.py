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

from .constants import FuzzySearchMethod
from .vocabulary import SharedVocabularyStore


class FuzzyMatch(BaseModel):
    """Result from fuzzy search with method metadata."""

    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    method: FuzzySearchMethod = Field(..., description="Method used for matching")
    edit_distance: int = Field(default=0, ge=0, description="Edit distance (if applicable)")
    is_phrase: bool = Field(default=False, description="Whether match is a phrase")

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

    def __init__(self, min_score: float = 0.6) -> None:
        """
        Initialize fuzzy search engine.

        Args:
            min_score: Minimum similarity score to include in results
        """
        self.min_score = min_score


    def search(
        self,
        query: str,
        vocab_store: SharedVocabularyStore,
        max_results: int = 20,
        method: FuzzySearchMethod = FuzzySearchMethod.AUTO,
        min_score: float | None = None,
    ) -> list[FuzzyMatch]:
        """
        Fuzzy search using SharedVocabularyStore with candidate filtering.
        """
        if not query.strip() or not vocab_store.is_loaded:
            return []

        query = query.strip().lower()
        min_score_threshold = min_score if min_score is not None else self.min_score

        # Select method automatically if needed
        if method == FuzzySearchMethod.AUTO:
            method = self._select_optimal_method(query)

        # Smart candidate selection based on query characteristics
        candidates = self._select_candidates(query, vocab_store, max_results)

        if not candidates:
            return []

        # Perform search with selected method on filtered candidates
        matches = self._search_with_method(
            query, candidates, vocab_store, method, max_results * 2, min_score_threshold
        )

        # Filter by score and limit results
        filtered_matches = [m for m in matches if m.score >= min_score_threshold]
        filtered_matches.sort(key=lambda m: m.score, reverse=True)

        return filtered_matches[:max_results]

    def _select_candidates(
        self, query: str, vocab_store: SharedVocabularyStore, max_results: int
    ) -> list[int]:
        """Select promising candidates using vocabulary store indices."""
        query_len = len(query)
        candidates = []

        # Strategy 1: Length-based filtering (±2 characters for fuzzy tolerance)
        length_candidates = vocab_store.get_candidates_by_length(query_len, tolerance=2)
        candidates.extend(length_candidates)

        # Strategy 2: Prefix matching for short queries (boost performance)
        if query_len <= 4:
            prefix_candidates = vocab_store.get_candidates_by_prefix(query[:2], max_candidates=200)
            candidates.extend(prefix_candidates)

        # Remove duplicates and limit candidates for performance
        unique_candidates = list(set(candidates))

        # Limit total candidates to prevent performance degradation
        max_candidates = min(1000, len(unique_candidates))
        if len(unique_candidates) > max_candidates:
            # Keep the first max_candidates (length-based candidates are prioritized)
            unique_candidates = unique_candidates[:max_candidates]

        return unique_candidates

    def _search_with_method(
        self,
        query: str,
        candidate_indices: list[int],
        vocab_store: SharedVocabularyStore,
        method: FuzzySearchMethod,
        max_results: int,
        min_score_threshold: float,
    ) -> list[FuzzyMatch]:
        """Execute search with a specific method on candidate indices."""

        # Get candidate words from vocabulary store
        candidate_words = vocab_store.get_words(candidate_indices)

        if method == FuzzySearchMethod.RAPIDFUZZ:
            return self._search_rapidfuzz(query, candidate_words, max_results, min_score_threshold)
        elif method == FuzzySearchMethod.JARO_WINKLER:
            return self._search_jaro_winkler(query, candidate_words, max_results, min_score_threshold)
        else:
            # Default to RapidFuzz for all other methods
            return self._search_rapidfuzz(query, candidate_words, max_results, min_score_threshold)

    def _search_rapidfuzz(
        self,
        query: str,
        candidate_words: list[str],
        max_results: int,
        min_score_threshold: float,
    ) -> list[FuzzyMatch]:
        """RapidFuzz search on pre-filtered candidates."""

        if not candidate_words:
            return []

        # Use RapidFuzz on filtered candidates (much smaller search space)
        results = process.extract(
            query,
            candidate_words,
            limit=min(max_results * 2, len(candidate_words)),
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
                    is_phrase=" " in word,
                )
            )

        # Sort by corrected scores
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _search_jaro_winkler(
        self,
        query: str,
        candidate_words: list[str],
        max_results: int,
        min_score_threshold: float,
    ) -> list[FuzzyMatch]:
        """Jaro-Winkler search on pre-filtered candidates."""

        matches = []

        for word in candidate_words:
            try:
                word_lower = word.lower()
                score = jellyfish.jaro_winkler_similarity(query, word_lower)

                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=score,
                        method=FuzzySearchMethod.JARO_WINKLER,
                        is_phrase=" " in word,
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
        query_len = len(query.strip())
        candidate_len = len(candidate.strip())
        is_candidate_phrase = " " in candidate.strip()
        query_lower = query.strip().lower()
        candidate_lower = candidate.strip().lower()

        # No correction needed for perfect matches
        if base_score >= 0.99:
            return base_score

        # Check if query is a prefix of the candidate (important for phrases)
        is_prefix_match = candidate_lower.startswith(query_lower)

        # Check if query matches the first word of a phrase exactly
        first_word_match = False
        if is_candidate_phrase and not is_query_phrase:
            first_word = candidate_lower.split()[0]
            first_word_match = query_lower == first_word

        # Length ratio penalty for very different lengths
        length_ratio = min(query_len, candidate_len) / max(query_len, candidate_len)

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
