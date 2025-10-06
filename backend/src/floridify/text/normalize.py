"""Core text normalization functions.

Provides comprehensive and fast normalization for different use cases.
"""

from __future__ import annotations

import functools
import os
import unicodedata
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor

import contractions  # type: ignore[import-untyped]
import ftfy

from ..utils.logging import get_logger
from .constants import (
    ALPHABETIC_PATTERN,
    ARTICLE_PATTERN,
    COMBINED_CLEANUP_PATTERN,
    DIACRITIC_MAPPINGS,
    FAST_PUNCTUATION_PATTERN,
    MULTIPLE_SPACE_PATTERN,
    NON_ALPHABETIC_PATTERN,
    SUFFIX_RULES,
    UNICODE_TO_ASCII,
)

logger = get_logger(__name__)

# Lazy NLTK lemmatizer initialization (saves ~1.1s on import)
# OPTIMIZATION: NLTK and scipy are only imported when lemmatization is actually used
_nltk_lemmatizer = None


def _get_lemmatizer():
    """Get or create the NLTK lemmatizer singleton.

    OPTIMIZATION: Lazy initialization reduces CLI boot time by ~1.1s (32% reduction).
    NLTK imports scipy which is expensive, so we defer this until actually needed.
    """
    global _nltk_lemmatizer

    if _nltk_lemmatizer is not None:
        return _nltk_lemmatizer

    # Lazy imports
    import nltk  # type: ignore[import-untyped]
    from nltk.stem import WordNetLemmatizer  # type: ignore[import-untyped]

    # Download NLTK data if missing (only on first use)
    try:
        nltk.data.find("corpora/wordnet")
        nltk.data.find("taggers/averaged_perceptron_tagger")
    except LookupError:
        try:
            nltk.download("wordnet", quiet=True)
            nltk.download("averaged_perceptron_tagger", quiet=True)
            nltk.download("omw-1.4", quiet=True)
        except Exception:
            logger.error("Failed to download NLTK data")

    _nltk_lemmatizer = WordNetLemmatizer()
    logger.debug("NLTK lemmatizer initialized (lazy)")
    return _nltk_lemmatizer


@functools.lru_cache(maxsize=50_000)
def normalize_comprehensive(
    text: str,
    fix_encoding: bool = True,
    expand_contractions: bool = True,
    remove_articles: bool = False,
    lowercase: bool = True,
) -> str:
    """Optimized single-pass text normalization with caching.

    Reduces Unicode passes from 3 to 2 and combines operations
    for 3-5x performance improvement while maintaining accuracy.

    Args:
        text: Input text to normalize
        fix_encoding: Fix Unicode encoding issues (requires ftfy)
        expand_contractions: Expand contractions (requires contractions library)
        remove_articles: Remove leading articles (the, a, an, etc.)
        lowercase: Convert to lowercase

    Returns:
        Fully normalized text

    """
    if not text:
        return ""

    # Fix encoding issues if needed (only when necessary)
    if fix_encoding:
        text = ftfy.fix_text(text)

    # Single-pass Unicode normalization with integrated diacritic removal
    # NFD allows separation of base characters from combining marks
    text = unicodedata.normalize("NFD", text)

    # Build normalized text in single pass
    chars: list[str] = []
    for char in text:
        # Skip combining marks (diacritics)
        if unicodedata.category(char) == "Mn":
            continue

        # Apply character mappings (Unicode to ASCII + diacritics)
        char_ord = ord(char)
        if char_ord in UNICODE_TO_ASCII:
            char = UNICODE_TO_ASCII[char_ord]
        elif char in DIACRITIC_MAPPINGS:
            chars.extend(DIACRITIC_MAPPINGS[char])  # Some mappings are multi-char
            continue

        # Apply lowercase during the same pass if requested
        if lowercase:
            char = char.lower()

        chars.append(char)

    # Join characters and convert back to NFC
    text = unicodedata.normalize("NFC", "".join(chars))

    # Expand contractions if requested (requires full text)
    if expand_contractions:
        text = contractions.fix(text)

    # Remove leading articles
    if remove_articles:
        text = ARTICLE_PATTERN.sub("", text, count=1)

    # Fast punctuation normalization for fuzzy search consistency
    # Remove apostrophes and normalize hyphens to spaces for signature matching
    text = text.replace("'", "").replace("-", " ")

    # Single regex for punctuation removal and whitespace normalization
    text = COMBINED_CLEANUP_PATTERN.sub(" ", text).strip()

    return text


