"""Adaptive generation counts based on word characteristics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def _clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))


# Part-of-speech factor: function words get fewer synonyms/antonyms than content words
_POS_FACTORS: dict[str, float] = {
    "adjective": 1.0,
    "verb": 1.0,
    "noun": 0.8,
    "adverb": 0.7,
    "preposition": 0.3,
    "conjunction": 0.3,
    "determiner": 0.3,
    "interjection": 0.4,
    "pronoun": 0.3,
    "particle": 0.3,
}

# Bounds for each field
MIN_SYNONYMS, MAX_SYNONYMS = 2, 12
MIN_ANTONYMS, MAX_ANTONYMS = 1, 8
MIN_EXAMPLES, MAX_EXAMPLES = 1, 4
MIN_FACTS, MAX_FACTS = 1, 4
MIN_COLLOCATIONS, MAX_COLLOCATIONS = 2, 8
MIN_USAGE_NOTES, MAX_USAGE_NOTES = 1, 3
MIN_GRAMMAR_PATTERNS, MAX_GRAMMAR_PATTERNS = 1, 3


class AdaptiveCounts(BaseModel):
    """Adaptive generation counts for all generated list fields."""

    model_config = ConfigDict(frozen=True)

    # Definition-level (count-parameterized)
    synonyms: int
    antonyms: int
    examples: int

    # Word-level
    facts: int

    # Assessment (currently only prompt-limited, now code-controlled)
    collocations: int
    usage_notes: int
    grammar_patterns: int


def compute_counts(
    language: str,
    definition_count: int,
    part_of_speech: str | None = None,
) -> AdaptiveCounts:
    """Scale output counts based on word characteristics.

    Args:
        language: ISO language code (e.g., "en", "fr")
        definition_count: Number of definitions for the word
        part_of_speech: Part of speech string, if known

    Returns:
        AdaptiveCounts with scaled counts for each component

    """
    # Language factor: non-English → 0.4x
    lang_factor = 1.0 if language == "en" else 0.4

    # Polysemy factor: single-sense → 1.0, polysemous → up to 1.5x
    poly_factor = min(1.0 + (definition_count - 1) * 0.15, 1.5)

    # POS factor: function words → 0.3x, adj/verb → 1.0x, noun → 0.8x
    pos_factor = _POS_FACTORS.get(part_of_speech, 0.5) if part_of_speech else 0.8

    f = lang_factor * poly_factor * pos_factor

    return AdaptiveCounts(
        synonyms=_clamp(round(5 * f), MIN_SYNONYMS, MAX_SYNONYMS),
        antonyms=_clamp(round(3 * f), MIN_ANTONYMS, MAX_ANTONYMS),
        examples=_clamp(round(2 * lang_factor), MIN_EXAMPLES, MAX_EXAMPLES),
        facts=_clamp(round(2 * poly_factor), MIN_FACTS, MAX_FACTS),
        collocations=_clamp(round(4 * f), MIN_COLLOCATIONS, MAX_COLLOCATIONS),
        usage_notes=_clamp(round(2 * lang_factor), MIN_USAGE_NOTES, MAX_USAGE_NOTES),
        grammar_patterns=_clamp(round(2 * pos_factor), MIN_GRAMMAR_PATTERNS, MAX_GRAMMAR_PATTERNS),
    )
