from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from ..models.base import Language


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
