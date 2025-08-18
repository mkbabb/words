from __future__ import annotations

from enum import Enum
from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from ..caching.models import (
    BaseVersionedData,
    CacheNamespace,
    ContentLocation,
    ResourceType,
)
from ..models.base import Language
from ..models.versioned import register_model


class CorpusType(Enum):
    """Types of corpora in the system."""

    LEXICON = "lexicon"  # Dictionary/vocabulary corpus
    LITERATURE = "literature"  # Literature corpus
    LANGUAGE = "language"  # Language-specific corpus
    WORDLIST = "wordlist"  # Individual wordlist corpus
    WORDLIST_NAMES = "wordlist_names"  # All wordlist names corpus
    CUSTOM = "custom"  # User-defined corpus


class CorpusSource(BaseModel):
    """Configuration for a corpus source."""

    name: str = Field(..., description="Unique identifier for the source")
    url: str = Field(default="", description="URL to download the corpus data")
    parser: str | None = Field(
        default="parse_text_lines",
        description="Function to parse raw data into vocabulary",
    )
    language: Language = Field(..., description="Language of the corpus")
    description: str = Field(default="", description="Human-readable description")
    scraper: str | None = Field(
        default=None,
        description="Optional custom scraper function",
    )

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


@register_model(ResourceType.CORPUS)
class CorpusMetadata(BaseVersionedData):
    """Corpus metadata with tree hierarchy for vocabulary management."""

    corpus_type: CorpusType
    language: Language

    # Tree hierarchy
    parent_corpus_id: PydanticObjectId | None = None
    child_corpus_ids: list[PydanticObjectId] = Field(default_factory=list)
    is_master: bool = False

    # Vocabulary (external if large)
    vocabulary_size: int
    vocabulary_hash: str
    vocabulary: ContentLocation | None = None  # External storage for large vocabs

    # Statistics (external)
    word_frequencies: ContentLocation | None = None
    metadata_stats: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        data.setdefault("resource_type", ResourceType.CORPUS)
        data.setdefault("namespace", CacheNamespace.CORPUS)
        super().__init__(**data)
