"""Pure functions for candidate indexing and trigram-based fuzzy matching.

These functions operate on vocabulary data (lists, dicts) without requiring
access to the Corpus model instance, enabling reuse and easier testing.
"""

from __future__ import annotations

import numpy as np

from ..text.normalize import batch_normalize
from ..utils.logging import get_logger

logger = get_logger(__name__)


def word_trigrams(word: str) -> list[str]:
    """Extract character trigrams from a word with sentinel padding.

    Args:
        word: Input word

    Returns:
        List of character trigrams (e.g. "cat" -> ["##c", "#ca", "cat", "at#", "t##"])

    """
    padded = f"##{word}##"
    return [padded[i : i + 3] for i in range(len(padded) - 2)]


def build_candidate_index(
    vocabulary: list[str],
) -> tuple[dict[str, list[int]], dict[int, list[int]]]:
    """Build trigram inverted index and length buckets for candidate selection.

    Args:
        vocabulary: Sorted, normalized vocabulary list

    Returns:
        Tuple of (trigram_index, length_buckets) where:
        - trigram_index maps trigram strings to sorted lists of vocabulary indices
        - length_buckets maps word lengths to sorted lists of vocabulary indices

    """
    trigram_index: dict[str, list[int]] = {}
    length_buckets: dict[int, list[int]] = {}

    for idx, word in enumerate(vocabulary):
        # Trigram index
        for tg in word_trigrams(word):
            if tg not in trigram_index:
                trigram_index[tg] = []
            trigram_index[tg].append(idx)

        # Length bucket
        length = len(word)
        if length not in length_buckets:
            length_buckets[length] = []
        length_buckets[length].append(idx)

    # Sort buckets for consistent ordering
    for bucket in trigram_index.values():
        bucket.sort()
    for bucket in length_buckets.values():
        bucket.sort()

    logger.info(
        f"Built candidate index: {len(trigram_index)} trigrams, "
        f"{len(length_buckets)} length buckets",
    )

    return trigram_index, length_buckets


def get_candidates(
    query: str,
    vocabulary: list[str],
    vocabulary_to_index: dict[str, int],
    trigram_index: dict[str, list[int]],
    length_buckets: dict[int, list[int]],
    lemma_text_to_index: dict[str, int] | None = None,
    lemma_to_word_indices: dict[int, list[int]] | None = None,
    max_results: int = 50,
    use_lemmas: bool = True,
    use_trigrams: bool = True,
    length_tolerance: int = 2,
) -> list[int]:
    """Get candidate word indices for a query.

    Accumulates candidates from ALL four stages (direct, lemma, trigram,
    length buckets). High-priority candidates (stages 1-3) are always kept;
    length-bucket candidates fill remaining slots up to max_results.

    Args:
        query: Search query
        vocabulary: Sorted normalized vocabulary list
        vocabulary_to_index: Mapping from word to its index in vocabulary
        trigram_index: Trigram inverted index (from build_candidate_index)
        length_buckets: Length-based buckets (from build_candidate_index)
        lemma_text_to_index: Mapping from lemma text to lemma index
        lemma_to_word_indices: Mapping from lemma index to word indices
        max_results: Maximum number of results
        use_lemmas: Whether to include lemma matches
        use_trigrams: Whether to use trigram index matching
        length_tolerance: Length difference tolerance

    Returns:
        List of vocabulary indices

    """
    # Handle empty query
    if not query or not query.strip():
        return []

    normalized_queries = batch_normalize([query])
    if not normalized_queries:
        return []
    normalized_query = normalized_queries[0]

    # High-priority candidates: direct + lemma + trigram
    # These are always kept when truncating to max_results.
    priority: set[int] = set()

    # Stage 1: Direct lookup
    if normalized_query in vocabulary_to_index:
        priority.add(vocabulary_to_index[normalized_query])

    # Stage 2: Lemma-based lookup (O(1) via lemma_text_to_index)
    if use_lemmas and lemma_text_to_index:
        from ..text.normalize import batch_lemmatize

        query_lemmas, _, _ = batch_lemmatize([normalized_query])
        query_lemma: str = query_lemmas[0]

        lemma_idx = lemma_text_to_index.get(query_lemma)
        if lemma_idx is not None and lemma_to_word_indices:
            if word_indices := lemma_to_word_indices.get(lemma_idx):
                priority.update(word_indices)

    # Stage 3: Trigram overlap candidates
    if use_trigrams and trigram_index:
        query_trigrams = word_trigrams(normalized_query)
        vocab_size = len(vocabulary)

        # Collect all word indices that share any trigram with the query
        all_indices = []
        for tg in query_trigrams:
            if tg in trigram_index:
                all_indices.extend(trigram_index[tg])

        if all_indices:
            # Count shared trigrams per vocabulary word using numpy
            counts = np.bincount(all_indices, minlength=vocab_size)
            threshold = max(2, len(query_trigrams) // 3)
            # Get indices above threshold, sorted by overlap descending
            above = np.where(counts >= threshold)[0]
            if len(above) > 0:
                order = np.argsort(-counts[above])
                trigram_candidates = above[order][:max_results].tolist()
                priority.update(trigram_candidates)

    # Stage 4: Length-based candidates (ALWAYS runs -- critical for typo correction)
    # Each individual length bucket (len-1, len, len+1, len-2, len+2, ...) is
    # a separate stream. Round-robin interleaving ensures no single bucket
    # (e.g. exact-length with 9K+ entries at 278K) drowns out adjacent
    # buckets where the actual typo target lives.
    per_bucket_cap = max_results
    length_streams: list[list[int]] = []
    query_len = len(normalized_query)
    for length_diff in range(length_tolerance + 1):
        for length in [query_len - length_diff, query_len + length_diff]:
            if length > 0 and length in length_buckets:
                bucket = length_buckets[length]
                length_streams.append(bucket[:per_bucket_cap])

    # Merge: priority candidates first, then round-robin fill from length streams
    result = list(priority)[:max_results]
    if len(result) < max_results and length_streams:
        remaining = max_results - len(result)
        seen = set(result)
        # Round-robin: take one unseen candidate from each stream per round
        iterators = [iter(s) for s in length_streams]
        while remaining > 0 and iterators:
            exhausted = []
            for i, it in enumerate(iterators):
                for idx in it:
                    if idx not in seen:
                        result.append(idx)
                        seen.add(idx)
                        remaining -= 1
                        break
                else:
                    exhausted.append(i)
                if remaining <= 0:
                    break
            for i in reversed(exhausted):
                iterators.pop(i)

    return result
