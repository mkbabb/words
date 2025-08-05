"""
Search utilities - text processing and corpus management.

This module provides:
1. Text processing utilities (imported from unified text module)
2. Corpus management utilities (ID generation, naming, configuration)
"""

from __future__ import annotations

from typing import Any

# Import required types for corpus utilities
from ..models.definition import CorpusType, Language

# Import all search-related functions from the unified text module
from ..text import (
    clean_phrase,
    create_subword_text,
    generate_diacritic_variants,
    generate_word_variants,
    get_vocabulary_hash,
    is_phrase,
    normalize_for_search,
    normalize_lexicon_entry,
    normalize_word,
    remove_diacritics,
    split_word_into_subwords,
)

# Import constants for backwards compatibility
from ..text.constants import DIACRITIC_MAPPINGS
from ..utils.logging import get_logger
from ..utils.utils import generate_deterministic_id, generate_slug

logger = get_logger(__name__)


# ============================================================================
# CORPUS MANAGEMENT UTILITIES
# ============================================================================


def generate_corpus_id(
    corpus_type: CorpusType,
    languages: list[Language] | None = None,
    custom_id: str | None = None,
) -> str:
    """Generate deterministic corpus ID based on type and parameters.

    Rules:
    - language_search: Sorted languages joined with dash (e.g., 'de-en-fr')
    - wordlist: Provided custom_id or generated slug
    - wordlist_names: Static 'wordlist-names'
    - custom: Provided custom_id or generated slug

    Args:
        corpus_type: Type of corpus
        languages: List of languages (for language_search type)
        custom_id: Custom ID to use (optional)

    Returns:
        Deterministic corpus ID string

    Examples:
        >>> generate_corpus_id(CorpusType.LANGUAGE_SEARCH, [Language.ENGLISH, Language.FRENCH])
        'en-fr'
        >>> generate_corpus_id(CorpusType.WORDLIST, custom_id='my-words')
        'my-words'
        >>> generate_corpus_id(CorpusType.WORDLIST_NAMES)
        'wordlist-names'
    """
    if corpus_type == CorpusType.LANGUAGE_SEARCH:
        if not languages:
            raise ValueError("Languages required for language_search corpus type")
        # Use deterministic ID generator to sort languages
        language_codes = [lang.value for lang in languages]
        return generate_deterministic_id(*language_codes)

    elif corpus_type == CorpusType.WORDLIST_NAMES:
        # Static ID for wordlist names corpus
        return "wordlist-names"

    elif custom_id:
        # Use provided custom ID
        return custom_id

    else:
        # Generate slug for wordlists and custom corpora
        return generate_slug()


def get_corpus_name(corpus_type: CorpusType, corpus_id: str) -> str:
    """Generate consistent corpus name for MongoDB storage.

    Creates a namespaced corpus name by combining type and ID.

    Args:
        corpus_type: Type of corpus
        corpus_id: Corpus identifier

    Returns:
        Formatted corpus name for storage

    Examples:
        >>> get_corpus_name(CorpusType.LANGUAGE_SEARCH, 'en-fr')
        'language_search_en-fr'
        >>> get_corpus_name(CorpusType.WORDLIST, 'my-words')
        'wordlist_my-words'
    """
    return f"{corpus_type.value}_{corpus_id}"


def parse_corpus_name(corpus_name: str) -> tuple[CorpusType | None, str]:
    """Parse corpus name back into type and ID.

    Args:
        corpus_name: Full corpus name from storage

    Returns:
        Tuple of (corpus_type, corpus_id) or (None, corpus_name) if not parseable

    Examples:
        >>> parse_corpus_name('language_search_en-fr')
        (CorpusType.LANGUAGE_SEARCH, 'en-fr')
        >>> parse_corpus_name('wordlist_my-words')
        (CorpusType.WORDLIST, 'my-words')
    """
    # Try to match corpus type prefixes
    for corpus_type in CorpusType:
        prefix = f"{corpus_type.value}_"
        if corpus_name.startswith(prefix):
            corpus_id = corpus_name[len(prefix) :]
            return corpus_type, corpus_id

    # Not a recognized corpus name format
    return None, corpus_name


def get_semantic_config(vocabulary_size: int) -> dict[str, Any]:
    """Get recommended semantic search configuration based on vocabulary size.

    Implements smart defaults:
    - Small corpora (<10k): Enable semantic with binary quantization
    - Medium corpora (10k-100k): Optional semantic with scalar quantization
    - Large corpora (>100k): Disable semantic by default

    Args:
        vocabulary_size: Number of words in vocabulary

    Returns:
        Configuration dictionary with semantic settings
    """
    if vocabulary_size < 10_000:
        return {
            "enable_semantic": True,
            "quantization_type": "binary",
            "auto_enable": True,
            "reason": "Small corpus - semantic search recommended",
        }
    elif vocabulary_size < 100_000:
        return {
            "enable_semantic": False,
            "quantization_type": "scalar",
            "auto_enable": False,
            "reason": "Medium corpus - semantic search optional",
        }
    else:
        return {
            "enable_semantic": False,
            "quantization_type": "none",
            "auto_enable": False,
            "reason": "Large corpus - semantic search not recommended",
        }


def normalize_corpus_id(corpus_id: str) -> str:
    """Normalize corpus ID for consistent storage.

    Ensures corpus IDs are lowercase and use hyphens.

    Args:
        corpus_id: Raw corpus ID

    Returns:
        Normalized corpus ID

    Examples:
        >>> normalize_corpus_id('My_Words')
        'my-words'
        >>> normalize_corpus_id('EN FR')
        'en-fr'
    """
    # Convert to lowercase and replace spaces/underscores with hyphens
    normalized = corpus_id.lower().strip()
    normalized = normalized.replace("_", "-").replace(" ", "-")
    # Remove multiple consecutive hyphens
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    # Remove leading/trailing hyphens
    normalized = normalized.strip("-")
    return normalized


# ============================================================================
# EXPORTS
# ============================================================================


__all__ = [
    # Text processing (backwards compatibility)
    "generate_word_variants",
    "is_phrase",
    "clean_phrase",
    "remove_diacritics",
    "normalize_for_search",
    "generate_diacritic_variants",
    "normalize_lexicon_entry",
    "create_subword_text",
    "split_word_into_subwords",
    "get_vocabulary_hash",
    "normalize_word",
    "DIACRITIC_MAPPINGS",
    # Corpus management (new)
    "generate_corpus_id",
    "get_corpus_name",
    "parse_corpus_name",
    "get_semantic_config",
    "normalize_corpus_id",
]
