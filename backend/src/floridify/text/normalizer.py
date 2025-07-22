"""Text normalization and lemmatization utilities."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

try:
    import contractions
    CONTRACTIONS_AVAILABLE = True
except ImportError:
    CONTRACTIONS_AVAILABLE = False

try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False

from .processor import get_text_processor
from ..utils.logging import get_logger

logger = get_logger(__name__)


# Pre-compiled regex patterns for performance
WHITESPACE_PATTERN = re.compile(r'\s+')
PUNCTUATION_PATTERN = re.compile(r'[^\w\s\'-]', re.UNICODE) 

# Translation table for character replacements (faster than regex)
CHAR_TRANSLATION_TABLE = str.maketrans({
    # Hyphen variants
    '–': '-', '—': '-', '‒': '-',
    # Apostrophe variants  
    '`': "'", '"': '"', '"': '"'
})

# Basic suffix rules for lemmatization fallback
SUFFIX_RULES = {
    'ies': 'y',   # stories -> story
    'ves': 'f',   # knives -> knife  
    'ing': '',    # running -> run
    'ed': '',     # walked -> walk
    'er': '',     # bigger -> big
    'est': '',    # biggest -> big
    'ly': '',     # quickly -> quick
    's': '',      # cats -> cat
}


def normalize_text(text: str, fix_encoding: bool = True, expand_contractions: bool = True) -> str:
    """
    Comprehensive text normalization.
    
    Args:
        text: Input text to normalize
        fix_encoding: Whether to fix encoding issues
        expand_contractions: Whether to expand contractions
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    normalized = text
    
    # Step 1: Fix encoding issues if available
    if fix_encoding and FTFY_AVAILABLE:
        try:
            normalized = ftfy.fix_text(normalized)
        except Exception as e:
            logger.debug(f"ftfy failed: {e}")
    
    # Step 2: Unicode normalization
    normalized = unicodedata.normalize("NFC", normalized)
    
    # Step 3: Case normalization
    normalized = normalized.lower()
    
    # Step 4: Standardize punctuation (using translate for better performance)
    normalized = normalized.translate(CHAR_TRANSLATION_TABLE)
    
    # Step 5: Expand contractions if available
    if expand_contractions and CONTRACTIONS_AVAILABLE:
        try:
            normalized = contractions.fix(normalized, slang=False)
        except Exception as e:
            logger.debug(f"Contractions expansion failed: {e}")
    
    # Step 6: Remove excess punctuation (but preserve hyphens and apostrophes)
    normalized = PUNCTUATION_PATTERN.sub(" ", normalized)
    
    # Step 7: Normalize whitespace
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    
    return normalized.strip()


def lemmatize_word(word: str) -> str:
    """
    Lemmatize a single word using best available method.
    
    Args:
        word: Word to lemmatize
        
    Returns:
        Lemmatized word
    """
    if not word.strip():
        return word
    
    processor = get_text_processor()
    return processor.lemmatize(word)


def basic_lemmatize(word: str) -> str:
    """
    Basic lemmatization using rule-based suffix removal.
    
    Args:
        word: Word to lemmatize
        
    Returns:
        Lemmatized word
    """
    if not word or len(word) < 3:
        return word
    
    word = word.lower().strip()
    
    # Apply suffix rules
    for suffix, replacement in SUFFIX_RULES.items():
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            # Handle special cases
            if suffix == 'ing' and word[-4] == word[-5]:  # running -> run
                return word[:-4]
            elif suffix == 'ed' and word[-3] == word[-4]:  # stopped -> stop
                return word[:-3]
            else:
                return word[:-len(suffix)] + replacement
    
    return word


def normalize_for_search(text: str) -> str:
    """
    Normalize text specifically for search operations.
    
    Args:
        text: Text to normalize
        
    Returns:
        Search-optimized normalized text
    """
    if not text:
        return ""
    
    # Apply basic normalization
    normalized = normalize_text(text, fix_encoding=False, expand_contractions=False)
    
    # Remove extra characters that might interfere with search
    normalized = re.sub(r'[^\w\s-]', ' ', normalized)
    normalized = WHITESPACE_PATTERN.sub(' ', normalized)
    
    return normalized.strip()


def clean_word(word: str) -> str:
    """
    Clean a single word for processing.
    
    Args:
        word: Word to clean
        
    Returns:
        Cleaned word
    """
    if not word:
        return ""
    
    # Remove non-alphabetic characters except hyphens and apostrophes
    cleaned = re.sub(r"[^a-zA-Z'-]", "", word.strip().lower())
    
    return cleaned


def is_valid_word(word: str, min_length: int = 2) -> bool:
    """
    Check if a word is valid for processing.
    
    Args:
        word: Word to validate
        min_length: Minimum required length
        
    Returns:
        True if word is valid
    """
    if not word:
        return False
    
    cleaned = clean_word(word)
    
    # Check length and alphabetic content
    if len(cleaned) < min_length:
        return False
    
    # Must contain at least one alphabetic character
    if not any(c.isalpha() for c in cleaned):
        return False
    
    return True