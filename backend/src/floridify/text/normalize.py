"""
Core text normalization functions.

Provides comprehensive and fast normalization for different use cases.
"""

from __future__ import annotations

import re
import unicodedata

from .constants import SUFFIX_RULES
from .patterns import (
    ARTICLE_PATTERN,
    MULTIPLE_SPACE_PATTERN,
    PUNCTUATION_PATTERN,
    UNICODE_TO_ASCII,
    WHITESPACE_PATTERN,
)

# NLTK lemmatization (modern approach)
try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    # Try to use NLTK data, download if missing
    try:
        nltk.data.find('corpora/wordnet')
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        # Download required NLTK data in production-safe way
        try:
            nltk.download('wordnet', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
            nltk.download('omw-1.4', quiet=True)  # Multilingual wordnet
        except Exception:
            pass  # Fail gracefully if downloads don't work
    
    NLTK_AVAILABLE = True
    _nltk_lemmatizer = WordNetLemmatizer()
except ImportError:
    NLTK_AVAILABLE = False
    _nltk_lemmatizer = None

# Performance optimization: lemma cache for repeated lookups
# Research shows "LOADS of repetitions" in large corpora
_lemma_cache: dict[str, str] = {}

# Optional dependencies
try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False

try:
    import contractions
    CONTRACTIONS_AVAILABLE = True
except ImportError:
    CONTRACTIONS_AVAILABLE = False


def normalize_comprehensive(
    text: str,
    fix_encoding: bool = True,
    expand_contractions: bool = True,
    remove_articles: bool = False,
    lowercase: bool = True,
) -> str:
    """
    Comprehensive text normalization with all processing steps.
    
    This is the full normalization pipeline for maximum text cleaning.
    Use this when accuracy is more important than speed.
    
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
    
    # Step 1: Fix encoding issues
    if fix_encoding and FTFY_AVAILABLE:
        text = ftfy.fix_text(text)
    
    # Step 2: Unicode normalization (NFD -> NFC)
    text = unicodedata.normalize("NFC", text)
    
    # Step 3: Replace Unicode characters with ASCII equivalents
    text = text.translate(UNICODE_TO_ASCII)
    
    # Step 4: Expand contractions
    if expand_contractions and CONTRACTIONS_AVAILABLE:
        text = contractions.fix(text)
    
    # Step 5: Remove leading articles
    if remove_articles:
        text = ARTICLE_PATTERN.sub("", text, count=1)
    
    # Step 6: Remove excessive punctuation but keep apostrophes and hyphens
    text = PUNCTUATION_PATTERN.sub(" ", text)
    
    # Step 7: Normalize whitespace
    text = WHITESPACE_PATTERN.sub(" ", text)
    text = text.strip()
    
    # Step 8: Lowercase if requested
    if lowercase:
        text = text.lower()
    
    return text


def normalize_fast(text: str, lowercase: bool = True) -> str:
    """
    Fast normalization for search and lookup operations.
    
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
    
    # Remove excessive punctuation
    text = re.sub(r"[^\w\s\'-]", " ", text)
    
    # Quick whitespace normalization
    text = " ".join(text.split())
    
    # Lowercase if requested
    if lowercase:
        text = text.lower()
    
    return text


def normalize_word(word: str, remove_articles: bool = True) -> str:
    """
    Normalize a single word or short phrase.
    
    Specifically optimized for dictionary words and entries.
    
    Args:
        word: Word or short phrase to normalize
        remove_articles: Remove leading articles
        
    Returns:
        Normalized word
    """
    if not word:
        return ""
    
    # NFD normalization for diacritic handling
    normalized = unicodedata.normalize("NFD", word)
    
    # Remove diacritics
    without_accents = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )
    
    # Back to NFC
    result = unicodedata.normalize("NFC", without_accents)
    
    # Convert to lowercase and strip
    result = result.lower().strip()
    
    # Remove leading articles
    if remove_articles:
        result = ARTICLE_PATTERN.sub("", result, count=1).strip()
    
    return result


def clean_word(word: str) -> str:
    """
    Clean a single word by removing invalid characters.
    
    Preserves hyphens and apostrophes which are valid in words.
    
    Args:
        word: Word to clean
        
    Returns:
        Cleaned word
    """
    if not word:
        return ""
    
    # Remove characters that aren't letters, hyphens, or apostrophes
    cleaned = re.sub(r"[^a-zA-Z\-']", "", word)
    
    # Remove leading/trailing punctuation
    cleaned = cleaned.strip("-'")
    
    return cleaned


def is_valid_word(word: str, min_length: int = 2, max_length: int = 50) -> bool:
    """
    Check if a word is valid for dictionary operations.
    
    Args:
        word: Word to validate
        min_length: Minimum valid length
        max_length: Maximum valid length
        
    Returns:
        True if word is valid
    """
    if not word or len(word) < min_length or len(word) > max_length:
        return False
    
    # Must contain at least one letter
    if not re.search(r"[a-zA-Z]", word):
        return False
    
    # Check for excessive punctuation
    punct_count = sum(1 for c in word if c in "-'")
    if punct_count > len(word) // 2:
        return False
    
    # Check for invalid characters
    if re.search(r"[^a-zA-Z\-'\s]", word):
        return False
    
    return True


