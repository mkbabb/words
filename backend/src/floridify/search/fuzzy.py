"""High-performance fuzzy search implementation.

Streamlined fuzzy search using RapidFuzz backend with direct corpus vocabulary access.
"""

from __future__ import annotations

from rapidfuzz import fuzz, process

from ..corpus.core import Corpus
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod
from .result import SearchResult
from .utils import apply_length_correction

logger = get_logger(__name__)


class FuzzySearch:
    """Streamlined fuzzy search using RapidFuzz backend.

    Optimized with candidate pre-selection for better performance.
    """

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE) -> None:
        """Initialize fuzzy search engine.

        Args:
            min_score: Minimum similarity score to include in results

        """
        self.min_score = min_score

    def _get_length_neighborhood(
        self,
        corpus: Corpus,
        query: str,
        sample_size: int = 1500,
    ) -> list[str]:
        """Get words of similar length to the query as fallback candidates.

        More targeted than random sampling: typos typically don't change word length
        by more than a few characters.

        Args:
            corpus: Corpus to sample from
            query: Query word to match length against
            sample_size: Maximum number of words to return

        Returns:
            List of words with similar length

        """
        query_len = len(query)
        result: list[str] = []

        # Search outward from exact length match
        for tolerance in range(5):
            for length in [query_len - tolerance, query_len + tolerance]:
                if length > 0 and length in corpus.length_buckets:
                    bucket = corpus.length_buckets[length]
                    words = corpus.get_words_by_indices(bucket)
                    result.extend(words)
                    if len(result) >= sample_size:
                        return result[:sample_size]

        return result[:sample_size]

    def search(
        self,
        query: str,
        corpus: Corpus,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Robust fuzzy search with balanced performance and accuracy."""
        min_score_threshold = min_score if min_score is not None else self.min_score

        # Bigram index provides high-quality candidates; use a large pool
        max_candidates = max(1500, max_results * 75)

        # Try to get candidates with normalized query
        candidates = corpus.get_candidates(query.lower(), max_results=max_candidates)
        vocabulary = corpus.get_words_by_indices(candidates) if candidates else []

        # For multi-word queries, also get candidates for each word separately
        if not vocabulary and " " in query:
            all_candidates: set[int] = set()
            for word in query.split():
                word_candidates = corpus.get_candidates(
                    word.lower(), max_results=max_candidates // 2
                )
                all_candidates.update(word_candidates)

            if all_candidates:
                vocabulary = corpus.get_words_by_indices(list(all_candidates))

        # Fallback: targeted length-neighborhood search instead of random sampling
        if not vocabulary:
            if len(corpus.vocabulary) <= 1000:
                vocabulary = corpus.vocabulary
            else:
                vocabulary = self._get_length_neighborhood(corpus, query, sample_size=500)

            if not vocabulary:
                return []

        # Multi-scorer approach for robustness
        matches: list[tuple[str, float, str]] = []
        seen_words: set[str] = set()

        # Normalize query for consistent matching
        normalized_query = query.lower()

        # Primary scorer: WRatio for general accuracy
        primary_cutoff = min_score_threshold * 45 if " " in query else min_score_threshold * 50
        limit_multiplier = 5 if len(vocabulary) > 200 else 3
        primary_results = process.extract(
            normalized_query,
            vocabulary,
            limit=max_results * limit_multiplier,
            scorer=fuzz.WRatio,
            score_cutoff=primary_cutoff,
        )

        # Add primary results
        for result in primary_results:
            word, score, _ = result if len(result) == 3 else (result[0], result[1], 0)
            if word not in seen_words:
                seen_words.add(word)
                matches.append((word, score / 100.0, "primary"))

        # Secondary scorer: Token set ratio for phrase matching
        # Short-circuit: skip secondary scorer if primary already has strong matches
        has_strong_primary = sum(1 for _, s, _ in matches[:3] if s > 0.85) >= 3
        if not has_strong_primary and (" " in query or len(query) >= 8):
            secondary_cutoff = (
                min_score_threshold * 35 if " " in query else min_score_threshold * 45
            )
            secondary_results = process.extract(
                normalized_query,
                vocabulary,
                limit=max_results * limit_multiplier,
                scorer=fuzz.token_set_ratio,
                score_cutoff=secondary_cutoff,
            )

            for result in secondary_results:
                word, score, _ = result if len(result) == 3 else (result[0], result[1], 0)
                if word not in seen_words:
                    seen_words.add(word)
                    boosted_score = min(1.0, (score / 100.0) * 1.2)
                    matches.append((word, boosted_score, "secondary"))

        # Convert to SearchResult objects with length correction
        final_matches = []
        for word, base_score, method in matches:
            corrected_score = apply_length_correction(
                query,
                word,
                base_score,
                is_query_phrase=" " in query,
                is_candidate_phrase=" " in word,
            )

            if corrected_score >= min_score_threshold:
                lemmatized_word = None
                if word in corpus.vocabulary_to_index:
                    word_idx = corpus.vocabulary_to_index[word]
                    if corpus.word_to_lemma_indices and word_idx in corpus.word_to_lemma_indices:
                        lemma_idx = corpus.word_to_lemma_indices[word_idx]
                        if lemma_idx < len(corpus.lemmatized_vocabulary):
                            lemmatized_word = corpus.lemmatized_vocabulary[lemma_idx]

                final_matches.append(
                    SearchResult(
                        word=word,
                        score=corrected_score,
                        method=SearchMethod.FUZZY,
                        lemmatized_word=lemmatized_word,
                        language=corpus.language,
                        metadata={"scoring_method": method} if method == "secondary" else None,
                    ),
                )

        final_matches.sort(key=lambda x: x.score, reverse=True)
        return final_matches[:max_results]
