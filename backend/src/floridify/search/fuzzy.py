"""High-performance fuzzy search implementation.

Streamlined fuzzy search using TheFuzz backend with direct corpus vocabulary access.
"""

from __future__ import annotations

import random

from rapidfuzz import fuzz, process

from ..corpus.core import Corpus
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMethod
from .models import SearchResult
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

    def _get_frequency_weighted_sample(
        self,
        corpus: Corpus,
        sample_size: int = 1000,
    ) -> list[str]:
        """Get frequency-weighted sample from corpus vocabulary.

        For large corpora, samples words based on their frequency rather than
        taking the first N words. This ensures common words are more likely to
        be included in fuzzy search candidates.

        Args:
            corpus: Corpus to sample from
            sample_size: Number of words to sample

        Returns:
            List of sampled words

        """
        vocabulary = corpus.vocabulary

        # If corpus has frequency data, use weighted sampling
        if corpus.word_frequencies and len(corpus.word_frequencies) > 0:
            # Get frequencies for vocabulary words
            words_with_freq = []
            for word in vocabulary[
                : min(len(vocabulary), sample_size * 3)
            ]:  # Check 3x sample size for efficiency
                freq = corpus.word_frequencies.get(word, 1)  # Default freq=1 for unknown
                if freq > 0:  # Only include words with positive frequency
                    words_with_freq.append((word, freq))

            # If we got enough words with frequencies, do weighted sampling
            if len(words_with_freq) >= sample_size:
                words, freqs = zip(*words_with_freq)

                # Normalize frequencies to probabilities
                total_freq = sum(freqs)
                if total_freq > 0:
                    probabilities = [f / total_freq for f in freqs]

                    # Sample without replacement using frequency weights
                    try:
                        sampled_words = random.choices(
                            words, weights=probabilities, k=min(sample_size, len(words))
                        )
                        # Remove duplicates while preserving frequency bias
                        seen = set()
                        result = []
                        for word in sampled_words:
                            if word not in seen:
                                seen.add(word)
                                result.append(word)

                        logger.debug(
                            f"Frequency-weighted sampling: selected {len(result)} words "
                            f"from {len(words_with_freq)} candidates"
                        )
                        return result
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Weighted sampling failed: {e}, falling back to top-N")

        # Fallback: if no frequency data or sampling failed, use first N words
        logger.debug(f"Using first {sample_size} words (no frequency data available)")
        return vocabulary[:sample_size]

    def search(
        self,
        query: str,
        corpus: Corpus,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Robust fuzzy search with balanced performance and accuracy."""
        min_score_threshold = min_score if min_score is not None else self.min_score

        # Enhanced candidate selection for better recall
        max_candidates = max_results * 40

        # Try to get candidates with normalized query
        candidates = corpus.get_candidates(query.lower(), max_results=max_candidates)
        vocabulary = corpus.get_words_by_indices(candidates) if candidates else []

        # For multi-word queries, also get candidates for each word separately
        if not vocabulary and " " in query:
            all_candidates = set()
            for word in query.split():
                word_candidates = corpus.get_candidates(
                    word.lower(), max_results=max_candidates // 2
                )
                all_candidates.update(word_candidates)

            if all_candidates:
                vocabulary = corpus.get_words_by_indices(list(all_candidates))

        # If still no vocabulary, use a reasonable subset of the corpus
        if not vocabulary:
            # Fall back to full vocabulary for small corpora, or
            # frequency-weighted sampling for large corpora
            if len(corpus.vocabulary) <= 1000:
                vocabulary = corpus.vocabulary
            else:
                # Use frequency-weighted sampling for large corpora
                # This prioritizes common words over arbitrary first-N cutoff
                vocabulary = self._get_frequency_weighted_sample(corpus, sample_size=1000)

            if not vocabulary:
                return []

        # Multi-scorer approach for robustness
        matches = []
        seen_words = set()

        # Normalize query for consistent matching
        normalized_query = query.lower()

        # Primary scorer: WRatio for general accuracy
        # Lower cutoff for multi-word queries and improved limits for better quality
        primary_cutoff = (
            min_score_threshold * 45 if " " in query else min_score_threshold * 50
        )  # Further lowered for better typo tolerance
        # Increase limit multiplier to ensure we get enough high-quality candidates
        limit_multiplier = (
            5 if len(vocabulary) > 200 else 3
        )  # More candidates for large vocabularies
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
        if " " in query or len(query) >= 8:
            # Even lower cutoff for multi-word queries, aligned with primary scorer improvements
            secondary_cutoff = (
                min_score_threshold * 35
                if " " in query
                else min_score_threshold * 45  # Further lowered for better typo tolerance
            )
            secondary_results = process.extract(
                normalized_query,
                vocabulary,
                limit=max_results * limit_multiplier,  # Use same multiplier as primary
                scorer=fuzz.token_set_ratio,
                score_cutoff=secondary_cutoff,
            )

            for result in secondary_results:
                word, score, _ = result if len(result) == 3 else (result[0], result[1], 0)
                if word not in seen_words:
                    seen_words.add(word)
                    # Boost secondary scores slightly
                    boosted_score = min(1.0, (score / 100.0) * 1.2)
                    matches.append((word, boosted_score, "secondary"))

        # Convert to SearchResult objects with length correction
        final_matches = []
        for word, base_score, method in matches:
            # Simple length-based correction
            corrected_score = apply_length_correction(
                query,
                word,
                base_score,
                is_query_phrase=" " in query,
                is_candidate_phrase=" " in word,
            )

            if corrected_score >= min_score_threshold:
                # Get lemmatized word if available
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
