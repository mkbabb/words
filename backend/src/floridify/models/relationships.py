"""Relationship and supplementary models for dictionary data."""

from __future__ import annotations

import re
from typing import Literal
from uuid import uuid4

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, model_validator

from .base import BaseMetadata

# UUID4 pattern for detecting old slug-as-id vs new UUID id
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


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

    id: str = Field(default_factory=lambda: str(uuid4()))  # UUID primary key
    slug: str = ""  # Human-readable: "bank_noun_financial"
    name: str  # Human-readable cluster name
    description: str  # Brief description of this meaning
    order: int = Field(ge=0)  # Display order
    relevance: float = Field(ge=0.0, le=1.0)  # Usage frequency

    @model_validator(mode="before")
    @classmethod
    def _migrate_old_id_to_slug(cls, data: dict) -> dict:
        """Migrate old documents where id was a slug string (not a UUID)."""
        if not isinstance(data, dict):
            return data
        id_val = data.get("id", "")
        slug_val = data.get("slug", "")
        # Old schema: id was a slug like "bank_noun_financial" (not a UUID)
        if id_val and not _UUID_RE.match(id_val):
            # Migrate: move old slug-id → slug, generate new UUID id
            if not slug_val:
                data["slug"] = id_val
            data["id"] = str(uuid4())
        # If slug is still empty, derive from id (shouldn't happen for new data)
        if not data.get("slug"):
            data["slug"] = data.get("name", "unknown")
        return data


class WordRelationship(Document, BaseMetadata):
    """Relationships between words."""

    from_word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    to_word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    relationship_type: Literal[
        "synonym",
        "antonym",
        "related",
        "compare",
        "see_also",
        "derived_from",
    ]
    strength: float = Field(ge=0.0, le=1.0, default=1.0)
    context: str | None = None

    class Settings:
        name = "word_relationships"
        indexes = [
            [("from_word_id", 1), ("relationship_type", 1)],
            [("to_word_id", 1), ("relationship_type", 1)],
        ]
