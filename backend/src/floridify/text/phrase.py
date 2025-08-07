"""Phrase detection utility.

Provides minimal phrase detection for corpus parsing.
"""

from __future__ import annotations


def is_phrase(text: str) -> bool:
    """
    Check if text contains multiple words (is a phrase).

    Args:
        text: Text to check

    Returns:
        True if text contains multiple words
    """
    if not text:
        return False

    # Check for whitespace (simple phrase detection)
    normalized = text.strip()
    return len(normalized.split()) > 1
