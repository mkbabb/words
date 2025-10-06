"""Language provider models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ...caching.models import BaseVersionedData, CacheNamespace, ResourceType
from ...models.base import Language


class ScraperType(Enum):
    """Available scrapers for language data."""

    DEFAULT = "default_scraper"
    FRENCH_EXPRESSIONS = "scrape_french_expressions"


class ParserType(Enum):
    """Available parsers for language data."""

    TEXT_LINES = "parse_text_lines"
    JSON_VOCABULARY = "parse_json_vocabulary"
    CSV_WORDS = "parse_csv_words"
    CUSTOM = "custom"


class LanguageProvider(Enum):
    """Language provider sources."""

    # For now, only custom URL provider
    CUSTOM_URL = "custom_url"

    @property
    def display_name(self) -> str:
        """Get human-readable display name for the provider."""
        display_names: dict[LanguageProvider, str] = {
            LanguageProvider.CUSTOM_URL: "Custom URL Source",
        }
        return display_names.get(self, self.value.replace("_", " ").title())


class LanguageSource(BaseModel):
    """Configuration for a language corpus source."""

    name: str = Field(..., description="Unique identifier for the source")
    url: str = Field(default="", description="URL to download the corpus data")
    parser: ParserType = Field(
        default=ParserType.TEXT_LINES,
        description="Parser type for raw data",
    )
    language: Language = Field(..., description="Language of the corpus")
    description: str = Field(default="", description="Human-readable description")
    scraper: ScraperType | None = Field(
        default=None,
        description="Optional custom scraper type",
    )

    model_config = {"frozen": True, "arbitrary_types_allowed": True}


class LanguageEntry(BaseModel):
    """In-memory representation of a language corpus collection with composed source."""

    # Composed source configuration
    provider: LanguageProvider
    source: LanguageSource = Field(..., description="Language source configuration")

    # Vocabulary collection
    vocabulary: list[str] = Field(default_factory=list, description="List of words/phrases")

    # Optional categorization
    phrases: list[str] = Field(default_factory=list, description="Extracted phrases")
    idioms: list[str] = Field(default_factory=list, description="Extracted idioms")

    # Additional runtime data
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @property
    def vocabulary_count(self) -> int:
        """Number of vocabulary items."""
        return len(self.vocabulary)

    @property
    def phrase_count(self) -> int:
        """Number of phrases."""
        return len(self.phrases)

    @property
    def idiom_count(self) -> int:
        """Number of idioms."""
        return len(self.idioms)

    model_config = {"arbitrary_types_allowed": True}

    class Metadata(
        BaseVersionedData,
        default_resource_type=ResourceType.LANGUAGE,
        default_namespace=CacheNamespace.LANGUAGE,
    ):
        """Minimal language metadata for versioning."""

        class Settings:
            """Beanie settings."""

            name = "language_entry_metadata"
            indexes = ["provider"]
