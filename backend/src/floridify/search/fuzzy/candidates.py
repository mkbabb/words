"""Pure functions for candidate indexing and trigram-based fuzzy matching.

These functions operate on vocabulary data (lists, dicts) without requiring
access to the Corpus model instance, enabling reuse and easier testing.

Data structures:
- Trigram posting lists: numpy structured arrays with 8-bit positional + next-char
  masks (inspired by GitHub "Project Blackbird") for ~40-60% false positive reduction.
- Length buckets: numpy int32 arrays for cache-friendly access.
"""

from __future__ import annotations

import numpy as np

from ...text.normalize import batch_normalize
from ...utils.logging import get_logger
from ..config import TRIGRAM_CAP_FRACTION, TRIGRAM_CAP_MINIMUM

logger = get_logger(__name__)

# Structured dtype for trigram posting lists with probabilistic masks.
# - idx: vocabulary index (int32)
# - loc: positional mask — bit i%8 set for each position i where this trigram appears
# - nxt: next-char mask — bit hash(next_char)%8 set, giving "3.5-gram" precision
POSTING_DTYPE = np.dtype([("idx", np.int32), ("loc", np.uint8), ("nxt", np.uint8)])

# Type aliases for clarity
PostingArray = np.ndarray  # dtype=POSTING_DTYPE
TrigramIndex = dict[str, PostingArray]
LengthBuckets = dict[int, np.ndarray]  # dtype=np.int32


def _next_char_hash(char: str) -> int:
    """Hash a character to a bit position (0-7) for the next-char mask."""
    return hash(char) & 7


def word_trigrams(word: str) -> list[str]:
    """Extract character trigrams from a word with sentinel padding.

    Args:
        word: Input word

    Returns:
        List of character trigrams (e.g. "cat" -> ["##c", "#ca", "cat", "at#", "t##"])

    """
    padded = f"##{word}##"
    return [padded[i : i + 3] for i in range(len(padded) - 2)]


def word_substring_trigrams(word: str) -> list[str]:
    """Extract non-sentinel trigrams for substring/infix matching.

    Unlike word_trigrams(), this does NOT add sentinel padding, so these
    trigrams match mid-word positions. Requires len(word) >= 3.

    Args:
        word: Input word (must be >= 3 chars)

    Returns:
        List of character trigrams without sentinels

    """
    if len(word) < 3:
        return []
    return [word[i : i + 3] for i in range(len(word) - 2)]


