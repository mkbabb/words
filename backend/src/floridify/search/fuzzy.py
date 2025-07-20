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

        # Cache for performance optimization
        self._last_vocabulary_hash: int = 0
        self._cached_lowercase_words: list[str] = []
        self._phrase_words: set[str] = set()
        self._single_words: set[str] = set()

    def search(
        self,
        query: str,
        word_list: list[str],
        max_results: int = 20,
        method: FuzzySearchMethod = FuzzySearchMethod.AUTO,
        min_score: float | None = None,
    ) -> list[FuzzyMatch]:
        """
        Perform fuzzy search with automatic or specified method.

        Args:
            query: Search query
            word_list: List of words to search against
            max_results: Maximum number of results
            method: Search method to use
            min_score: Override default minimum score

        Returns:
            List of fuzzy matches sorted by score
        """
        if not query.strip() or not word_list:
            return []

        query = query.strip().lower()
        score_threshold = min_score if min_score is not None else self.min_score

        # Cache vocabulary processing - use object id for performance
        vocab_id = id(word_list)
        if vocab_id != self._last_vocabulary_hash:
            self._cache_vocabulary(word_list)
            self._last_vocabulary_hash = vocab_id

        # Select method automatically if needed
        if method == FuzzySearchMethod.AUTO:
            method = self._select_optimal_method(query)

        # Perform search with selected method
        matches = self._search_with_method(query, word_list, method, max_results * 2)

        # Filter by score and limit results
        filtered_matches = [m for m in matches if m.score >= score_threshold]
        filtered_matches.sort(key=lambda m: m.score, reverse=True)

        return filtered_matches[:max_results]

    def _cache_vocabulary(self, word_list: list[str]) -> None:
        """Cache vocabulary preprocessing for performance."""
        self._cached_lowercase_words = [word.lower() for word in word_list]
        self._phrase_words = {word for word in word_list if " " in word}
        self._single_words = {word for word in word_list if " " not in word}

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

    def _search_with_method(
        self,
        query: str,
        word_list: list[str],
        method: FuzzySearchMethod,
        max_results: int,
    ) -> list[FuzzyMatch]:
        """Execute search with a specific method."""

        if method == FuzzySearchMethod.RAPIDFUZZ:
            return self._search_rapidfuzz(query, word_list, max_results)
        elif method == FuzzySearchMethod.JARO_WINKLER:
            return self._search_jaro_winkler(query, word_list, max_results)
        elif method == FuzzySearchMethod.SOUNDEX:
            return self._search_soundex(query, word_list, max_results)
        elif method == FuzzySearchMethod.METAPHONE:
            return self._search_metaphone(query, word_list, max_results)
        elif method == FuzzySearchMethod.LEVENSHTEIN:
            return self._search_polyleven(query, word_list, max_results)
        else:
            # Default to optimized RapidFuzz
            return self._search_rapidfuzz(query, word_list, max_results)

    def _search_rapidfuzz(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using RapidFuzz library (C++ optimized) with length bias correction."""

        # Increase limit to get more candidates for re-scoring
        search_limit = min(max_results * 3, len(word_list))

        # Use process.extract for efficient top-k search
        results = process.extract(
            query,
            word_list,
            limit=search_limit,
            scorer=fuzz.WRatio,  # Weighted ratio for better results
        )

        matches = []
        is_query_phrase = " " in query.strip()

        for result in results:
            # RapidFuzz returns (string, score, index) tuples
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

        # Sort by corrected scores and limit results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _search_jaro_winkler(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using Jaro-Winkler similarity with early termination."""

        matches: list[FuzzyMatch] = []
        min_score_seen = 0.0

        for word in word_list:
            try:
                # Use cached lowercase if available
                word_lower = word.lower() if not self._cached_lowercase_words else word.lower()
                score = jellyfish.jaro_winkler_similarity(query, word_lower)

                # Early termination optimization
                if score > min_score_seen or len(matches) < max_results:
                    matches.append(
                        FuzzyMatch(
                            word=word,
                            score=score,
                            method=FuzzySearchMethod.JARO_WINKLER,
                            is_phrase=" " in word,
                        )
                    )

                    # Keep only top results and track minimum
                    if len(matches) > max_results * 2:
                        matches.sort(key=lambda m: m.score, reverse=True)
                        matches = matches[:max_results]
                        min_score_seen = matches[-1].score

            except Exception:
                continue

        # Final sort and return top results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _search_soundex(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using Soundex phonetic matching."""

        try:
            query_soundex = jellyfish.soundex(query)
        except Exception:
            return []

        matches = []
        for word in word_list:
            try:
                word_soundex = jellyfish.soundex(word.lower())
                if query_soundex == word_soundex:
                    # Phonetic match - calculate additional similarity
                    similarity = self._calculate_string_similarity(query, word.lower())
                    matches.append(
                        FuzzyMatch(
                            word=word,
                            score=similarity,
                            method=FuzzySearchMethod.SOUNDEX,
                            is_phrase=" " in word,
                        )
                    )
            except Exception:
                continue

        # Sort and return top results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _search_metaphone(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using Metaphone phonetic matching."""

        try:
            query_metaphone = jellyfish.metaphone(query)
        except Exception:
            return []

        matches = []
        for word in word_list:
            try:
                word_metaphone = jellyfish.metaphone(word.lower())
                if query_metaphone == word_metaphone:
                    # Phonetic match - calculate additional similarity
                    similarity = self._calculate_string_similarity(query, word.lower())
                    matches.append(
                        FuzzyMatch(
                            word=word,
                            score=similarity,
                            method=FuzzySearchMethod.METAPHONE,
                            is_phrase=" " in word,
                        )
                    )
            except Exception:
                continue

        # Sort and return top results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _search_polyleven(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using polyleven library (Rust-optimized Levenshtein)."""
        matches = []
        query_lower = query.lower()

        for word in word_list:
            word_lower = word.lower()

            # Calculate edit distance using Rust-optimized polyleven
            distance = polyleven.levenshtein(query_lower, word_lower)
            max_length = max(len(query_lower), len(word_lower))

            if max_length == 0:
                similarity = 1.0
            else:
                similarity = 1.0 - (distance / max_length)

            if similarity >= self.min_score:
                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=similarity,
                        method=FuzzySearchMethod.LEVENSHTEIN,
                        edit_distance=distance,
                        is_phrase=" " in word,
                    )
                )

        # Sort and return top results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _apply_length_correction(
        self, query: str, candidate: str, base_score: float, is_query_phrase: bool
    ) -> float:
        """Apply length-aware correction to prevent short fragment bias."""
        query_len = len(query.strip())
        candidate_len = len(candidate.strip())
        is_candidate_phrase = " " in candidate.strip()

        # No correction needed for perfect matches
        if base_score >= 0.99:
            return base_score

        # Length ratio penalty for very different lengths
        length_ratio = min(query_len, candidate_len) / max(query_len, candidate_len)

        # Phrase matching bonus/penalty
        phrase_penalty = 1.0
        if is_query_phrase and not is_candidate_phrase:
            # Query is phrase but candidate is not - significant penalty
            phrase_penalty = 0.7
        elif not is_query_phrase and is_candidate_phrase:
            # Query is word but candidate is phrase - moderate penalty
            phrase_penalty = 0.85
        elif is_query_phrase and is_candidate_phrase:
            # Both phrases - bonus for length similarity
            phrase_penalty = 1.1 if length_ratio > 0.7 else 1.0

        # Short fragment penalty (aggressive for very short candidates)
        if candidate_len <= 3 and query_len > 6:
            # Very short candidates for longer queries get heavy penalty
            short_penalty = 0.5
        elif candidate_len < query_len * 0.5:
            # Moderately short candidates get moderate penalty
            short_penalty = 0.75
        else:
            short_penalty = 1.0

        # Combined correction
        corrected_score = base_score * length_ratio * phrase_penalty * short_penalty

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
