"""Multi-strategy fuzzy search implementation.

Combines multiple candidate sources (BK-tree edit distance, phonetic matching,
trigram overlap, length neighborhood) into a unified pipeline. Each strategy
contributes candidates to a shared pool, which is then scored by RapidFuzz.

Signal-based boosting: candidates found by multiple strategies get boosted,
providing robust coverage for severely misspelled words.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from rapidfuzz import fuzz, process

from ...corpus.core import Corpus
from ...utils.logging import get_logger
from ..config import (
    BKTREE_MAX_CORPUS_SIZE,
    BKTREE_TIME_BUDGET_LARGE,
    BKTREE_TIME_BUDGET_MEDIUM,
    BKTREE_TIME_BUDGET_SMALL,
    PERWORD_MIN_WORD_LENGTH,
    PERWORD_SUFFIX_MIN_STEM_LENGTH,
    PERWORD_SUFFIX_TRIM_LENGTHS,
    CLOSE_EDIT_DISTANCE_BOOST,
    CORPUS_MEDIUM,
    CORPUS_SMALL,
    CORPUS_TINY,
    CORPUS_XLARGE,
    FUZZY_BUDGET_LARGE,
    FUZZY_BUDGET_MEDIUM,
    FUZZY_BUDGET_SMALL,
    FUZZY_BUDGET_XLARGE,
    MULTI_SIGNAL_BOOST,
    PHONETIC_BUDGET_CAP,
    PHONETIC_MATCH_BOOST,
    PRIMARY_PHRASE_CUTOFF_MULTIPLIER,
    PRIMARY_WORD_CUTOFF_MULTIPLIER,
    RAPIDFUZZ_LIMIT_MULTIPLIER_LARGE,
    RAPIDFUZZ_LIMIT_MULTIPLIER_SMALL,
    SECONDARY_PHRASE_CUTOFF_MULTIPLIER,
    SECONDARY_RESULT_BOOST,
    SECONDARY_WORD_CUTOFF_MULTIPLIER,
    STRONG_PRIMARY_COUNT,
    STRONG_PRIMARY_SCORE,
    VOCABULARY_SIZE_LIMIT_THRESHOLD,
)
from ..constants import DEFAULT_MIN_SCORE, SearchMethod
from ..phonetic.index import PhoneticIndex
from ..result import SearchResult
from .bk_tree import BKTree, cascading_search
from .scoring import apply_length_correction
from .suffix_array import SuffixArray

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def _get_candidate_budget(corpus_size: int) -> int:
    """Scale-aware candidate budget to avoid over/under-fetching.

    Small corpora don't need large budgets; large corpora need enough
    for recall without drowning RapidFuzz in candidates.
    """
    if corpus_size < CORPUS_TINY:
        return corpus_size  # Use full vocabulary
    elif corpus_size < CORPUS_SMALL:
        return FUZZY_BUDGET_SMALL
    elif corpus_size < CORPUS_MEDIUM:
        return FUZZY_BUDGET_MEDIUM
    elif corpus_size < CORPUS_XLARGE:
        return FUZZY_BUDGET_LARGE
    else:
        return FUZZY_BUDGET_XLARGE


class CandidateSignals(BaseModel):
    """Tracks which strategies found a candidate, for signal-based score boosting."""

    edit_distance: int | None = None
    phonetic_match: bool = False
    trigram_overlap: bool = False
    substring_match: bool = False


class FuzzySearch:
    """Multi-strategy fuzzy search with candidate aggregation.

    Combines BK-tree (adaptive edit distance), phonetic matching, and trigram
    overlap into a unified candidate pipeline. RapidFuzz scores the aggregated
    pool, with signal-based boosting for candidates found by multiple strategies.
    """

    def __init__(self, min_score: float = DEFAULT_MIN_SCORE) -> None:
        self.min_score = min_score

        # Strategy components (set externally by Search.initialize())
        self.bk_tree: BKTree | None = None
        self.phonetic_index: PhoneticIndex | None = None

    def _get_length_neighborhood(
        self,
        corpus: Corpus,
        query: str,
        sample_size: int = 1500,
    ) -> list[str]:
        """Get words of similar length to the query as fallback candidates."""
        query_len = len(query)
        result: list[str] = []

        for tolerance in range(5):
            for length in [query_len - tolerance, query_len + tolerance]:
                if length > 0 and length in corpus.length_buckets:
                    bucket = corpus.length_buckets[length]
                    words = corpus.get_words_by_indices(bucket)
                    result.extend(words)
                    if len(result) >= sample_size:
                        return result[:sample_size]

        return result[:sample_size]

    def _collect_candidates(
        self,
        query: str,
        corpus: Corpus,
        max_candidates: int,
        suffix_array: SuffixArray | None = None,
    ) -> dict[int, CandidateSignals]:
        """Aggregate candidates from all strategies into a unified pool.

        Each strategy contributes word indices with signal metadata.
        """
        candidates: dict[int, CandidateSignals] = {}
        normalized_query = query.lower()
        is_phrase = " " in query

        # Strategy 1: BK-tree (adaptive edit distance)
        # For corpora >100K the full-phrase BK-tree search is skipped (unbalanced
        # tree traversal can exceed the time budget). Per-word BK-tree searches
        # still run for phrases — individual words are short and cheap to search.
        corpus_size = len(corpus.vocabulary)
        bk_time_budget = BKTREE_TIME_BUDGET_LARGE  # default, overridden below
        if self.bk_tree and corpus_size < BKTREE_MAX_CORPUS_SIZE:
            if corpus_size < CORPUS_SMALL:
                bk_time_budget = BKTREE_TIME_BUDGET_SMALL
            elif corpus_size < CORPUS_MEDIUM:
                bk_time_budget = BKTREE_TIME_BUDGET_MEDIUM

            bk_results = cascading_search(
                self.bk_tree,
                normalized_query,
                min_candidates=10,
                time_budget_ms=bk_time_budget,
            )
            for word_idx, distance in bk_results[:max_candidates]:
                signals = candidates.setdefault(word_idx, CandidateSignals())
                signals.edit_distance = distance

        # Strategy 2: Phonetic matching (handles both single words and phrases)
        phonetic_budget = min(PHONETIC_BUDGET_CAP, max_candidates // 3)
        if self.phonetic_index:
            phonetic_results = self.phonetic_index.search(
                normalized_query, max_results=phonetic_budget
            )
            for word_idx in phonetic_results:
                signals = candidates.setdefault(word_idx, CandidateSignals())
                signals.phonetic_match = True

        # Strategy 3: Enhanced trigram overlap (with probabilistic masks)
        trigram_indices = corpus.get_candidates(
            normalized_query, max_results=max_candidates
        )
        for word_idx in trigram_indices:
            signals = candidates.setdefault(word_idx, CandidateSignals())
            signals.trigram_overlap = True

        # Strategy 4: Per-word suffix array search for phrases.
        # For multi-word queries, search each word and its trimmed stems
        # as substrings. The suffix array is the only per-word strategy —
        # BK-tree (40ms+) and trigram (1000ms+) are too expensive per-word
        # on large corpora. See config.py PERWORD_* for rationale.
        if is_phrase and suffix_array:
            words = [w for w in normalized_query.split() if len(w) >= PERWORD_MIN_WORD_LENGTH]
            per_word_budget = max_candidates // max(1, len(words) * 2)

            for word in words:
                if len(word) < PERWORD_SUFFIX_MIN_STEM_LENGTH:
                    continue
                for trim in PERWORD_SUFFIX_TRIM_LENGTHS:
                    stem = word[:len(word) - trim] if trim else word
                    if len(stem) < PERWORD_SUFFIX_MIN_STEM_LENGTH:
                        continue
                    sa_matches = suffix_array.search(stem, max_results=per_word_budget)
                    for word_idx, _coverage in sa_matches:
                        signals = candidates.setdefault(word_idx, CandidateSignals())
                        signals.substring_match = True

        return candidates

    def _score_with_signals(
        self,
        base_score: float,
        signals: CandidateSignals,
    ) -> float:
        """Apply signal-based score boosting.

        Candidates found by multiple strategies are almost certainly correct,
        so they get a modest boost. The boosts are multiplicative tiebreakers
        that never override a genuinely better base score.
        """
        score = base_score

        # Phonetic match: strong signal that the word "sounds right"
        if signals.phonetic_match:
            score = min(1.0, score * PHONETIC_MATCH_BOOST)

        # Very close edit distance: modest signal (avoid inflating scores
        # above what RapidFuzz alone would give, as this can create scale artifacts)
        if signals.edit_distance is not None and signals.edit_distance <= 1:
            score = min(1.0, score * CLOSE_EDIT_DISTANCE_BOOST)

        # Multi-signal bonus: found by 3+ strategies
        signal_count = sum([
            signals.edit_distance is not None,
            signals.phonetic_match,
            signals.trigram_overlap,
            signals.substring_match,
        ])
        if signal_count >= 3:
            score = min(1.0, score * MULTI_SIGNAL_BOOST)

        return score

    def search(
        self,
        query: str,
        corpus: Corpus,
        max_results: int = 20,
        min_score: float | None = None,
        suffix_array: SuffixArray | None = None,
    ) -> list[SearchResult]:
        """Multi-strategy fuzzy search with unified candidate aggregation."""
        min_score_threshold = min_score if min_score is not None else self.min_score

        # Scale-aware candidate budget
        max_candidates = _get_candidate_budget(len(corpus.vocabulary))

        # Phase 1: Collect candidates from all strategies
        candidate_signals = self._collect_candidates(
            query, corpus, max_candidates, suffix_array=suffix_array
        )

        # Phase 2: Resolve candidates to words for RapidFuzz scoring
        # Cap total pool to prevent RapidFuzz from being overwhelmed
        if candidate_signals:
            # Prioritize candidates with stronger signals (more strategies found them)
            def _signal_strength(idx: int) -> int:
                s = candidate_signals[idx]
                score = 0
                if s.edit_distance is not None:
                    score += 3 - min(3, s.edit_distance)  # Closer = higher
                if s.phonetic_match:
                    score += 2
                if s.trigram_overlap:
                    score += 1
                return score

            candidate_indices = sorted(
                candidate_signals.keys(),
                key=_signal_strength,
                reverse=True,
            )[:max_candidates]
            vocabulary = corpus.get_words_by_indices(candidate_indices)
            # Build index-to-word mapping for signal lookup
            idx_to_word: dict[str, int] = {}
            for i, word_idx in enumerate(candidate_indices):
                if i < len(vocabulary):
                    idx_to_word[vocabulary[i]] = word_idx
        else:
            vocabulary = []

        # Fallback: length-neighborhood if no strategies produced candidates
        if not vocabulary:
            if len(corpus.vocabulary) <= 1000:
                vocabulary = corpus.vocabulary
            else:
                vocabulary = self._get_length_neighborhood(corpus, query, sample_size=500)
            idx_to_word = {}  # No signal data for fallback candidates

            if not vocabulary:
                return []

        # Phase 3: RapidFuzz scoring on aggregated pool
        matches: list[tuple[str, float, str]] = []
        seen_words: set[str] = set()
        normalized_query = query.lower()
        is_phrase = " " in query

        # Primary scorer: WRatio
        primary_cutoff = min_score_threshold * PRIMARY_PHRASE_CUTOFF_MULTIPLIER if is_phrase else min_score_threshold * PRIMARY_WORD_CUTOFF_MULTIPLIER
        limit_multiplier = RAPIDFUZZ_LIMIT_MULTIPLIER_LARGE if len(vocabulary) > VOCABULARY_SIZE_LIMIT_THRESHOLD else RAPIDFUZZ_LIMIT_MULTIPLIER_SMALL
        primary_results = process.extract(
            normalized_query,
            vocabulary,
            limit=max_results * limit_multiplier,
            scorer=fuzz.WRatio,
            score_cutoff=primary_cutoff,
        )

        for result in primary_results:
            word, score, _ = result if len(result) == 3 else (result[0], result[1], 0)
            if word not in seen_words:
                seen_words.add(word)
                matches.append((word, score / 100.0, "primary"))

        # Secondary scorer: token_set_ratio for phrase matching
        # Skip for short single-word queries (token_set_ratio adds no value)
        has_strong_primary = sum(1 for _, s, _ in matches[:STRONG_PRIMARY_COUNT] if s > STRONG_PRIMARY_SCORE) >= STRONG_PRIMARY_COUNT
        has_any_results = any(s >= min_score_threshold for _, s, _ in matches)
        skip_secondary = has_strong_primary or (
            not is_phrase and (len(query) < 6 or has_any_results)
        )
        if not skip_secondary and (is_phrase or len(query) >= 8):
            secondary_cutoff = (
                min_score_threshold * SECONDARY_PHRASE_CUTOFF_MULTIPLIER if is_phrase else min_score_threshold * SECONDARY_WORD_CUTOFF_MULTIPLIER
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
                    boosted_score = min(1.0, (score / 100.0) * SECONDARY_RESULT_BOOST)
                    matches.append((word, boosted_score, "secondary"))

        # Phase 4: Convert to SearchResult with length correction + signal boost
        # Signal boost is applied AFTER length correction to prevent inflating
        # scores above what the corrected score warrants.
        final_matches = []
        for word, base_score, method in matches:
            corrected_score = apply_length_correction(
                query,
                word,
                base_score,
                is_query_phrase=is_phrase,
                is_candidate_phrase=" " in word,
            )

            # Apply signal-based boosting after length correction
            if word in idx_to_word:
                signals = candidate_signals.get(idx_to_word[word])
                if signals:
                    corrected_score = self._score_with_signals(corrected_score, signals)

            if corrected_score >= min_score_threshold:
                lemmatized_word = None
                if word in corpus.vocabulary_to_index:
                    word_idx = corpus.vocabulary_to_index[word]
                    if (
                        corpus.word_to_lemma_indices
                        and word_idx in corpus.word_to_lemma_indices
                    ):
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
                        metadata={"scoring_method": method}
                        if method == "secondary"
                        else None,
                    ),
                )

        final_matches.sort(key=lambda x: x.score, reverse=True)
        return final_matches[:max_results]
