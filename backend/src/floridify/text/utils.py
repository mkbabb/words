"""Text utility functions for phrase processing."""

from __future__ import annotations

import re
from typing import Any

from .tokenizer import tokenize, word_tokenize
from .normalizer import normalize_text
from ..utils.logging import get_logger

logger = get_logger(__name__)


# Pre-compiled patterns for performance
HYPHEN_PATTERN = re.compile(r'[-–—]')
HYPHENATED_PATTERN = re.compile(r'\b\w+(?:[-–—]\w+){1,4}\b', re.UNICODE)
QUOTED_PATTERN = re.compile(r'["\'\'""\«]([^"\'\'""\»]+)["\'\'""\»]')


def is_phrase(text: str) -> bool:
    """
    Determine if text represents a multi-word expression.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if text is a multi-word expression
    """
    if not text.strip():
        return False
    
    # Use tokenization to intelligently detect phrases
    tokens = word_tokenize(text.strip())
    
    # Multiple tokens = phrase
    if len(tokens) > 1:
        return True
    
    # Single hyphenated compound = phrase
    if len(tokens) == 1 and HYPHEN_PATTERN.search(tokens[0]):
        return True
    
    return False


def split_phrase(phrase: str) -> list[str]:
    """
    Split a phrase into component words.
    
    Args:
        phrase: Phrase to split
        
    Returns:
        List of component words
    """
    if not phrase.strip():
        return []
    
    words = []
    tokens = word_tokenize(phrase)
    
    for token in tokens:
        if not token.strip():
            continue
        
        # Handle hyphenated compounds
        if HYPHEN_PATTERN.search(token):
            parts = HYPHEN_PATTERN.split(token)
            words.extend([part for part in parts if part.strip()])
        else:
            words.append(token)
    
    return [word for word in words if word.strip()]


def join_words(words: list[str], prefer_hyphens: bool = False) -> str:
    """
    Join words into a phrase with intelligent separator selection.
    
    Args:
        words: List of words to join
        prefer_hyphens: Whether to use hyphens instead of spaces
        
    Returns:
        Joined phrase
    """
    if not words:
        return ""
    
    # Filter out empty words
    valid_words = [word.strip() for word in words if word.strip()]
    if not valid_words:
        return ""
    
    separator = "-" if prefer_hyphens else " "
    return separator.join(valid_words)


def find_hyphenated_phrases(text: str) -> list[str]:
    """
    Find hyphenated compound expressions.
    
    Args:
        text: Input text to search
        
    Returns:
        List of hyphenated phrases found
    """
    if not text:
        return []
    
    matches = HYPHENATED_PATTERN.findall(text)
    
    phrases = []
    for match in matches:
        # Count hyphen variants to determine word count
        hyphen_count = len(HYPHEN_PATTERN.findall(match))
        word_count = hyphen_count + 1
        
        if word_count >= 2:  # At least 2 words
            normalized = normalize_text(match)
            if normalized:
                phrases.append(normalized)
    
    return phrases


def find_quoted_phrases(text: str) -> list[str]:
    """
    Find phrases enclosed in quotes.
    
    Args:
        text: Input text to search
        
    Returns:
        List of quoted phrases found
    """
    if not text:
        return []
    
    matches = QUOTED_PATTERN.findall(text)
    
    phrases = []
    for match in matches:
        phrase_text = match.strip()
        if not phrase_text:
            continue
        
        normalized = normalize_text(phrase_text)
        tokens = word_tokenize(normalized)
        
        if len(tokens) >= 2:  # Multi-word phrases only
            phrases.append(normalized)
    
    return phrases


def extract_phrases(text: str) -> list[str]:
    """
    Extract all types of multi-word expressions from text.
    
    Args:
        text: Input text to analyze
        
    Returns:
        List of extracted phrases
    """
    if not text.strip():
        return []
    
    phrases = []
    
    # Simple phrase detection based on word count
    tokens = word_tokenize(text)
    if len(tokens) > 1:
        normalized = normalize_text(text)
        if normalized:
            phrases.append(normalized)
    
    # Find hyphenated compounds
    hyphenated = find_hyphenated_phrases(text)
    phrases.extend(hyphenated)
    
    # Find quoted phrases
    quoted = find_quoted_phrases(text)
    phrases.extend(quoted)
    
    # Deduplicate while preserving order
    seen = set()
    unique_phrases = []
    for phrase in phrases:
        if phrase not in seen:
            seen.add(phrase)
            unique_phrases.append(phrase)
    
    return unique_phrases


def phrase_word_count(phrase: str) -> int:
    """
    Count the number of words in a phrase.
    
    Args:
        phrase: Phrase to count words in
        
    Returns:
        Number of words
    """
    if not phrase.strip():
        return 0
    
    tokens = word_tokenize(phrase)
    return len([token for token in tokens if token.strip()])


def is_compound_word(word: str) -> bool:
    """
    Check if a word is a hyphenated compound.
    
    Args:
        word: Word to check
        
    Returns:
        True if word is a hyphenated compound
    """
    if not word.strip():
        return False
    
    return bool(HYPHEN_PATTERN.search(word))


def normalize_phrase(phrase: str) -> str:
    """
    Normalize a phrase for consistent processing.
    
    Args:
        phrase: Phrase to normalize
        
    Returns:
        Normalized phrase
    """
    if not phrase:
        return ""
    
    # Apply text normalization
    normalized = normalize_text(phrase)
    
    # Ensure consistent spacing
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()