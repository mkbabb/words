"""
High-performance fuzzy search implementation.

Multiple fuzzy algorithms with automatic method selection for optimal results.
Supports typo tolerance, abbreviations, and phonetic matching.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

import jellyfish
import polyleven  # type: ignore[import-not-found]
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process


class FuzzySearchMethod(Enum):
    """Available fuzzy search methods with characteristics."""

    RAPIDFUZZ = "rapidfuzz"  # General-purpose, C++ optimized
    LEVENSHTEIN = "levenshtein"  # Classic edit distance
    JARO_WINKLER = "jaro_winkler"  # Good for names and abbreviations
    SOUNDEX = "soundex"  # Phonetic matching
    METAPHONE = "metaphone"  # Advanced phonetic matching
    AUTO = "auto"  # Automatic method selection


class FuzzyMatch(BaseModel):
    """Result from fuzzy search with method metadata."""

    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    method: FuzzySearchMethod = Field(..., description="Method used for matching")
    edit_distance: int = Field(
        default=0, ge=0, description="Edit distance (if applicable)"
    )
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

        # Select method automatically if needed
        if method == FuzzySearchMethod.AUTO:
            method = self._select_optimal_method(query)

        # Perform search with selected method
        matches = self._search_with_method(query, word_list, method, max_results * 2)

        # Filter by score and limit results
        filtered_matches = [m for m in matches if m.score >= score_threshold]
        filtered_matches.sort(key=lambda m: m.score, reverse=True)

        return filtered_matches[:max_results]

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
        """Search using RapidFuzz library (C++ optimized)."""

        # Use process.extract for efficient top-k search
        results = process.extract(
            query,
            word_list,
            limit=max_results,
            scorer=fuzz.WRatio,  # Weighted ratio for better results
        )

        matches = []
        for result in results:
            # RapidFuzz returns (string, score, index) tuples
            if len(result) == 3:
                word, score, _ = result
            else:
                word, score = result

            # Convert 0-100 score to 0.0-1.0
            normalized_score = score / 100.0

            matches.append(
                FuzzyMatch(
                    word=word,
                    score=normalized_score,
                    method=FuzzySearchMethod.RAPIDFUZZ,
                    is_phrase=" " in word,
                )
            )

        return matches

    def _search_jaro_winkler(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using Jaro-Winkler similarity."""

        matches = []
        for word in word_list:
            try:
                score = jellyfish.jaro_winkler_similarity(query, word.lower())
                if score > 0:
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

    def _search_levenshtein(
        self, query: str, word_list: list[str], max_results: int
    ) -> list[FuzzyMatch]:
        """Search using basic Levenshtein distance."""
        matches = []

        for word in word_list:
            word_lower = word.lower()
            distance = self._levenshtein_distance(query, word_lower)
            max_len = max(len(query), len(word_lower))

            if max_len == 0:
                score = 1.0
            else:
                score = 1.0 - (distance / max_len)

            if score > 0:
                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=score,
                        method=FuzzySearchMethod.LEVENSHTEIN,
                        edit_distance=distance,
                        is_phrase=" " in word,
                    )
                )

        # Sort and return top results
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:max_results]

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _calculate_string_similarity(self, s1: str, s2: str) -> float:
        """Calculate basic string similarity for phonetic matches."""
        if s1 == s2:
            return 1.0

        # Use Levenshtein distance for similarity
        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))

        if max_len == 0:
            return 1.0

        return 1.0 - (distance / max_len)
