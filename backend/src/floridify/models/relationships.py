"""Relationship and supplementary models for dictionary data."""

from __future__ import annotations

from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from .base import BaseMetadata


class WordForm(BaseModel):
    """Word inflections and variations."""

    form_type: Literal[
        "plural",
        "past",
        "past_participle",
        "present_participle",
        "comparative",
        "superlative",
        "variant",
    ]
    text: str


class GrammarPattern(BaseModel):
    """Grammar patterns and verb frames."""

    pattern: str  # e.g., "[Tn]", "sb/sth"
    description: str | None = None


class Collocation(BaseModel):
    """Common word combinations."""

    text: str
    type: str  # Allow flexible collocation types like "adjective+noun", "verb+noun", etc.
    frequency: float = Field(ge=0.0, le=1.0)


class UsageNote(BaseModel):
    """Usage guidance and warnings."""

    type: Literal["grammar", "confusion", "regional", "register", "error"]
    text: str


class MeaningCluster(BaseModel):
    """Semantic grouping metadata."""

    id: str
    name: str  # Human-readable cluster name
    description: str  # Brief description of this meaning
    order: int = Field(ge=0)  # Display order
    relevance: float = Field(ge=0.0, le=1.0)  # Usage frequency


class WordRelationship(Document, BaseMetadata):
    """Relationships between words."""

    from_word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    to_word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    relationship_type: Literal[
        "synonym", "antonym", "related", "compare", "see_also", "derived_from"
    ]
    strength: float = Field(ge=0.0, le=1.0, default=1.0)
    context: str | None = None

    class Settings:
        name = "word_relationships"
        indexes = [
            [("from_word_id", 1), ("relationship_type", 1)],
            [("to_word_id", 1), ("relationship_type", 1)],
        ]
