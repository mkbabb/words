"""Traditional fuzzy search implementation with optimized algorithms.

Implements multiple traditional fuzzy search approaches:
1. RapidFuzz for high-performance string similarity
2. Optimized Levenshtein distance with early termination
3. Jaro-Winkler similarity for name-like strings
4. Soundex and Metaphone for phonetic matching
5. VSCode-style character sequence matching
"""

from __future__ import annotations

import re
from typing import NamedTuple

from rapidfuzz import fuzz, process

from .enums import ScoringMethod, TraditionalSearchMethod


class FuzzyMatch(NamedTuple):
    """Represents a fuzzy search match with detailed scoring."""

    word: str
    score: float
    distance: int
    method: str
    explanation: str


class TraditionalFuzzySearch:
    """High-performance traditional fuzzy search with multiple algorithms."""

    def __init__(self, score_threshold: float = 0.6) -> None:
        self.score_threshold = score_threshold

        # Precompiled regex patterns for efficiency
        self.vowel_pattern = re.compile(r"[aeiouAEIOU]")
        self.consonant_pattern = re.compile(r"[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]")

    def search(
        self,
        query: str,
        word_list: list[str],
        max_results: int = 20,
        methods: list[TraditionalSearchMethod] | None = None,
    ) -> list[FuzzyMatch]:
        """Comprehensive fuzzy search using multiple methods."""
        if methods is None:
            methods = [
                TraditionalSearchMethod.RAPIDFUZZ,
                TraditionalSearchMethod.JARO_WINKLER,
                TraditionalSearchMethod.VSCODE,
                TraditionalSearchMethod.PHONETIC,
            ]

        query_clean = query.lower().strip()
        if not query_clean:
            return []

        all_matches: list[FuzzyMatch] = []

        # Method 1: RapidFuzz (fastest, most accurate for most cases)
        if TraditionalSearchMethod.RAPIDFUZZ in methods:
            rapidfuzz_matches = self._rapidfuzz_search(query_clean, word_list, max_results * 2)
            all_matches.extend(rapidfuzz_matches)

        # Method 2: Jaro-Winkler (good for name-like strings)
        if TraditionalSearchMethod.JARO_WINKLER in methods:
            jaro_matches = self._jaro_winkler_search(query_clean, word_list, max_results)
            all_matches.extend(jaro_matches)

        # Method 3: VSCode-style sequence matching
        if TraditionalSearchMethod.VSCODE in methods:
            vscode_matches = self._vscode_search(query_clean, word_list, max_results)
            all_matches.extend(vscode_matches)

        # Method 4: Phonetic matching (Soundex/Metaphone)
        if TraditionalSearchMethod.PHONETIC in methods:
            phonetic_matches = self._phonetic_search(query_clean, word_list, max_results)
            all_matches.extend(phonetic_matches)

        # Deduplicate and merge scores
        merged_matches = self._merge_duplicate_matches(all_matches)

        # Filter by threshold and sort
        filtered_matches = [
            match for match in merged_matches if match.score >= self.score_threshold
        ]

        filtered_matches.sort(key=lambda x: x.score, reverse=True)
        return filtered_matches[:max_results]

    def _rapidfuzz_search(self, query: str, word_list: list[str], limit: int) -> list[FuzzyMatch]:
        """High-performance fuzzy search using RapidFuzz."""
        try:
            # Use process.extract for fast bulk processing
            results = process.extract(
                query,
                word_list,
                scorer=fuzz.WRatio,  # Weighted ratio for best accuracy
                limit=limit,
            )

            matches = []
            for word, score, _ in results:
                # Convert percentage to 0-1 scale
                normalized_score = score / 100.0

                # Calculate edit distance for additional info
                distance = self._levenshtein_distance(query, word.lower())

                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=normalized_score,
                        distance=distance,
                        method=ScoringMethod.WEIGHTED_RATIO.value,
                        explanation=f"Weighted ratio similarity: {score}%",
                    )
                )

            return matches

        except Exception:
            return []

    def _jaro_winkler_search(
        self, query: str, word_list: list[str], limit: int
    ) -> list[FuzzyMatch]:
        """Jaro-Winkler similarity search (good for names and proper nouns)."""
        matches = []

        for word in word_list:
            word_lower = word.lower()
            similarity = self._jaro_winkler_similarity(query, word_lower)

            if similarity >= self.score_threshold:
                distance = self._levenshtein_distance(query, word_lower)
                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=similarity,
                        distance=distance,
                        method=ScoringMethod.JARO_WINKLER.value,
                        explanation=f"Jaro-Winkler similarity: {similarity:.3f}",
                    )
                )

        # Sort and limit
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:limit]

    def _vscode_search(self, query: str, word_list: list[str], limit: int) -> list[FuzzyMatch]:
        """VSCode-style character sequence matching."""
        matches = []

        for word in word_list:
            word_lower = word.lower()
            score = self._vscode_score(query, word_lower)

            if score >= self.score_threshold:
                distance = self._levenshtein_distance(query, word_lower)
                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=score,
                        distance=distance,
                        method=ScoringMethod.VSCODE_SEQUENCE.value,
                        explanation=f"Character sequence match: {score:.3f}",
                    )
                )

        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:limit]

    def _phonetic_search(self, query: str, word_list: list[str], limit: int) -> list[FuzzyMatch]:
        """Phonetic matching using Soundex and Metaphone algorithms."""
        query_soundex = self._soundex(query)
        query_metaphone = self._metaphone(query)

        matches = []

        for word in word_list:
            word_lower = word.lower()
            word_soundex = self._soundex(word_lower)
            word_metaphone = self._metaphone(word_lower)

            # Score based on phonetic similarity
            score = 0.0
            explanations = []

            # Soundex match
            if query_soundex == word_soundex and query_soundex != "0000":
                score += 0.7
                explanations.append("Soundex match")

            # Metaphone match
            if query_metaphone == word_metaphone and query_metaphone:
                score += 0.8
                explanations.append("Metaphone match")

            # Partial phonetic similarity
            if score == 0 and query_soundex and word_soundex:
                soundex_sim = self._string_similarity(query_soundex, word_soundex)
                if soundex_sim > 0.5:
                    score = soundex_sim * 0.5
                    explanations.append(f"Partial Soundex: {soundex_sim:.3f}")

            if score >= self.score_threshold:
                distance = self._levenshtein_distance(query, word_lower)
                explanation = ", ".join(explanations) if explanations else "Phonetic similarity"

                matches.append(
                    FuzzyMatch(
                        word=word,
                        score=score,
                        distance=distance,
                        method=ScoringMethod.PHONETIC_MATCH.value,
                        explanation=explanation,
                    )
                )

        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:limit]

    def _merge_duplicate_matches(self, matches: list[FuzzyMatch]) -> list[FuzzyMatch]:
        """Merge duplicate word matches, keeping the best score and combining methods."""
        word_to_best: dict[str, FuzzyMatch] = {}

        for match in matches:
            word = match.word.lower()

            if word not in word_to_best or match.score > word_to_best[word].score:
                # Keep the match with the highest score
                if word in word_to_best:
                    # Combine method information
                    existing = word_to_best[word]
                    combined_method = f"{existing.method}+{match.method}"
                    combined_explanation = f"{existing.explanation}; {match.explanation}"

                    word_to_best[word] = FuzzyMatch(
                        word=match.word,  # Keep original casing from best match
                        score=match.score,
                        distance=min(existing.distance, match.distance),
                        method=combined_method,
                        explanation=combined_explanation,
                    )
                else:
                    word_to_best[word] = match

        return list(word_to_best.values())

    def _vscode_score(self, pattern: str, word: str) -> float:
        """Calculate VSCode-style character sequence score."""
        if not pattern or not word:
            return 0.0

        if pattern == word:
            return 1.0

        # Check if pattern is a subsequence of word
        pattern_chars = list(pattern)
        word_chars = list(word)

        matches = 0
        consecutive_matches = 0
        max_consecutive = 0
        pattern_idx = 0
        position_bonus = 0.0

        for word_idx, char in enumerate(word_chars):
            if pattern_idx < len(pattern_chars) and char == pattern_chars[pattern_idx]:
                matches += 1
                consecutive_matches += 1
                max_consecutive = max(max_consecutive, consecutive_matches)

                # Earlier matches get higher bonus
                position_bonus += (1.0 - word_idx / len(word_chars)) * 0.1

                pattern_idx += 1
            else:
                consecutive_matches = 0

        if matches == 0:
            return 0.0

        # Base score from character matches
        match_ratio = matches / len(pattern)

        # Bonus for consecutive matches
        consecutive_bonus = max_consecutive / len(pattern) * 0.3

        # Bonus for completing the pattern
        completion_bonus = 0.2 if pattern_idx == len(pattern) else 0.0

        # Length penalty for very different lengths
        length_ratio = min(len(pattern), len(word)) / max(len(pattern), len(word))
        length_penalty = length_ratio * 0.1

        final_score = (
            match_ratio * 0.4
            + consecutive_bonus
            + completion_bonus
            + position_bonus
            + length_penalty
        )

        return min(final_score, 1.0)

    def _jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity."""
        # Jaro similarity
        jaro_sim = self._jaro_similarity(s1, s2)

        if jaro_sim < 0.7:
            return jaro_sim

        # Common prefix bonus (up to 4 characters)
        prefix_len = 0
        for i in range(min(4, len(s1), len(s2))):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break

        # Winkler modification
        return jaro_sim + (0.1 * prefix_len * (1 - jaro_sim))

    def _jaro_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro similarity."""
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Maximum allowed distance
        match_distance = max(len1, len2) // 2 - 1
        if match_distance < 0:
            match_distance = 0

        # Initialize match arrays
        s1_matches = [False] * len1
        s2_matches = [False] * len2

        matches = 0
        transpositions = 0

        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)

            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break

        if matches == 0:
            return 0.0

        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1

        # Calculate Jaro similarity
        jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3

        return jaro

    def _soundex(self, word: str) -> str:
        """Generate Soundex code for phonetic matching."""
        if not word:
            return "0000"

        word = word.upper()

        # Keep first letter
        soundex = word[0]

        # Soundex mapping
        mapping = {"BFPV": "1", "CGJKQSXZ": "2", "DT": "3", "L": "4", "MN": "5", "R": "6"}

        for char in word[1:]:
            for group, code in mapping.items():
                if char in group:
                    if soundex[-1] != code:  # Avoid consecutive duplicates
                        soundex += code
                    break

        # Remove vowels and H, W, Y
        soundex = soundex[0] + "".join([c for c in soundex[1:] if c.isdigit()])

        # Pad or truncate to 4 characters
        soundex = (soundex + "000")[:4]

        return soundex

    def _metaphone(self, word: str) -> str:
        """Generate Metaphone code for phonetic matching (simplified)."""
        if not word:
            return ""

        word = word.upper()
        metaphone = ""

        # Simple Metaphone rules (subset)
        i = 0
        while i < len(word):
            char = word[i]

            if char in "AEIOU":
                if i == 0:
                    metaphone += char
            elif char == "B":
                metaphone += "B"
            elif char == "C":
                if i + 1 < len(word) and word[i + 1] in "HI":
                    metaphone += "X"
                else:
                    metaphone += "K"
            elif char in "DT":
                metaphone += "T"
            elif char in "FV":
                metaphone += "F"
            elif char in "GH":
                metaphone += "G"
            elif char in "JY":
                metaphone += "J"
            elif char in "KQ":
                metaphone += "K"
            elif char == "L":
                metaphone += "L"
            elif char in "MN":
                metaphone += "M"
            elif char == "P":
                if i + 1 < len(word) and word[i + 1] == "H":
                    metaphone += "F"
                    i += 1
                else:
                    metaphone += "P"
            elif char == "R":
                metaphone += "R"
            elif char in "SZ":
                metaphone += "S"
            elif char == "W":
                if i + 1 < len(word) and word[i + 1] in "AEIOU":
                    metaphone += "W"
            elif char == "X":
                metaphone += "KS"

            i += 1

        return metaphone[:8]  # Limit length

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance with early termination."""
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

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity as 1 - (edit_distance / max_length)."""
        if not s1 and not s2:
            return 1.0

        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0

        distance = self._levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)