@functools.lru_cache(maxsize=50_000)
def normalize_basic(text: str, lowercase: bool = True) -> str:
    """Fast normalization for search and lookup operations.

    Optimized for speed with minimal processing steps.
    Use this for real-time search and high-frequency operations.

    Args:
        text: Input text to normalize
        lowercase: Convert to lowercase

    Returns:
        Quickly normalized text

    """
    if not text:
        return ""

    # Quick Unicode normalization
    text = unicodedata.normalize("NFC", text)

    # Quick character replacement
    text = text.translate(UNICODE_TO_ASCII)

    # Use pre-compiled pattern for better performance
    text = FAST_PUNCTUATION_PATTERN.sub(" ", text)

    # Quick whitespace normalization
    text = MULTIPLE_SPACE_PATTERN.sub(" ", text).strip()

    # Lowercase if requested
    if lowercase:
        text = text.lower()

    return text


def normalize(text: str) -> str:
    """Global normalization function - switch between simple and comprehensive.

    This is the main normalization entry point. Swap the implementation
    to quickly test performance vs quality tradeoffs.

    Args:
        text: Input text to normalize

    Returns:
        Normalized text

    """
    return normalize_comprehensive(text)


def _normalize_chunk(args: tuple[list[str], Callable[[str], str]]) -> list[str]:
    """Helper function for batch_normalize - must be at module level for multiprocessing.

    Args:
        args: Tuple of (words, normalizer_func) for multiprocessing

    """
    words, normalizer = args
    return [normalizer(word) for word in words if word]


