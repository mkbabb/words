"""Literature provider models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field

from ...caching.models import BaseVersionedData, ResourceType
from ...models.base import Language
from ...models.literature import AuthorInfo, Genre, LiteratureProvider, Period
from ...models.versioned import register_model


class ScraperType(Enum):
    """Available scrapers for literature data."""

    GUTENBERG = "scrape_gutenberg"
    ARCHIVE_ORG = "scrape_archive_org"
    WIKISOURCE = "scrape_wikisource"
    DEFAULT = "default_scraper"


class ParserType(Enum):
    """Available parsers for literature text."""

    PLAIN_TEXT = "parse_text"
    MARKDOWN = "parse_markdown"
    HTML = "parse_html"
    EPUB = "parse_epub"
    PDF = "parse_pdf"
    CUSTOM = "custom"


class LiteratureSource(BaseModel):
    """Configuration for a literature source."""

    name: str
    url: str = ""
    parser: ParserType = Field(default=ParserType.PLAIN_TEXT, description="Parser type for text")
    author: AuthorInfo | None = None
    genre: Genre | None = None
    period: Period | None = None
    language: Language = Language.ENGLISH
    description: str = ""
    scraper: ScraperType | None = Field(default=None, description="Optional scraper type")

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


class LiteratureEntry(BaseModel):
    """In-memory representation of a literary work with composed source."""

    # Composed source configuration
    source: LiteratureSource = Field(..., description="Literature source configuration")

    # Core identification
    title: str = Field(..., description="Title of the work")
    author: AuthorInfo = Field(..., description="Author information")

    # External IDs
    work_id: str | None = Field(None, description="Provider-specific work ID")
    gutenberg_id: str | None = Field(None, description="Project Gutenberg ID")

    # Additional metadata
    year: int | None = Field(None, description="Year of publication")
    subtitle: str | None = Field(None, description="Subtitle if any")
    description: str | None = Field(None, description="Work description")
    keywords: list[str] = Field(default_factory=list, description="Keywords/tags")

    # Vocabulary data
    extracted_vocabulary: list[str] = Field(
        default_factory=list, description="Extracted vocabulary"
    )

    # Content
    text: str | None = Field(None, description="Full text content (loaded separately)")

    # Additional runtime data
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def vocabulary_count(self) -> int:
        """Number of unique vocabulary items."""
        return len(self.extracted_vocabulary)

    @property
    def genre(self) -> Genre | None:
        """Get genre from source."""
        return self.source.genre

    @property
    def period(self) -> Period | None:
        """Get period from source."""
        return self.source.period

    @property
    def language(self) -> Language:
        """Get language from source."""
        return self.source.language

    model_config = {"arbitrary_types_allowed": True}

    @register_model(ResourceType.LITERATURE)
    class Metadata(BaseVersionedData, Document):
        """Minimal literature metadata for versioning."""

        provider: LiteratureProvider | None = None
        work_id: str | None = None

        class Settings:
            """Beanie settings."""

            name = "literature_entry_metadata"
            indexes = ["provider", "work_id"]
