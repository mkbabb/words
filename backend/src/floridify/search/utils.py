"""
Search utility functions.

Helper functions for search operations including vocabulary hashing and scoring.
"""

from __future__ import annotations

import hashlib


def get_vocabulary_hash(
    vocabulary: list[str], max_length: int = 16, is_sorted: bool = False
) -> str:
    """
    Generate a stable hash for vocabulary content using deterministic sampling.

    Args:
        vocabulary: List of words to hash
        max_length: Maximum length of hash string to return
        is_sorted: If True, skip sorting step for performance (vocabulary must be pre-sorted)

    Returns:
        Truncated hash string for cache key
    """
    # Use pre-sorted vocabulary if available, otherwise sort
    if is_sorted:
        sorted_vocab = vocabulary
    else:
        sorted_vocab = sorted(vocabulary)

    # Use sample words + length for fast, stable hashing
    vocab_len = len(sorted_vocab)
    sample_size = min(20, vocab_len)

    if vocab_len > sample_size:
        # Take samples from beginning and end for better distribution
        half_sample = sample_size // 2
        sample_words = sorted_vocab[:half_sample] + sorted_vocab[-half_sample:]
    else:
        sample_words = sorted_vocab

    # Use join() directly to avoid f-string overhead for large samples
    content = str(vocab_len) + ":" + "|".join(sample_words)

    return hashlib.sha256(content.encode()).hexdigest()[:max_length]


def apply_length_correction(
    query: str, candidate: str, base_score: float
) -> float:
    """
    Apply length-aware correction to fuzzy search scores.
    
    Prevents short fragment bias and improves phrase matching.
    
    Args:
        query: Search query
        candidate: Candidate word being scored
        base_score: Raw fuzzy match score (0.0-1.0)
    
    Returns:
        Corrected score (0.0-1.0)
    """
    # No correction needed for perfect matches
    if base_score >= 0.99:
        return base_score

    # Pre-compute lengths and lowercase versions (minimize string operations)
    query_len = len(query)
    candidate_len = len(candidate)
    is_query_phrase = " " in query
    is_candidate_phrase = " " in candidate

    # Only compute lowercase versions when needed
    query_lower = query.lower()
    candidate_lower = candidate.lower()

    # Check if query is a prefix of the candidate (important for phrases)
    is_prefix_match = candidate_lower.startswith(query_lower)

    # Check if query matches the first word of a phrase exactly
    first_word_match = False
    if is_candidate_phrase and not is_query_phrase:
        # Find first space index instead of split() to avoid list allocation
        space_idx = candidate_lower.find(" ")
        if space_idx > 0:
            first_word_match = query_lower == candidate_lower[:space_idx]

    # Length ratio penalty for very different lengths
    min_len = min(query_len, candidate_len)
    max_len = max(query_len, candidate_len)
    length_ratio = min_len / max_len if max_len > 0 else 1.0

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