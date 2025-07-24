"""Models for phrasal expressions, idioms, and multi-word units."""

from __future__ import annotations

from typing import Literal

from beanie import Document

from .base import BaseMetadata


class PhrasalExpression(Document, BaseMetadata):
    """Phrasal verbs, idioms, and multi-word expressions."""
    
    base_word_id: str  # FK to main Word
    expression: str  # Full expression text
    type: Literal["phrasal_verb", "idiom", "colloquialism", "proverb"]
    definition_ids: list[str] = []  # FK to Definition documents
    separable: bool | None = None  # For phrasal verbs
    
    class Settings:
        name = "phrasal_expressions"
        indexes = ["base_word_id", "type", "expression"]