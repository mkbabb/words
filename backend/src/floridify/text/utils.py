"""Text utility functions for phrase processing."""

from __future__ import annotations

import re

from ..utils.logging import get_logger
from .normalizer import normalize_text
from .tokenizer import word_tokenize

logger = get_logger(__name__)


# Enhanced pre-compiled patterns for robust phrase detection (2025 best practices)
HYPHEN_PATTERN = re.compile(r'[-–—]')
HYPHENATED_PATTERN = re.compile(r'\b\w+(?:[-–—]\w+){1,4}\b', re.UNICODE)
QUOTED_PATTERN = re.compile(r'["\'\'""\«]([^"\'\'""\»]+)["\'\'""\»]')

# Advanced multi-word expression patterns (based on NLP research)
COMPOUND_PATTERN = re.compile(r'\b\w+(?:[\s-]\w+)+\b', re.UNICODE)  # Multi-word compounds
IDIOM_PATTERN = re.compile(r'\b(?:out of|in order to|as well as|in spite of|on behalf of)\b', re.IGNORECASE)  # Common English idioms
COLLOCATION_PATTERN = re.compile(r'\b(?:strongly|highly|deeply)\s+(?:recommend|suggest|believe)\b', re.IGNORECASE)  # Collocation patterns
PREPOSITIONAL_PATTERN = re.compile(r'\b(?:in|on|at|by|for|with|under|over)\s+(?:the|a|an)?\s*\w+(?:\s+\w+)*\b', re.IGNORECASE)  # Prepositional phrases


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


def extract_phrases(text: str, include_advanced_patterns: bool = True) -> list[str]:
    """
    Extract all types of multi-word expressions using advanced NLP patterns.
    
    Based on 2025 best practices for multi-word expression detection,
    combining rule-based patterns with tokenization-based approaches.
    
    Args:
        text: Input text to analyze
        include_advanced_patterns: Whether to use advanced MWE detection patterns
        
    Returns:
        List of extracted phrases with confidence-based filtering
    """
    if not text.strip():
        return []
    
    phrases = []
    
    # Primary: Simple phrase detection based on word count
    tokens = word_tokenize(text)
    if len(tokens) > 1:
        normalized = normalize_text(text)
        if normalized:
            phrases.append(normalized)
    
    if include_advanced_patterns:
        # Advanced multi-word expression detection (based on research)
        
        # Find compound expressions (space or hyphen separated)
        compound_matches = COMPOUND_PATTERN.findall(text)
        for match in compound_matches:
            normalized = normalize_text(match)
            if normalized and len(word_tokenize(normalized)) >= 2:
                phrases.append(normalized)
        
        # Find common English idioms
        idiom_matches = IDIOM_PATTERN.findall(text)
        for match in idiom_matches:
            # Expand context around idioms
            idiom_start = text.lower().find(match.lower())
            if idiom_start >= 0:
                # Get 2-3 words before and after for context
                words_before = text[:idiom_start].split()[-2:]
                words_after = text[idiom_start + len(match):].split()[:2]
                
                extended_phrase = ' '.join(words_before + [match] + words_after)
                normalized = normalize_text(extended_phrase)
                if normalized and len(word_tokenize(normalized)) >= 2:
                    phrases.append(normalized)
        
        # Find collocation patterns
        collocation_matches = COLLOCATION_PATTERN.findall(text)
        for match in collocation_matches:
            normalized = normalize_text(match)
            if normalized:
                phrases.append(normalized)
        
        # Find prepositional phrases (common MWEs)
        prep_matches = PREPOSITIONAL_PATTERN.findall(text)
        for match in prep_matches:
            normalized = normalize_text(match)
            if normalized and len(word_tokenize(normalized)) >= 2:
                # Filter out overly long prepositional phrases
                if len(word_tokenize(normalized)) <= 5:
                    phrases.append(normalized)
    
    # Traditional pattern detection
    hyphenated = find_hyphenated_phrases(text)
    phrases.extend(hyphenated)
    
    quoted = find_quoted_phrases(text)
    phrases.extend(quoted)
    
    # Enhanced deduplication with length-based filtering
    seen = set()
    unique_phrases = []
    for phrase in phrases:
        phrase_clean = phrase.strip()
        if phrase_clean and phrase_clean not in seen:
            # Quality filter: reasonable length, meaningful content
            tokens = word_tokenize(phrase_clean)
            if 2 <= len(tokens) <= 6 and not all(len(token) <= 2 for token in tokens):
                seen.add(phrase_clean)
                unique_phrases.append(phrase_clean)
    
    return unique_phrases


def phrase_word_count(phrase: str, count_hyphenated_as_multiple: bool = True) -> int:
    """
    Count words in a phrase with advanced handling of compounds.
    
    Args:
        phrase: Phrase to count words in
        count_hyphenated_as_multiple: Whether hyphenated words count as multiple words
        
    Returns:
        Number of words (with intelligent compound handling)
    """
    if not phrase.strip():
        return 0
    
    tokens = word_tokenize(phrase)
    word_count = 0
    
    for token in tokens:
        if not token.strip():
            continue
            
        if count_hyphenated_as_multiple and HYPHEN_PATTERN.search(token):
            # Count each part of hyphenated compound as separate word
            parts = HYPHEN_PATTERN.split(token)
            word_count += len([part for part in parts if part.strip()])
        else:
            word_count += 1
    
    return word_count


