"""Utility functions for wordlist operations."""

import hashlib

from ..utils.logging import get_logger
from ..utils.utils import generate_slug

logger = get_logger(__name__)


def generate_wordlist_hash(words: list[str]) -> str:
    """Generate content-based hash from word list.

    Args:
        words: List of word strings

    Returns:
        16-character hash string
    """
    # Sort words to ensure consistent hash regardless of order
    sorted_words = sorted(set(w.lower().strip() for w in words if w.strip()))
    content = "|".join(sorted_words)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def generate_wordlist_name(words: list[str]) -> str:
    """Generate a human-readable animal phrase name.

    Args:
        words: List of words (used for fallback hash)

    Returns:
        Generated name like 'myrtle-goldfish-swim' or fallback 'wordlist-{hash}'
    """
    # Use the unified slug generator from utils
    slug = generate_slug(3)  # 3 words: adjective-animal-verb

    # If slug generation somehow returns a UUID fallback, prepend 'wordlist-'
    if len(slug) == 8 and all(c in "0123456789abcdef-" for c in slug):
        # Looks like a UUID fragment, use hash-based name instead
        hash_id = generate_wordlist_hash(words)
        return f"wordlist-{hash_id}"

    return slug
