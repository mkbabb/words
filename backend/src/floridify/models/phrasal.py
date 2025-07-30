"""Models for phrasal expressions, idioms, and multi-word units."""

from __future__ import annotations

from typing import Literal

from beanie import Document, PydanticObjectId

from .base import DocumentWithObjectIdSupport


class PhrasalExpression(DocumentWithObjectIdSupport):
    """Phrasal verbs, idioms, and multi-word expressions."""

    base_word_id: PydanticObjectId  # FK to main Word - optimized with ObjectId
    expression: str  # Full expression text
    type: Literal["phrasal_verb", "idiom", "colloquialism", "proverb"]
    definition_ids: list[
        PydanticObjectId
    ] = []  # FK to Definition documents - optimized with ObjectIds
    separable: bool | None = None  # For phrasal verbs

    class Settings:
        name = "phrasal_expressions"
        indexes = ["base_word_id", "type", "expression"]
