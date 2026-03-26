"""Vocabulary processing utilities for corpus management.

Pure functions for normalization, lemmatization, and index building —
extracted from Corpus to separate data processing from the data model.
"""

from __future__ import annotations

from ..text.normalize import batch_lemmatize, batch_normalize
from ..utils.logging import get_logger
from .utils import get_vocabulary_hash

logger = get_logger(__name__)


def has_diacritics(word: str) -> bool:
    """Check if word contains non-ASCII characters (diacritics)."""
    return any(ord(c) > 127 for c in word)


def normalize_vocabulary(
    vocabulary: list[str],
) -> tuple[list[str], dict[str, int], dict[int, list[int]]]:
    """Normalize, sort, deduplicate a vocabulary and build index mappings.

    Args:
        vocabulary: Raw word list (may contain duplicates, diacritics, etc.)

    Returns:
        Tuple of:
          - unique_normalized: sorted deduplicated normalized vocabulary
          - vocabulary_to_index: normalized_word -> index mapping
          - normalized_to_original_indices: normalized_index -> [original_indices]
            (sorted with diacritics-preferred first)
    """
    normalized_vocabulary = batch_normalize(vocabulary)
    logger.info(f"Normalized to {len(normalized_vocabulary)} words")

    # Sort and deduplicate
    unique_normalized = sorted(set(normalized_vocabulary))
    logger.info(f"Final vocabulary: {len(unique_normalized)} unique normalized words")

    # Create vocabulary-to-index mapping
    vocabulary_to_index = {word: i for i, word in enumerate(unique_normalized)}

    # Build normalized -> original indices mapping
    normalized_to_original_indices: dict[int, list[int]] = {}
    for orig_idx, (orig_word, norm_word) in enumerate(
        zip(vocabulary, normalized_vocabulary, strict=False)
    ):
        if norm_word in vocabulary_to_index:
            sorted_idx = vocabulary_to_index[norm_word]
            if sorted_idx not in normalized_to_original_indices:
                normalized_to_original_indices[sorted_idx] = []
            normalized_to_original_indices[sorted_idx].append(orig_idx)

    # Sort each list: prefer words with diacritics, then by original index
    for _sorted_idx, orig_indices in normalized_to_original_indices.items():
        if len(orig_indices) > 1:
            orig_indices.sort(key=lambda idx: (not has_diacritics(vocabulary[idx]), idx))

    return unique_normalized, vocabulary_to_index, normalized_to_original_indices


def rebuild_original_indices(
    vocabulary: list[str],
    original_vocabulary: list[str],
    vocabulary_to_index: dict[str, int],
) -> dict[int, list[int]]:
    """Rebuild normalized_to_original_indices from vocabulary + original_vocabulary.

    Used during index rebuild when the corpus already has both vocabularies.
    """
    normalized_to_original_indices: dict[int, list[int]] = {}
    normalized_orig = batch_normalize(original_vocabulary)

    for orig_idx, norm_word in enumerate(normalized_orig):
        if norm_word in vocabulary_to_index:
            sorted_idx = vocabulary_to_index[norm_word]
            if sorted_idx not in normalized_to_original_indices:
                normalized_to_original_indices[sorted_idx] = []
            normalized_to_original_indices[sorted_idx].append(orig_idx)

    # Sort: diacritics-preferred first
    for _sorted_idx, orig_indices in normalized_to_original_indices.items():
        if len(orig_indices) > 1:
            orig_indices.sort(
                key=lambda idx: (not has_diacritics(original_vocabulary[idx]), idx)
            )

    return normalized_to_original_indices


def create_lemmatization_maps(
    vocabulary: list[str],
) -> tuple[list[str], dict[str, int], dict[int, int], dict[int, list[int]]]:
    """Create lemmatized vocabulary and all word<->lemma mappings.

    Args:
        vocabulary: Normalized, sorted vocabulary.

    Returns:
        Tuple of:
          - lemmatized_vocabulary: unique lemmas in first-seen order
          - lemma_text_to_index: lemma string -> lemma index
          - word_to_lemma_indices: word_index -> lemma_index
          - lemma_to_word_indices: lemma_index -> [word_indices]
    """
    lemmas, _, _ = batch_lemmatize(vocabulary)

    # Build unique lemma vocabulary (preserving first-seen order)
    unique_lemmas: list[str] = []
    seen_lemmas: set[str] = set()
    for lemma in lemmas:
        if lemma not in seen_lemmas:
            unique_lemmas.append(lemma)
            seen_lemmas.add(lemma)

    lemma_text_to_index = {lemma: i for i, lemma in enumerate(unique_lemmas)}

    word_to_lemma_indices: dict[int, int] = {}
    lemma_to_word_indices: dict[int, list[int]] = {}

    for word_idx, lemma in enumerate(lemmas):
        lemma_idx = lemma_text_to_index[lemma]
        word_to_lemma_indices[word_idx] = lemma_idx
        if lemma_idx not in lemma_to_word_indices:
            lemma_to_word_indices[lemma_idx] = []
        lemma_to_word_indices[lemma_idx].append(word_idx)

    logger.info(
        f"Created lemmatization maps: {len(unique_lemmas)} lemmas "
        f"from {len(vocabulary)} words",
    )

    return unique_lemmas, lemma_text_to_index, word_to_lemma_indices, lemma_to_word_indices


def merge_words(
    existing_vocabulary: list[str],
    new_words: list[str],
) -> tuple[list[str], list[str]]:
    """Normalize new words and merge with existing vocabulary.

    Returns:
        Tuple of (merged_sorted_vocabulary, normalized_new_words).
    """
    normalized_new = batch_normalize(new_words)
    merged = set(existing_vocabulary) | set(normalized_new)
    return sorted(merged), normalized_new


def filter_words(
    vocabulary: list[str],
    original_vocabulary: list[str],
    words_to_remove: list[str],
) -> tuple[list[str], list[str]]:
    """Remove words from both vocabularies.

    Returns:
        Tuple of (filtered_vocabulary, filtered_original_vocabulary).
    """
    normalized_remove = set(batch_normalize(words_to_remove))
    filtered_vocab = sorted([w for w in vocabulary if w not in normalized_remove])

    # Filter original vocabulary
    normalized_orig = batch_normalize(original_vocabulary)
    keep_indices = [
        i for i, norm_word in enumerate(normalized_orig) if norm_word not in normalized_remove
    ]
    filtered_original = [original_vocabulary[i] for i in keep_indices]

    return filtered_vocab, filtered_original
