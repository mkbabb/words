"""Local language register classification using keyword taxonomy.

Classifies definitions as formal, informal, neutral, slang, or technical
based on indicator words in the definition text and Wiktionary labels.
Extends the pattern from wiktionary_parser.py:703-757.
"""

from __future__ import annotations

import re
from typing import Literal

RegisterType = Literal["formal", "informal", "neutral", "slang", "technical"]

# Keyword sets for register detection — ordered by specificity
_REGISTER_PATTERNS: list[tuple[RegisterType, list[str]]] = [
    ("slang", [
        "slang", "vulgar", "profanity", "taboo", "offensive",
        "derogatory", "pejorative", "crude",
    ]),
    ("informal", [
        "informal", "colloquial", "casual", "conversational",
        "everyday", "nonstandard", "non-standard", "humorous",
        "jocular", "playful",
    ]),
    ("formal", [
        "formal", "literary", "poetic", "elevated",
        "rhetorical", "academic",
    ]),
    ("technical", [
        "technical", "specialized", "scientific", "medical",
        "legal", "computing", "mathematics", "chemistry",
        "biology", "physics", "engineering", "nautical",
        "military", "architecture", "botany", "zoology",
        "astronomy", "geology", "philosophy", "theology",
        "linguistics", "music theory",
    ]),
]

# Compiled regex for efficiency
_REGISTER_REGEXES: list[tuple[RegisterType, re.Pattern[str]]] = [
    (register, re.compile(r"\b(" + "|".join(re.escape(kw) for kw in keywords) + r")\b", re.IGNORECASE))
    for register, keywords in _REGISTER_PATTERNS
]


def classify_register_local(definition_text: str) -> RegisterType | None:
    """Classify the language register of a definition from its text content.

    Returns:
        Register type string, or None if no clear indicator found.
    """
    for register, pattern in _REGISTER_REGEXES:
        if pattern.search(definition_text):
            return register

    return None
