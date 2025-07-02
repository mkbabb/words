"""Word list parsing functionality."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import coolname
from pydantic import BaseModel, Field

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ParsedWordList(BaseModel):
    """Result of parsing a word list file."""
    
    words: list[str] = Field(..., description="Extracted words")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Parsing metadata")
    source_file: str | None = Field(default=None, description="Source file path")


def parse_file(file_path: Path) -> ParsedWordList:
    """Parse word list from file with format detection."""
    if not file_path.exists():
        raise FileNotFoundError(f"Word list file not found: {file_path}")
    
    logger.info(f"📋 Parsing word list from: {file_path}")
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 decode failed, trying latin-1 for: {file_path}")
        content = file_path.read_text(encoding='latin-1')
    
    words = _extract_words(content)
    
    metadata = {
        "file_size": file_path.stat().st_size,
        "raw_lines": len(content.splitlines()),
        "extracted_words": len(words),
        "format_detected": _detect_format(content),
    }
    
    logger.info(f"✅ Extracted {len(words)} words from {metadata['raw_lines']} lines")
    
    return ParsedWordList(
        words=words,
        metadata=metadata,
        source_file=str(file_path)
    )


def generate_name(words: list[str]) -> str:
    """Generate a human-readable animal phrase name."""
    try:
        # Generate a cool name with adjective + animal format
        name = coolname.generate_slug(2)  # 2 words: adjective-animal
        logger.debug(f"Generated name: {name}")
        return name
    except Exception as e:
        logger.warning(f"Failed to generate cool name: {e}")
        # Fallback to hash-based name
        from .models import WordList
        hash_id = WordList.generate_hash(words)
        return f"wordlist-{hash_id}"


def _extract_words(content: str) -> list[str]:
    """Extract words from content using multiple strategies."""
    lines = content.splitlines()
    words = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):  # Skip empty lines and comments
            continue
        
        # Try different parsing strategies
        line_words = _parse_line(line)
        words.extend(line_words)
    
    # Clean words but preserve duplicates for frequency tracking
    cleaned_words = []
    
    for word in words:
        word_clean = _clean_word(word)
        if word_clean:
            cleaned_words.append(word_clean)
    
    return cleaned_words


def _parse_line(line: str) -> list[str]:
    """Parse a single line using various strategies."""
    # Strategy 1: Numbered list (e.g., "1. Word", "2) Word")
    numbered_match = re.match(r'^\d+[.)]\s*(.+)', line)
    if numbered_match:
        return [numbered_match.group(1).strip()]
    
    # Strategy 2: Comma-separated values
    if ',' in line:
        return [word.strip() for word in line.split(',')]
    
    # Strategy 3: Tab-separated values
    if '\t' in line:
        return [word.strip() for word in line.split('\t')]
    
    # Strategy 4: Multiple words separated by spaces (but not phrases)
    words = line.split()
    if len(words) > 1:
        # Check if it looks like a phrase vs multiple words
        if _looks_like_phrase(line):
            return [line]
        else:
            return words
    
    # Strategy 5: Single word or phrase
    return [line]


def _looks_like_phrase(text: str) -> bool:
    """Determine if text is likely a single phrase vs multiple words."""
    # If it has articles, prepositions, or conjunctions, likely a phrase
    phrase_indicators = {
        'a', 'an', 'the', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'to', 'and', 'or'
    }
    words = text.lower().split()
    return len(words) <= 5 and any(word in phrase_indicators for word in words)


def _clean_word(word: str) -> str:
    """Clean and normalize a word."""
    # Remove leading/trailing whitespace and punctuation
    word = word.strip().strip('.,;:!?"\'()[]{}')
    
    # Remove extra whitespace
    word = ' '.join(word.split())
    
    # Skip very short or very long words
    if len(word) < 2 or len(word) > 50:
        return ""
    
    # Skip if it's just numbers or special characters
    if re.match(r'^[\d\W]+$', word):
        return ""
    
    return word


def _detect_format(content: str) -> str:
    """Detect the format of the word list."""
    lines = content.splitlines()[:10]  # Check first 10 lines
    
    numbered_count = sum(1 for line in lines if re.match(r'^\d+[.)]', line.strip()))
    comma_count = sum(1 for line in lines if ',' in line)
    tab_count = sum(1 for line in lines if '\t' in line)
    
    if numbered_count >= len(lines) * 0.5:
        return "numbered_list"
    elif comma_count >= len(lines) * 0.5:
        return "comma_separated"
    elif tab_count >= len(lines) * 0.5:
        return "tab_separated"
    else:
        return "plain_text"