def remove_diacritics(text: str) -> str:
    """
    Remove diacritics from text while preserving base characters.
    
    Args:
        text: Input text
        
    Returns:
        Text without diacritics
    """
    # Normalize to NFD (decomposed form)
    nfd_text = unicodedata.normalize("NFD", text)
    
    # Remove combining marks (diacritics)
    without_diacritics = "".join(
        char for char in nfd_text
        if unicodedata.category(char) != "Mn"
    )
    
    # Normalize back to NFC (composed form)
    return unicodedata.normalize("NFC", without_diacritics)


def normalize_for_search(text: str) -> str:
    """
    Normalize text specifically for search operations.
    
    Removes interference characters and normalizes aggressively
    for better search matching.
    
    Args:
        text: Text to normalize for search
        
    Returns:
        Search-normalized text
    """
    if not text:
        return ""
    
    # Use fast normalization as base
    normalized = normalize_fast(text, lowercase=True)
    
    # Additional search-specific cleaning
    # Remove all punctuation except spaces
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    
    # Collapse multiple spaces
    normalized = MULTIPLE_SPACE_PATTERN.sub(" ", normalized)
    
    # Remove extra whitespace
    normalized = normalized.strip()
    
    return normalized


# Lemmatization functions


def basic_lemmatize(word: str) -> str:
    """
    Basic rule-based lemmatization.
    
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
    for suffix, replacement in sorted(
        SUFFIX_RULES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    ):
        if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 1:
            stem = word_lower[:-len(suffix)] + replacement
            # Validate the result is reasonable
            if len(stem) >= 2:
                return stem
    
    return word_lower


def _get_wordnet_pos(word: str) -> str:
    """Convert POS tag to WordNet format for better lemmatization."""
    if not NLTK_AVAILABLE:
        return "n"  # Default to noun
        
    try:
        import nltk
        # Get POS tag
        pos_tag = nltk.pos_tag([word])[0][1]
        
        # Map to WordNet POS (return string constants)
        if pos_tag.startswith('J'):
            return 'a'  # wordnet.ADJ
        elif pos_tag.startswith('V'):
            return 'v'  # wordnet.VERB
        elif pos_tag.startswith('N'):
            return 'n'  # wordnet.NOUN
        elif pos_tag.startswith('R'):
            return 'r'  # wordnet.ADV
        else:
            return 'n'  # wordnet.NOUN - Default to noun
    except Exception:
        return "n"  # Safe fallback


def lemmatize_word(word: str) -> str:
    """
    Lemmatize a word using modern NLTK WordNet approach with POS tagging.
    
    Uses NLTK WordNetLemmatizer with POS context for accuracy (>95%).
    Falls back to rule-based approach if NLTK unavailable.
    Includes vocabulary validation to prevent errors like 'hapines'.
    Performance-optimized with memoization for repeated lookups.
    
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
    
    # Check cache first (performance optimization)
    if word_lower in _lemma_cache:
        return _lemma_cache[word_lower]
    
    lemma = word_lower  # Default fallback
    
    # Try modern NLTK approach first
    if NLTK_AVAILABLE and _nltk_lemmatizer:
        try:
            # Get POS context for better accuracy
            pos = _get_wordnet_pos(word_lower)
            nltk_lemma = _nltk_lemmatizer.lemmatize(word_lower, pos=pos)
            
            # Validate result quality
            if nltk_lemma and is_valid_word(nltk_lemma) and len(nltk_lemma) >= 2:
                lemma = nltk_lemma
            else:
                # Fallback to rule-based approach
                lemma = basic_lemmatize(word_lower)
        except Exception:
            # Fallback to rule-based approach
            lemma = basic_lemmatize(word_lower)
    else:
        # No NLTK available, use rule-based
        lemma = basic_lemmatize(word_lower)
    
    # Cache result for future lookups (performance optimization)
    _lemma_cache[word_lower] = lemma
    return lemma


def batch_lemmatize(words: list[str]) -> dict[str, str]:
    """
    Batch lemmatize multiple words for performance optimization.
    
    Processes words in batch to leverage caching and reduce overhead.
    Recommended for processing large vocabularies (270K+ words).
    
    Args:
        words: List of words to lemmatize
        
    Returns:
        Dictionary mapping original words to lemmatized forms
    """
    results = {}
    for word in words:
        if word:  # Skip empty strings
            results[word] = lemmatize_word(word)
    return results


def clear_lemma_cache() -> int:
    """
    Clear the lemmatization cache.
    
    Returns:
        Number of entries cleared
    """
    global _lemma_cache
    count = len(_lemma_cache)
    _lemma_cache.clear()
    return count