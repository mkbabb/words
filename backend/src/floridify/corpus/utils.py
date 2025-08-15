"""Corpus utility functions.

Helper functions for corpus operations including vocabulary hashing.
"""

from __future__ import annotations

import hashlib


def get_vocabulary_hash(
    vocabulary: list[str],
    model_name: str | None = None,
    max_length: int = 16,
    is_sorted: bool = False,
) -> str:
    """Generate a stable hash for vocabulary content using deterministic sampling.

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
