"""Text processing utilities for cleaning and formatting text content."""

from __future__ import annotations

import re


def clean_markdown(text: str) -> str:
    """Remove markdown formatting from text.
    
    Args:
        text: Text containing markdown formatting
        
    Returns:
        Clean text with markdown formatting removed
    """
    # Remove bold formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Remove italic formatting  
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # Remove code formatting
    text = re.sub(r'`(.*?)`', r'\1', text)
    # Remove links, keep link text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    return text


def ensure_sentence_case(text: str) -> str:
    """Ensure text has proper sentence case: capital first letter, period at end.
    
    Args:
        text: Text to format
        
    Returns:
        Text with proper sentence case
    """
    if not text:
        return text

    # Strip whitespace and ensure first letter is capitalized
    text = text.strip()
    if not text:
        return text

    # Capitalize first letter
    text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

    # Ensure ends with period if it doesn't end with punctuation
    if not text.endswith(('.', '!', '?', ':', ';')):
        text += '.'

    return text


def bold_word_in_text(text: str, word: str) -> list[tuple[str, str]]:
    """Find and mark word/phrase for bolding in text.
    
    Args:
        text: Text to search in
        word: Word or phrase to bold
        
    Returns:
        List of (text_part, style) tuples for rich formatting
    """
    word_lower = word.lower()
    text_lower = text.lower()
    
    # Try to find the complete phrase first
    if word_lower in text_lower:
        pattern = re.compile(re.escape(word_lower), re.IGNORECASE)
        parts = pattern.split(text)
        matches = pattern.findall(text)
        
        result = []
        for i, part in enumerate(parts):
            if i > 0 and i <= len(matches):
                result.append((matches[i - 1], "bold"))
            if part:
                result.append((part, "normal"))
        return result
    
    # Fallback for multi-word phrases
    word_parts = word_lower.split()
    if len(word_parts) > 1:
        return [(text, "normal")]
    
    # Single word fallback - try to bold significant word parts
    for word_part in word_parts:
        if len(word_part) > 3 and word_part in text_lower:
            pattern = re.compile(re.escape(word_part), re.IGNORECASE)
            if pattern.search(text):
                parts = pattern.split(text)
                matches = pattern.findall(text)
                
                result = []
                for i, part in enumerate(parts):
                    if i > 0 and i <= len(matches):
                        result.append((matches[i - 1], "bold"))
                    if part:
                        result.append((part, "normal"))
                return result
    
    # No matches found
    return [(text, "normal")]