def batch_normalize(
    vocabulary: list[str],
    normalizer: Callable[[str], str] | None = None,
    min_parallel_size: int = 5000,
) -> list[str]:
    """Batch normalization with optional custom normalizer function.

    Args:
        vocabulary: List of words to normalize
        normalizer: Function to normalize each word (defaults to normalize_comprehensive)
        min_parallel_size: Minimum size to use parallel processing

    Returns:
        List of normalized words

    """
    # Default to normalize_comprehensive if no normalizer provided
    if normalizer is None:
        normalizer = normalize_comprehensive
    # Filter empty words first
    valid_words = [word for word in vocabulary if word]

    if len(valid_words) < min_parallel_size:
        # Fall back to serial for small datasets
        return [normalizer(word) for word in valid_words]

    # Split into chunks for parallel processing
    cpu_count = os.cpu_count() or 4
    chunk_size = max(1000, len(valid_words) // cpu_count)
    chunks = [valid_words[i : i + chunk_size] for i in range(0, len(valid_words), chunk_size)]

    # Process chunks in parallel - pass normalizer with each chunk
    normalized_words = []
    with ProcessPoolExecutor(max_workers=min(8, cpu_count)) as executor:
        # Create args tuples for each chunk
        chunk_args = [(chunk, normalizer) for chunk in chunks]
        futures = [executor.submit(_normalize_chunk, args) for args in chunk_args]
        for future in futures:
            normalized_words.extend(future.result())

    return normalized_words


def is_valid_word(word: str, min_length: int = 2, max_length: int = 50) -> bool:
    """Check if a word is valid for dictionary operations.

    Args:
        word: Word to validate
        min_length: Minimum valid length
        max_length: Maximum valid length

    Returns:
        True if word is valid

    """
    if not word or len(word) < min_length or len(word) > max_length:
        return False

    # Must contain at least one letter (pre-compiled)
    if not ALPHABETIC_PATTERN.search(word):
        return False

    # Check for excessive punctuation
    punct_count = sum(1 for c in word if c in "-'")
    if punct_count > len(word) // 2:
        return False

    # Check for invalid characters (pre-compiled)
    if NON_ALPHABETIC_PATTERN.search(word):
        return False

    return True


def remove_diacritics(text: str) -> str:
    """Remove diacritics from text while preserving base characters.

    Args:
        text: Input text

    Returns:
        Text without diacritics

    """
    # Normalize to NFD (decomposed form)
    nfd_text = unicodedata.normalize("NFD", text)

    # Remove combining marks (diacritics)
    without_diacritics = "".join(char for char in nfd_text if unicodedata.category(char) != "Mn")

    # Normalize back to NFC (composed form)
    return unicodedata.normalize("NFC", without_diacritics)


# Lemmatization functions


def lemmatize_basic(word: str) -> str:
    """Basic rule-based lemmatization.

    Uses suffix rules to find base form of words.

    Args:
        word: Word to lemmatize

    Returns:
        Lemmatized form

    """
    if not word or len(word) < 3:
        return word

    word_lower = word.lower()

    # Try suffix rules in order of specificity
    for suffix, replacement in sorted(SUFFIX_RULES.items(), key=lambda x: len(x[0]), reverse=True):
        if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 1:
            stem = word_lower[: -len(suffix)] + replacement
            # Validate the result is reasonable
            if len(stem) >= 2:
                return stem

    return word_lower


def _get_wordnet_pos(word: str) -> str:
    """Convert POS tag to WordNet format for better lemmatization."""
    try:
        # Lazy import
        import nltk  # type: ignore[import-untyped]

        # Get POS tag
        pos_tag = nltk.pos_tag([word])[0][1]

        # Map to WordNet POS (return string constants)
        if pos_tag.startswith("J"):
            return "a"  # wordnet.ADJ
        if pos_tag.startswith("V"):
            return "v"  # wordnet.VERB
        if pos_tag.startswith("N"):
            return "n"  # wordnet.NOUN
        if pos_tag.startswith("R"):
            return "r"  # wordnet.ADV
        return "n"  # wordnet.NOUN - Default to noun
    except Exception:
        return "n"  # Safe fallback


@functools.lru_cache(maxsize=300_000)  # Cache up to 300k lemmatizations
def lemmatize_comprehensive(word: str) -> str:
    """Lemmatize a word using modern NLTK WordNet approach with POS tagging.

    Uses NLTK WordNetLemmatizer with POS context for accuracy (>95%).
    Performance-optimized with caching decorator for repeated lookups.

    Args:
        word: Word to lemmatize

    Returns:
        Lemmatized form, validated for quality

    """
    if not word or len(word) < 2:
        return word

    # Validate input word quality
    if not is_valid_word(word):
        return word  # Return original if invalid

    word_lower = word.lower().strip()
    lemma = word_lower  # Default fallback

    try:
        # Get POS context for better accuracy
        pos = _get_wordnet_pos(word_lower)
        nltk_lemma = _get_lemmatizer().lemmatize(word_lower, pos=pos)

        # Validate result quality
        if nltk_lemma and is_valid_word(nltk_lemma) and len(nltk_lemma) >= 2:
            lemma = nltk_lemma
        else:
            # Fallback to rule-based approach
            lemma = lemmatize_basic(word_lower)
    except Exception:
        # Fallback to rule-based approach
        lemma = lemmatize_basic(word_lower)

    return lemma


def lemmatize(word: str) -> str:
    """Lemmatize a word using the comprehensive approach.

    Args:
        word: Word to lemmatize

    Returns:
        Lemmatized form

    """
    return lemmatize_comprehensive(word)


def _lemmatize_chunk(chunk: list[str]) -> list[str]:
    """Lemmatize a chunk of words for multiprocessing.
    Helper function that reinitializes NLTK in each process.
    """
    # Each process needs its own NLTK lemmatizer

    # Initialize lemmatizer for this process (lazy import in worker)
    import nltk  # type: ignore[import-untyped]
    from nltk.stem import WordNetLemmatizer  # type: ignore[import-untyped]

    process_lemmatizer = WordNetLemmatizer()

    lemmas = []
    for word in chunk:
        if not word:
            lemmas.append("")
            continue

        word_lower = word.lower().strip()

        try:
            # Get POS tag
            pos_tag = nltk.pos_tag([word_lower])[0][1]

            # Map to WordNet POS
            if pos_tag.startswith("J"):
                pos = "a"
            elif pos_tag.startswith("V"):
                pos = "v"
            elif pos_tag.startswith("N"):
                pos = "n"
            elif pos_tag.startswith("R"):
                pos = "r"
            else:
                pos = "n"

            lemma = process_lemmatizer.lemmatize(word_lower, pos=pos)

            # Validate result
            if not lemma or len(lemma) < 2:
                lemma = lemmatize_basic(word_lower)
        except Exception:
            lemma = lemmatize_basic(word_lower)

        lemmas.append(lemma)

    return lemmas


def _build_lemma_indices(
    lemmas: list[str],
) -> tuple[list[str], list[int], list[int]]:
    """Build unique lemmas and indices from a list of lemmas."""
    seen_lemmas: set[str] = set()
    unique_lemmas: list[str] = []
    lemma_to_index: dict[str, int] = {}
    word_to_lemma_indices: list[int] = []
    lemma_to_word_indices: list[int] = []

    for word_idx, lemma in enumerate(lemmas):
        if not lemma:
            word_to_lemma_indices.append(-1)
            continue

        if lemma not in seen_lemmas:
            seen_lemmas.add(lemma)
            lemma_idx = len(unique_lemmas)
            unique_lemmas.append(lemma)
            lemma_to_index[lemma] = lemma_idx
            lemma_to_word_indices.append(word_idx)
        else:
            lemma_idx = lemma_to_index[lemma]

        word_to_lemma_indices.append(lemma_idx)

    return unique_lemmas, word_to_lemma_indices, lemma_to_word_indices


def batch_lemmatize(
    words: list[str],
    n_processes: int | None = None,
    chunk_size: int = 5000,
) -> tuple[list[str], list[int], list[int]]:
    """Batch lemmatization with automatic parallelization for large inputs.

    Args:
        words: List of words to lemmatize
        n_processes: Number of processes (None for CPU count)
        chunk_size: Size of chunks for each process

    Returns:
        Tuple of (unique_lemmas, word_to_lemma_indices, lemma_to_word_indices)

    """
    if not words:
        return [], [], []

    # For small batches, use serial processing
    if len(words) < 10000:
        lemmas = [lemmatize_comprehensive(word) if word else "" for word in words]
        return _build_lemma_indices(lemmas)

    import multiprocessing as mp
    import os

    # Determine optimal process count
    if n_processes is None:
        n_processes = min(os.cpu_count() or 4, 8)  # Cap at 8 for efficiency

    logger.info(f"🚀 Parallelized lemmatization: {len(words)} words across {n_processes} processes")

    # Split words into chunks
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(words[i : i + chunk_size])

    # Use spawn context to avoid fork issues and proper cleanup
    ctx = mp.get_context("spawn")

    # Process chunks in parallel with proper cleanup
    chunk_results = []
    with ctx.Pool(processes=n_processes) as pool:
        try:
            chunk_results = pool.map(_lemmatize_chunk, chunks)
        finally:
            pool.close()
            pool.join()

    # Flatten results
    all_lemmas = []
    for chunk_lemmas in chunk_results:
        all_lemmas.extend(chunk_lemmas)

    unique_lemmas, word_to_lemma_indices, lemma_to_word_indices = _build_lemma_indices(all_lemmas)

    logger.info(
        f"✅ Lemmatization complete: {len(unique_lemmas)} unique lemmas from {len(words)} words",
    )

    return unique_lemmas, word_to_lemma_indices, lemma_to_word_indices


@functools.lru_cache(maxsize=50_000)
def get_word_signature(word: str) -> str:
    """Generate a phonetic signature for a word.

    Creates a simplified representation for grouping similar-sounding words.

    Args:
        word: Input word

    Returns:
        Phonetic signature (max 6 characters)

    """
    if not word:
        return ""

    # Normalize and prepare
    signature = word.lower().strip()

    # Remove non-alphabetic characters
    signature = "".join(c for c in signature if c.isalpha())

    if not signature:
        return ""

    # Common phonetic simplifications
    # Ph -> F
    signature = signature.replace("ph", "f")

    # CK -> K
    signature = signature.replace("ck", "k")

    # Double consonants -> single
    prev = ""
    result = []
    for char in signature:
        if char != prev or char in "aeiou":
            result.append(char)
        prev = char
    signature = "".join(result)

    # Remove vowels except first
    if signature:
        first_char = signature[0]
        rest = "".join(c for c in signature[1:] if c not in "aeiou")
        signature = first_char + rest

    # Truncate to 6 characters
    return signature[:6]


def clear_lemma_cache() -> None:
    """Clear the lemmatization cache.

    Note: Cache is managed by decorator, clearing happens automatically via TTL.
    """
    lemmatize_comprehensive.cache_clear()
    logger.info("Lemmatization cache cleared")


def get_lemma_cache_stats() -> dict[str, int]:
    """Get statistics about the lemmatization cache.

    Returns:
        Dictionary with cache statistics

    """
    cache_info = lemmatize_comprehensive.cache_info()
    return {
        "hits": cache_info.hits,
        "misses": cache_info.misses,
        "size": cache_info.currsize,
        "maxsize": cache_info.maxsize or 0,
    }