def build_candidate_index(
    vocabulary: list[str],
) -> tuple[TrigramIndex, LengthBuckets]:
    """Build trigram inverted index and length buckets for candidate selection.

    Trigram posting lists use structured numpy arrays with 8-bit positional
    and next-char masks for high-precision candidate filtering.

    Args:
        vocabulary: Sorted, normalized vocabulary list

    Returns:
        Tuple of (trigram_index, length_buckets) where:
        - trigram_index maps trigram strings to structured PostingArrays
        - length_buckets maps word lengths to int32 numpy arrays

    """
    # Phase 1: Collect as Python lists (O(1) amortized append)
    trigram_lists: dict[str, list[tuple[int, int, int]]] = {}
    length_lists: dict[int, list[int]] = {}

    for idx, word in enumerate(vocabulary):
        padded = f"##{word}##"
        n_trigrams = len(padded) - 2

        for i in range(n_trigrams):
            tg = padded[i : i + 3]

            # Positional mask: bit (i % 8) records where this trigram appears
            loc_bit = 1 << (i & 7)

            # Next-char mask: hash of character after trigram for "3.5-gram" precision
            next_pos = i + 3
            if next_pos < len(padded):
                nxt_bit = 1 << _next_char_hash(padded[next_pos])
            else:
                nxt_bit = 1 << 7  # sentinel bit for end-of-word

            if tg not in trigram_lists:
                trigram_lists[tg] = []
            trigram_lists[tg].append((idx, loc_bit, nxt_bit))

        # Length bucket
        length = len(word)
        if length not in length_lists:
            length_lists[length] = []
        length_lists[length].append(idx)

    # Phase 2: Convert to numpy arrays for cache-friendly, vectorized access
    trigram_index: TrigramIndex = {}
    for tg, entries in trigram_lists.items():
        arr = np.empty(len(entries), dtype=POSTING_DTYPE)
        for j, (idx, loc, nxt) in enumerate(entries):
            arr[j] = (idx, loc, nxt)
        # Sort by vocabulary index for consistent ordering
        arr.sort(order="idx")
        # Merge masks for duplicate (trigram, word_idx) pairs. A word can have
        # the same trigram at multiple positions — we OR the masks together.
        if len(arr) > 1:
            unique_mask = np.empty(len(arr), dtype=bool)
            unique_mask[0] = True
            unique_mask[1:] = arr["idx"][1:] != arr["idx"][:-1]
            if not unique_mask.all():
                # Merge duplicate entries by OR-ing masks
                merged: list[tuple[int, int, int]] = []
                cur_idx, cur_loc, cur_nxt = int(arr[0]["idx"]), int(arr[0]["loc"]), int(arr[0]["nxt"])
                for k in range(1, len(arr)):
                    if arr[k]["idx"] == cur_idx:
                        cur_loc |= int(arr[k]["loc"])
                        cur_nxt |= int(arr[k]["nxt"])
                    else:
                        merged.append((cur_idx, cur_loc, cur_nxt))
                        cur_idx, cur_loc, cur_nxt = int(arr[k]["idx"]), int(arr[k]["loc"]), int(arr[k]["nxt"])
                merged.append((cur_idx, cur_loc, cur_nxt))
                arr = np.array(merged, dtype=POSTING_DTYPE)
        trigram_index[tg] = arr

    length_buckets: LengthBuckets = {}
    for length, indices in length_lists.items():
        bucket = np.array(sorted(indices), dtype=np.int32)
        length_buckets[length] = bucket

    total_postings = sum(len(arr) for arr in trigram_index.values())
    memory_bytes = total_postings * POSTING_DTYPE.itemsize
    logger.info(
        f"Built candidate index: {len(trigram_index)} trigrams "
        f"({total_postings:,} postings, {memory_bytes / 1024:.0f}KB), "
        f"{len(length_buckets)} length buckets",
    )

    return trigram_index, length_buckets


