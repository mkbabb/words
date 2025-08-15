"""Utility functions for wordlist operations."""

import hashlib
import re

from ..utils.logging import get_logger

logger = get_logger(__name__)


def generate_slug(text: str) -> str:
    """Generate a URL-safe slug from text.

    Args:
        text: Text to convert to slug

    Returns:
        URL-safe slug

    """
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug


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
        Generated name like 'wordlist-{hash}'

    """
    # Generate a hash-based name
    hash_id = generate_wordlist_hash(words)
    return f"wordlist-{hash_id[:8]}"
