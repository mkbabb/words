"""Unified corpus data models.

This module provides the core data models for corpus management,
unifying language and literature corpus data into a consistent structure.
"""

from __future__ import annotations

from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.models import CacheableMetadata
from ..models.base import BaseMetadata
from ..models.dictionary import Language


class LexiconData(BaseModel):
    """Base lexicon data for all corpus types.

    This is the unified model for both language and literature corpora.
    Vocabulary is always stored as unique words only.
    """

    vocabulary: list[str]
    language: Language = Language.ENGLISH
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Reference to parent corpus
    corpus_id: PydanticObjectId | None = Field(
        default=None,
        description="Reference to the parent CorpusMetadata document",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize with unique vocabulary."""
        super().__init__(**data)
        # Ensure vocabulary is unique
        if self.vocabulary:
            self.vocabulary = list(set(self.vocabulary))


class CorpusMetadata(Document, BaseMetadata, CacheableMetadata):
    """Metadata for a corpus source."""

    name: str
    description: str | None = None
    language: Language

    class Settings:
        name = "corpus_metadata"
        indexes = [
            [("corpus_id", 1)],
            [("name", 1)],
            [("language", 1)],
        ]
