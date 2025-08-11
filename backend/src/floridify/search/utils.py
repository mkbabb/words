"""
Search utility functions.

Helper functions for search operations including vocabulary hashing and scoring.
"""

from __future__ import annotations

import hashlib


def get_vocabulary_hash(
    vocabulary: list[str],
    model_name: str | None = None,
    max_length: int = 16,
    is_sorted: bool = False,
) -> str:
    """
    Generate a stable hash for vocabulary content using deterministic sampling.

    Enhanced for BGE-M3 integration - includes model name to prevent cache collisions
    between different embedding models (all-MiniLM-L6-v2 vs BAAI/bge-m3).

    Args:
        vocabulary: List of words to hash
        model_name: Name of embedding model (for cache isolation)
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

    # Include model name in hash to prevent cache collisions between models
    model_prefix = f"{model_name}:" if model_name else ""
    content = model_prefix + str(vocab_len) + ":" + "|".join(sample_words)

    return hashlib.sha256(content.encode()).hexdigest()[:max_length]


def apply_length_correction(
    query: str,
    candidate: str,
    base_score: float,
    is_query_phrase: bool = False,
    is_candidate_phrase: bool = False,
) -> float:
    """
    Apply length-aware correction to fuzzy search scores.

    Prevents short fragment bias and improves phrase matching.

    Args:
        query: Search query
        candidate: Candidate word being scored
        base_score: Raw fuzzy match score (0.0-1.0)
        is_query_phrase: Whether query is a phrase (computed if None)
        is_candidate_phrase: Whether candidate is a phrase (computed if None)

    Returns:
        Corrected score (0.0-1.0)
    """
    # No correction needed for perfect matches
    if base_score >= 0.99:
        return base_score

    # Pre-compute lengths
    query_len = len(query)
    candidate_len = len(candidate)

    # Use provided phrase info or compute if not provided
    if is_query_phrase is None:
        is_query_phrase = " " in query
    if is_candidate_phrase is None:
        is_candidate_phrase = " " in candidate

    # Check if query is a prefix of the candidate (important for phrases)
    is_prefix_match = candidate.startswith(query)

    # Check if query matches the first word of a phrase exactly
    first_word_match = False
    if is_candidate_phrase and not is_query_phrase:
        # Find first space index instead of split() to avoid list allocation
        space_idx = candidate.find(" ")
        if space_idx > 0:
            first_word_match = query == candidate[:space_idx]

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
        base_score * length_ratio * phrase_penalty * short_penalty * prefix_bonus * first_word_bonus
    )

    # Ensure we don't exceed 1.0 or go below 0.0
    return max(0.0, min(1.0, corrected_score))


def calculate_default_frequency(word: str) -> int:
    """
    Calculate default frequency based on word characteristics.

    More robust heuristics:
    - Shorter words are typically more common
    - Common suffixes and prefixes get higher scores
    - Phrases get moderate scores based on word count
    - Very long words get lower scores

    Args:
        word: Word or phrase to calculate frequency for

    Returns:
        Estimated frequency score (higher = more common)
    """
    if not word:
        return 1

    base_score = 1000
    word_lower = word.lower()
    length = len(word_lower)

    # Length-based scoring (shorter = more common)
    if length <= 3:
        length_penalty = 0  # Very short words are often common
    elif length <= 5:
        length_penalty = 50
    elif length <= 8:
        length_penalty = 100
    elif length <= 12:
        length_penalty = 200
    else:
        length_penalty = 300 + (length - 12) * 10  # Progressive penalty for very long words

    # Phrase handling
    phrase_adjustment = 0
    if " " in word_lower:
        word_count = word_lower.count(" ") + 1
        if word_count == 2:
            phrase_adjustment = 150  # Two-word phrases are common
        elif word_count == 3:
            phrase_adjustment = 100  # Three-word phrases moderate
        else:
            phrase_adjustment = -50 * (word_count - 3)  # Longer phrases less common

    # Common suffix patterns (English-biased but generally applicable)
    suffix_bonus = 0
    common_suffixes = [
        ("ing", 150),
        ("ed", 140),
        ("er", 130),
        ("est", 120),
        ("ly", 110),
        ("tion", 100),
        ("able", 90),
        ("ness", 80),
        ("ment", 70),
        ("ful", 60),
        ("less", 50),
        ("ish", 40),
    ]
    for suffix, bonus in common_suffixes:
        if word_lower.endswith(suffix) and length > len(suffix):
            suffix_bonus = bonus
            break  # Take first matching suffix

    # Common prefix patterns
    prefix_bonus = 0
    common_prefixes = [
        ("un", 80),
        ("re", 70),
        ("pre", 60),
        ("dis", 50),
        ("over", 40),
        ("under", 30),
        ("out", 30),
        ("sub", 20),
    ]
    for prefix, bonus in common_prefixes:
        if word_lower.startswith(prefix) and length > len(prefix) + 2:
            prefix_bonus = bonus
            break  # Take first matching prefix

    # Vowel density (words with balanced vowel-consonant ratio are more common)
    vowel_count = sum(1 for c in word_lower if c in "aeiou")
    if length > 0:
        vowel_ratio = vowel_count / length
        if 0.35 <= vowel_ratio <= 0.45:  # Optimal vowel ratio
            vowel_bonus = 50
        elif 0.25 <= vowel_ratio <= 0.55:  # Acceptable ratio
            vowel_bonus = 20
        else:
            vowel_bonus = -20  # Too many or too few vowels
    else:
        vowel_bonus = 0

    # Calculate final score
    final_score = (
        base_score - length_penalty + phrase_adjustment + suffix_bonus + prefix_bonus + vowel_bonus
    )

    # Ensure minimum score of 1
    return max(1, final_score)
