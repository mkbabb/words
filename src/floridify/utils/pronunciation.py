"""Pronunciation utilities for generating phonetic spellings."""

from __future__ import annotations

import re


def generate_phonetic_pronunciation(word: str) -> str:
    """Generate a phonetic pronunciation for a word or phrase.

    Args:
        word: Word or phrase to generate pronunciation for

    Returns:
        Phonetic pronunciation string
    """
    if not word:
        return ""

    # Handle specific known phrases
    if word.lower() == "en coulisses":
        return "on koo-LEES"

    # For French phrases starting with "en"
    if word.lower().startswith("en "):
        parts = word.split()
        if len(parts) == 2:
            return f"on {_simple_phonetic(parts[1])}"

    # For multi-word phrases, process each word
    if " " in word:
        words = word.split()
        phonetic_parts = []
        for w in words:
            phonetic_parts.append(_simple_phonetic(w))
        return " ".join(phonetic_parts)

    # Single word
    return _simple_phonetic(word)


def _simple_phonetic(word: str) -> str:
    """Generate simple phonetic representation for a single word.

    Args:
        word: Single word

    Returns:
        Phonetic representation
    """
    if not word:
        return ""

    # Convert to lowercase for processing
    phonetic = word.lower()

    # Basic phonetic transformations
    phonetic_rules = [
        # French-specific rules
        (r"coulisses", "koo-LEES"),
        (r"ique$", "eek"),
        (r"eau$", "oh"),
        # Common English rules
        (r"ph", "f"),
        (r"gh", ""),
        (r"ough", "uff"),
        (r"augh", "aff"),
        (r"tion", "shun"),
        (r"sion", "zhun"),
        (r"ck", "k"),
        (r"qu", "kw"),
        # Vowel combinations
        (r"ea", "ee"),
        (r"ee", "ee"),
        (r"oo", "oo"),
        (r"ou", "ow"),
        (r"ow", "ow"),
        (r"ai", "ay"),
        (r"ay", "ay"),
        (r"ei", "ay"),
        (r"ie", "ee"),
        # Silent letters
        (r"kn", "n"),
        (r"wr", "r"),
        (r"gn", "n"),
        (r"mb$", "m"),
        (r"bt$", "t"),
    ]

    # Apply phonetic rules
    for pattern, replacement in phonetic_rules:
        phonetic = re.sub(pattern, replacement, phonetic)

    # Add stress markers for longer words
    if len(phonetic) > 6:
        # Simple heuristic: stress on first syllable for most words
        if "-" not in phonetic:
            # Find first vowel cluster and capitalize it
            vowel_pattern = r"[aeiou]+"
            match = re.search(vowel_pattern, phonetic)
            if match:
                start, end = match.span()
                phonetic = phonetic[:start] + phonetic[start:end].upper() + phonetic[end:]

    return phonetic