def is_compound_word(word: str, min_parts: int = 2) -> bool:
    """
    Advanced compound word detection with configurable sensitivity.
    
    Args:
        word: Word to check
        min_parts: Minimum number of parts to qualify as compound
        
    Returns:
        True if word is a compound (hyphenated or space-separated)
    """
    if not word.strip():
        return False
    
    # Check for hyphenated compounds
    if HYPHEN_PATTERN.search(word):
        parts = HYPHEN_PATTERN.split(word)
        valid_parts = [part for part in parts if part.strip()]
        return len(valid_parts) >= min_parts
    
    # Check for space-separated compounds
    tokens = word_tokenize(word)
    return len(tokens) >= min_parts


def normalize_phrase(phrase: str, preserve_hyphens: bool = True) -> str:
    """
    Advanced phrase normalization following 2025 best practices.
    
    Args:
        phrase: Phrase to normalize
        preserve_hyphens: Whether to preserve hyphen-separated compounds
        
    Returns:
        Normalized phrase with consistent formatting
    """
    if not phrase:
        return ""
    
    # Apply comprehensive text normalization
    normalized = normalize_text(phrase)
    
    if preserve_hyphens:
        # Normalize hyphen variants to standard ASCII hyphen
        normalized = re.sub(r'[–—]', '-', normalized)
    
    # Ensure consistent spacing (single spaces)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Remove leading/trailing punctuation except hyphens
    if preserve_hyphens:
        normalized = re.sub(r'^[^\w\s-]+|[^\w\s-]+$', '', normalized)
    else:
        normalized = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', normalized)
    
    return normalized.strip()


def detect_multiword_expressions(text: str, confidence_threshold: float = 0.7) -> list[tuple[str, float]]:
    """
    Advanced multi-word expression detection with confidence scoring.
    
    Based on 2025 NLP research combining multiple detection methods.
    
    Args:
        text: Text to analyze for MWEs
        confidence_threshold: Minimum confidence score to include results
        
    Returns:
        List of (phrase, confidence_score) tuples
    """
    if not text.strip():
        return []
    
    mwe_candidates = []
    
    # Extract all potential phrases
    phrases = extract_phrases(text, include_advanced_patterns=True)
    
    for phrase in phrases:
        confidence = calculate_mwe_confidence(phrase, text)
        if confidence >= confidence_threshold:
            mwe_candidates.append((phrase, confidence))
    
    # Sort by confidence (highest first)
    return sorted(mwe_candidates, key=lambda x: x[1], reverse=True)


def calculate_mwe_confidence(phrase: str, context: str = "") -> float:
    """
    Calculate confidence score for multi-word expression candidacy.
    
    Args:
        phrase: Phrase to evaluate
        context: Original text context (optional)
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not phrase.strip():
        return 0.0
    
    confidence = 0.0
    tokens = word_tokenize(phrase)
    
    # Base score for multi-word nature
    if len(tokens) >= 2:
        confidence += 0.3
    
    # Bonus for hyphenated compounds (often legitimate MWEs)
    if HYPHEN_PATTERN.search(phrase):
        confidence += 0.2
    
    # Bonus for quoted expressions (likely intentional phrases)
    if context and phrase in QUOTED_PATTERN.findall(context):
        confidence += 0.3
    
    # Bonus for common idiom patterns
    if IDIOM_PATTERN.search(phrase.lower()):
        confidence += 0.4
    
    # Bonus for collocation patterns
    if COLLOCATION_PATTERN.search(phrase.lower()):
        confidence += 0.3
    
    # Penalty for very long phrases (likely spurious)
    if len(tokens) > 5:
        confidence -= 0.2
    
    # Penalty for very short words (likely not meaningful MWEs)
    if all(len(token) <= 2 for token in tokens):
        confidence -= 0.3
    
    return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]


def get_phrase_variants(phrase: str) -> list[str]:
    """
    Generate spelling and formatting variants of a phrase.
    
    Args:
        phrase: Original phrase
        
    Returns:
        List of phrase variants
    """
    if not phrase.strip():
        return []
    
    variants = [phrase]
    
    # Hyphenated variants
    if ' ' in phrase and not HYPHEN_PATTERN.search(phrase):
        hyphenated = phrase.replace(' ', '-')
        variants.append(hyphenated)
    
    # Space-separated variants
    if HYPHEN_PATTERN.search(phrase):
        spaced = HYPHEN_PATTERN.sub(' ', phrase)
        variants.append(spaced)
    
    # Normalized variants
    for variant in list(variants):
        normalized = normalize_phrase(variant)
        if normalized and normalized not in variants:
            variants.append(normalized)
    
    return list(set(variants))  # Deduplicate