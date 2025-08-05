"""
Text tokenization utilities.

Functions for splitting text into tokens (words, sentences).
"""

from __future__ import annotations

import re

from .normalize import normalize_fast
from .patterns import (
    ADVANCED_WORD_PATTERN,
    SENTENCE_PATTERN,
    WORD_PATTERN,
)


def tokenize(text: str) -> list[str]:
    """
    Tokenize text using the best available method.
    
    Currently uses word tokenization.
    
    Args:
        text: Text to tokenize
        
    Returns:
        List of tokens
    """
    if not text:
        return []
    
    return word_tokenize(text)


def word_tokenize(text: str) -> list[str]:
    """
    Fast word tokenization using regex.
    
    Args:
        text: Text to tokenize
        
    Returns:
        List of word tokens
    """
    if not text:
        return []
    
    return WORD_PATTERN.findall(text)


def advanced_word_tokenize(text: str) -> list[str]:
    """
    Advanced word tokenization that handles contractions and punctuation.
    
    Args:
        text: Text to tokenize
        
    Returns:
        List of tokens including punctuation
    """
    if not text:
        return []
    
    return ADVANCED_WORD_PATTERN.findall(text)


def sentence_tokenize(text: str) -> list[str]:
    """
    Split text into sentences.
    
    Basic sentence splitting on common punctuation.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentences
    """
    if not text:
        return []
    
    # Split on sentence endings
    sentences = SENTENCE_PATTERN.split(text)
    
    # Clean up and filter
    result = []
    for sent in sentences:
        sent = sent.strip()
        if sent:
            result.append(sent)
    
    return result


def smart_tokenize(
    text: str,
    preserve_contractions: bool = True,
    preserve_punctuation: bool = False,
    lowercase: bool = False,
) -> list[str]:
    """
    Configurable tokenization with various options.
    
    Args:
        text: Text to tokenize
        preserve_contractions: Keep contractions together
        preserve_punctuation: Include punctuation tokens
        lowercase: Convert tokens to lowercase
        
    Returns:
        List of tokens
    """
    if not text:
        return []
    
    # Choose tokenization method
    if preserve_punctuation or preserve_contractions:
        tokens = advanced_word_tokenize(text)
    else:
        tokens = word_tokenize(text)
    
    # Filter punctuation if not preserving
    if not preserve_punctuation:
        tokens = [t for t in tokens if re.match(r"\w", t)]
    
    # Lowercase if requested
    if lowercase:
        tokens = [t.lower() for t in tokens]
    
    return tokens


def tokenize_for_search(text: str) -> list[str]:
    """
    Tokenize text specifically for search operations.
    
    Normalizes and tokenizes aggressively for better matching.
    
    Args:
        text: Text to tokenize
        
    Returns:
        List of normalized tokens
    """
    if not text:
        return []
    
    # Normalize first
    normalized = normalize_fast(text, lowercase=True)
    
    # Simple word tokenization
    tokens = word_tokenize(normalized)
    
    # Additional filtering
    return [t for t in tokens if len(t) > 1]