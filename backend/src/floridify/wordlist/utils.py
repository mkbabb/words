"""Utility functions for wordlist operations."""

import hashlib

import coolname  # type: ignore[import-untyped]

from ..utils.logging import get_logger

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
    try:
        # Generate a cool name with adjective + animal + verb format
        name: str = coolname.generate_slug(3)  # 3 words: adjective-animal-verb
        logger.debug(f"Generated name: {name}")
        return name
    except Exception as e:
        logger.warning(f"Failed to generate cool name: {e}")
        # Fallback to hash-based name
        hash_id = generate_wordlist_hash(words)
        return f"wordlist-{hash_id}"