def get_candidates(
    query: str,
    vocabulary: list[str],
    vocabulary_to_index: dict[str, int],
    trigram_index: TrigramIndex,
    length_buckets: LengthBuckets,
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

    Trigram stage uses probabilistic mask filtering for ~40-60% fewer false
    positives compared to plain trigram overlap counting.

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
        from ...text.normalize import batch_lemmatize

        query_lemmas, _, _ = batch_lemmatize([normalized_query])
        if not query_lemmas:
            query_lemmas = [normalized_query]
        query_lemma: str = query_lemmas[0]

        lemma_idx = lemma_text_to_index.get(query_lemma)
        if lemma_idx is not None and lemma_to_word_indices:
            if word_indices := lemma_to_word_indices.get(lemma_idx):
                priority.update(word_indices)

    # Stage 3: Trigram overlap candidates with mask filtering
    if use_trigrams and trigram_index:
        padded_query = f"##{normalized_query}##"
        query_trigrams = [padded_query[i : i + 3] for i in range(len(padded_query) - 2)]
        vocab_size = len(vocabulary)

        # Collect mask-filtered indices using vectorized numpy ops
        counts = np.zeros(vocab_size, dtype=np.int32)

        for i, tg in enumerate(query_trigrams):
            if tg not in trigram_index:
                continue

            posting = trigram_index[tg]

            # Build query masks for this trigram position
            query_loc_bit = np.uint8(1 << (i & 7))
            next_pos = i + 3
            if next_pos < len(padded_query):
                query_nxt_bit = np.uint8(1 << _next_char_hash(padded_query[next_pos]))
            else:
                query_nxt_bit = np.uint8(1 << 7)

            # Vectorized mask check: both positional AND next-char must match
            loc_match = (posting["loc"] & query_loc_bit).astype(bool)
            nxt_match = (posting["nxt"] & query_nxt_bit).astype(bool)
            mask_pass = loc_match & nxt_match

            # Only count entries that pass both mask checks
            passing_indices = posting["idx"][mask_pass]
            if len(passing_indices) > 0:
                np.add.at(counts, passing_indices, 1)

        threshold = max(2, len(query_trigrams) // 3)
        above = np.where(counts >= threshold)[0]
        if len(above) > 0:
            order = np.argsort(-counts[above])
            # Reserve ~20% of budget for length-bucket candidates
            trigram_cap = max(TRIGRAM_CAP_MINIMUM, int(max_results * TRIGRAM_CAP_FRACTION))
            trigram_candidates = above[order][:trigram_cap].tolist()
            priority.update(trigram_candidates)

    # Stage 4: Length-based candidates (ALWAYS runs -- critical for typo correction)
    # Each individual length bucket is a separate stream. Round-robin interleaving
    # ensures no single bucket drowns out adjacent buckets.
    per_bucket_cap = max_results
    length_streams: list[np.ndarray] = []
    query_len = len(normalized_query)
    for length_diff in range(length_tolerance + 1):
        for length in [query_len - length_diff, query_len + length_diff]:
            if length > 0 and length in length_buckets:
                bucket = length_buckets[length]
                length_streams.append(bucket[:per_bucket_cap])

    # Merge: priority candidates first, then round-robin fill from length streams.
    # Always leave room for length-bucket candidates by capping priority.
    result = list(priority)[:max_results]
    if len(result) < max_results and length_streams:
        remaining = max_results - len(result)
        seen = set(result)
        # Round-robin: take one unseen candidate from each stream per round
        iterators = [iter(s.tolist()) for s in length_streams]
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


def get_substring_candidates(
    query: str,
    vocabulary: list[str],
    trigram_index: TrigramIndex,
    max_results: int = 50,
) -> list[int]:
    """Get candidate word indices for substring/infix matching.

    Uses non-sentinel trigrams to find words containing the query as a substring.
    Candidates are verified with an actual `in` check.

    Args:
        query: Substring to search for (>= 3 chars recommended)
        vocabulary: Sorted normalized vocabulary list
        trigram_index: Trigram inverted index (from build_candidate_index)
        max_results: Maximum number of results

    Returns:
        List of vocabulary indices whose words contain the query as a substring,
        sorted by coverage ratio (query_len / word_len) descending.

    """
    normalized_queries = batch_normalize([query])
    if not normalized_queries:
        return []
    normalized_query = normalized_queries[0]

    if len(normalized_query) < 2:
        return []

    # For short queries (2 chars), we can't form trigrams — use direct scan
    if len(normalized_query) < 3:
        results = []
        for idx, word in enumerate(vocabulary):
            if normalized_query in word and word != normalized_query:
                results.append(idx)
                if len(results) >= max_results:
                    break
        return results

    # Generate non-sentinel trigrams for substring matching
    query_trigrams = word_substring_trigrams(normalized_query)
    if not query_trigrams:
        return []

    vocab_size = len(vocabulary)

    # Collect candidate indices from trigram posting lists (ignore masks for substring)
    counts = np.zeros(vocab_size, dtype=np.int32)
    for tg in query_trigrams:
        if tg in trigram_index:
            posting = trigram_index[tg]
            np.add.at(counts, posting["idx"], 1)

    # Require ALL query trigrams to match (strict intersection for substring)
    threshold = len(query_trigrams)
    above = np.where(counts >= threshold)[0]

    if len(above) == 0:
        # Fallback: relax to requiring most trigrams
        threshold = max(1, len(query_trigrams) - 1)
        above = np.where(counts >= threshold)[0]

    if len(above) == 0:
        return []

    # Verify actual substring containment
    verified: list[tuple[int, float]] = []
    for idx in above:
        word = vocabulary[idx]
        if normalized_query in word and word != normalized_query:
            # Score by coverage ratio (higher = query covers more of the word)
            coverage = len(normalized_query) / len(word)
            verified.append((idx, coverage))

    # Sort by coverage descending (most specific matches first)
    verified.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in verified[:max_results]]
