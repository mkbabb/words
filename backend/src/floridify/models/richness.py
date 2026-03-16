"""Pure functions for computing dictionary entry richness scores."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dictionary import Definition, DictionaryEntry


def compute_definition_richness(definition: Definition) -> float:
    """Score a single definition's richness (0.0–1.0)."""
    score = 0.0
    score += 0.20 * min(len(definition.example_ids) / 3, 1.0)
    score += 0.15 * min(len(definition.synonyms) / 5, 1.0)
    score += 0.10 * min(len(definition.antonyms) / 3, 1.0)
    score += 0.10 * min(len(definition.usage_notes) / 2, 1.0)
    score += 0.10 * min(len(definition.grammar_patterns) / 2, 1.0)
    score += 0.10 * min(len(definition.collocations) / 3, 1.0)
    score += 0.10 * (1.0 if definition.cefr_level else 0.0)
    score += 0.05 * (1.0 if definition.frequency_band else 0.0)
    score += 0.05 * (1.0 if definition.domain else 0.0)
    score += 0.05 * (1.0 if definition.language_register else 0.0)
    return score


def compute_entry_richness(
    entry: DictionaryEntry,
    definitions: list[Definition],
) -> float:
    """Score a dictionary entry's overall richness (0.0–1.0)."""
    score = 0.0
    score += 0.25 * min(len(entry.definition_ids) / 10, 1.0)
    score += 0.10 * (1.0 if entry.etymology else 0.0)
    score += 0.10 * (1.0 if entry.pronunciation_id else 0.0)
    score += 0.05 * min(len(entry.image_ids) / 2, 1.0)
    score += 0.05 * min(len(entry.fact_ids) / 2, 1.0)
    score += 0.05 * min(len(entry.phrases) / 3, 1.0)
    score += 0.05 * (1.0 if entry.synonym_chooser else 0.0)

    # Average definition richness
    if definitions:
        avg_def = sum(compute_definition_richness(d) for d in definitions) / len(definitions)
    else:
        avg_def = 0.0
    score += 0.35 * avg_def

    return round(score, 4)
