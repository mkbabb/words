"""Fuzzy search implementation with VSCode-style matching."""

from __future__ import annotations

import re
from typing import NamedTuple

from fuzzywuzzy import fuzz


class FuzzyMatch(NamedTuple):
    """Represents a fuzzy search match with score and metadata."""
    score: float
    word: str
    match_type: str  # 'exact', 'prefix', 'substring', 'fuzzy'
    

class FuzzyMatcher:
    """VSCode-style fuzzy string matcher with advanced scoring."""
    
    def __init__(self, threshold: float = 0.6) -> None:
        """Initialize fuzzy matcher.
        
        Args:
            threshold: Minimum score to include in results (0.0 to 1.0)
        """
        self.threshold = threshold
    
    def match(self, pattern: str, candidates: list[str], max_results: int = 20) -> list[FuzzyMatch]:
        """Find fuzzy matches for pattern in candidates.
        
        Args:
            pattern: Search pattern
            candidates: List of words to search
            max_results: Maximum number of results to return
            
        Returns:
            List of FuzzyMatch objects sorted by score (highest first)
        """
        if not pattern.strip():
            return []
        
        pattern = pattern.lower().strip()
        matches = []
        
        for candidate in candidates:
            score = self._calculate_score(pattern, candidate.lower())
            if score >= self.threshold:
                match_type = self._determine_match_type(pattern, candidate.lower())
                matches.append(FuzzyMatch(score, candidate, match_type))
        
        # Sort by score (descending) and return top results
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:max_results]
    
    def _calculate_score(self, pattern: str, candidate: str) -> float:
        """Calculate comprehensive fuzzy match score."""
        if pattern == candidate:
            return 1.0
        
        # Component scores
        exact_score = self._exact_match_score(pattern, candidate)
        prefix_score = self._prefix_score(pattern, candidate)
        substring_score = self._substring_score(pattern, candidate)
        sequence_score = self._sequence_score(pattern, candidate)
        fuzzy_score = self._fuzzy_score(pattern, candidate)
        
        # Weighted combination
        weights = {
            'exact': 1.0,
            'prefix': 0.9,
            'substring': 0.7,
            'sequence': 0.6,
            'fuzzy': 0.4,
        }
        
        final_score = max(
            exact_score * weights['exact'],
            prefix_score * weights['prefix'],
            substring_score * weights['substring'],
            sequence_score * weights['sequence'],
            fuzzy_score * weights['fuzzy'],
        )
        
        # Apply length penalty for very different lengths
        length_ratio = min(len(pattern), len(candidate)) / max(len(pattern), len(candidate))
        length_penalty = 0.9 + (0.1 * length_ratio)
        
        return final_score * length_penalty
    
    def _exact_match_score(self, pattern: str, candidate: str) -> float:
        """Score for exact matches."""
        return 1.0 if pattern == candidate else 0.0
    
    def _prefix_score(self, pattern: str, candidate: str) -> float:
        """Score for prefix matches."""
        if candidate.startswith(pattern):
            # Bonus for shorter candidates (more precise match)
            return 0.95 + (0.05 * (len(pattern) / len(candidate)))
        return 0.0
    
    def _substring_score(self, pattern: str, candidate: str) -> float:
        """Score for substring matches."""
        if pattern in candidate:
            # Position matters - earlier is better
            position = candidate.find(pattern)
            position_bonus = 1.0 - (position / len(candidate))
            
            # Length ratio matters
            length_bonus = len(pattern) / len(candidate)
            
            return 0.7 + (0.15 * position_bonus) + (0.15 * length_bonus)
        return 0.0
    
    def _sequence_score(self, pattern: str, candidate: str) -> float:
        """Score for character sequence matches (VSCode-style)."""
        if not pattern or not candidate:
            return 0.0
        
        pattern_chars = list(pattern)
        candidate_chars = list(candidate)
        
        matches = 0
        consecutive_matches = 0
        max_consecutive = 0
        pattern_idx = 0
        
        for char in candidate_chars:
            if pattern_idx < len(pattern_chars) and char == pattern_chars[pattern_idx]:
                matches += 1
                consecutive_matches += 1
                max_consecutive = max(max_consecutive, consecutive_matches)
                pattern_idx += 1
            else:
                consecutive_matches = 0
        
        if matches == 0:
            return 0.0
        
        # Base score from character matches
        match_ratio = matches / len(pattern)
        
        # Bonus for consecutive matches
        consecutive_bonus = max_consecutive / len(pattern)
        
        # Bonus for matching all characters
        completion_bonus = 1.0 if pattern_idx == len(pattern) else 0.0
        
        return (match_ratio * 0.5) + (consecutive_bonus * 0.3) + (completion_bonus * 0.2)
    
    def _fuzzy_score(self, pattern: str, candidate: str) -> float:
        """Score using fuzzy string matching library."""
        # Use fuzzywuzzy for additional fuzzy matching
        ratio = fuzz.ratio(pattern, candidate) / 100.0
        partial_ratio = fuzz.partial_ratio(pattern, candidate) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(pattern, candidate) / 100.0
        
        # Return the best score
        return max(ratio, partial_ratio, token_sort_ratio)
    
    def _determine_match_type(self, pattern: str, candidate: str) -> str:
        """Determine the type of match for display purposes."""
        if pattern == candidate:
            return 'exact'
        elif candidate.startswith(pattern):
            return 'prefix'
        elif pattern in candidate:
            return 'substring'
        else:
            return 'fuzzy'


def find_abbreviation_matches(pattern: str, candidates: list[str]) -> list[FuzzyMatch]:
    """Find matches where pattern could be an abbreviation.
    
    Example: 'syn' matches 'synonym', 'synthesis', 'synchronous'
    """
    if len(pattern) < 2:
        return []
    
    matches = []
    pattern = pattern.lower()
    
    for candidate in candidates:
        candidate_lower = candidate.lower()
        
        # Check if pattern characters appear in order at word boundaries or start of word
        if _is_abbreviation_match(pattern, candidate_lower):
            # Score based on how well the abbreviation fits
            score = _score_abbreviation(pattern, candidate_lower)
            if score > 0.5:  # Minimum threshold for abbreviations
                matches.append(FuzzyMatch(score, candidate, 'abbreviation'))
    
    return sorted(matches, key=lambda x: x.score, reverse=True)


def _is_abbreviation_match(pattern: str, candidate: str) -> bool:
    """Check if pattern could be an abbreviation of candidate."""
    pattern_idx = 0
    
    # Must start with first character
    if not candidate.startswith(pattern[0]):
        return False
    
    pattern_idx = 1
    
    for i in range(1, len(candidate)):
        if pattern_idx < len(pattern):
            # Check for next pattern character at word boundaries or after vowels
            if candidate[i] == pattern[pattern_idx]:
                # Good if it's after a vowel or at a word boundary
                if i == 0 or candidate[i-1] in 'aeiou' or not candidate[i-1].isalpha():
                    pattern_idx += 1
    
    return pattern_idx == len(pattern)


def _score_abbreviation(pattern: str, candidate: str) -> float:
    """Score how well pattern works as an abbreviation of candidate."""
    # Simple scoring based on pattern coverage and candidate length
    coverage = len(pattern) / len(candidate)
    
    # Prefer shorter candidates for abbreviations
    length_bonus = 1.0 / (1.0 + (len(candidate) - len(pattern)) * 0.1)
    
    return coverage * length_bonus * 0.8  # Max score of 0.8 for abbreviations