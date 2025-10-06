"""Literature provider models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ...caching.models import BaseVersionedData, CacheNamespace, ResourceType
from ...models.base import Language
from ...models.literature import AuthorInfo, Genre, LiteratureProvider, Period


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

    # Core identification (required fields)
    title: str = Field(description="Title of the work")
    author: AuthorInfo = Field(description="Author information")

    # Composed source configuration (optional for backward compatibility)
    source: LiteratureSource | None = Field(
        default=None,
        description="Literature source configuration",
    )

    # External IDs (all optional)
    work_id: str | None = Field(default=None, description="Provider-specific work ID")
    gutenberg_id: str | None = Field(default=None, description="Project Gutenberg ID")

    # Additional metadata (all optional)
    year: int | None = Field(default=None, description="Year of publication")
    subtitle: str | None = Field(default=None, description="Subtitle if any")
    description: str | None = Field(default=None, description="Work description")
    keywords: list[str] = Field(default_factory=list, description="Keywords/tags")

    # Direct genre/period/language fields for backward compatibility
    genre: Genre | None = Field(default=None, description="Genre of the work")
    period: Period | None = Field(default=None, description="Historical period")
    language: Language = Field(default=Language.ENGLISH, description="Language of the work")

    # Vocabulary data
    extracted_vocabulary: list[str] = Field(
        default_factory=list,
        description="Extracted vocabulary",
    )

    # Content (optional)
    text: str | None = Field(default=None, description="Full text content (loaded separately)")

    # Additional runtime data
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def vocabulary_count(self) -> int:
        """Number of unique vocabulary items."""
        return len(self.extracted_vocabulary)

    def get_genre(self) -> Genre | None:
        """Get genre from source or direct field."""
        return self.source.genre if self.source else self.genre

    def get_period(self) -> Period | None:
        """Get period from source or direct field."""
        return self.source.period if self.source else self.period

    def get_language(self) -> Language:
        """Get language from source or direct field."""
        return self.source.language if self.source else self.language

    model_config = {"arbitrary_types_allowed": True}

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.LITERATURE,
        default_namespace=CacheNamespace.LITERATURE,
    ):
        """Minimal literature metadata for versioning."""

        provider: LiteratureProvider | None = None
        work_id: str | None = None

        class Settings:
            """Beanie settings."""

            name = "literature_entry_metadata"
            indexes = ["provider", "work_id"]
