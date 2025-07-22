"""Core data models for dictionary entries and related structures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field


class Pronunciation(BaseModel):
    """Pronunciation data in multiple formats."""

    phonetic: str = ""  # e.g. "en coulisses -> on koo-LEES"
    ipa: str | None = None  # e.g. "/ɑːn kəˈliːs/"


class LiteratureSource(BaseModel):
    """Metadata for literature sources."""

    id: str
    title: str
    author: str | None = None
    text: str = ""


class GeneratedExample(BaseModel):
    """AI-generated modern usage example."""

    sentence: str
    regenerable: bool = True


class LiteratureExample(BaseModel):
    """Real-world usage from literature knowledge base."""

    sentence: str
    source: LiteratureSource


class Examples(BaseModel):
    """Container for different types of usage examples."""

    generated: list[GeneratedExample] = Field(default_factory=list)
    literature: list[LiteratureExample] = Field(default_factory=list)


class Fact(BaseModel):
    """Interesting fact about a word."""

    content: str = Field(description="The fact content")
    category: str = Field(
        description="Category of fact (etymology, usage, cultural, etc.)"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in fact accuracy")
    generated_at: datetime = Field(default_factory=datetime.now)


class Definition(BaseModel):
    """Single word definition with bound synonyms and examples."""

    word_type: str
    definition: str
    synonyms: list[str] = Field(default_factory=list)
    examples: Examples = Field(default_factory=Examples)
    meaning_cluster: str | None = None
    raw_metadata: dict[str, Any] | None = None

    # Enhanced metadata for comprehensive tracking
    created_at: datetime = Field(
        default_factory=datetime.now, description="When definition was created"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last modification time"
    )
    accessed_at: datetime | None = Field(None, description="Last access time")
    created_by: str | None = Field(
        None, description="Creator attribution (ai-synthesis, user-edit, provider-sync)"
    )
    updated_by: str | None = Field(None, description="Last modifier attribution")
    source_attribution: str | None = Field(
        None, description="AI model or provider source (gpt-4, oxford-api, etc.)"
    )
    version: int = Field(1, ge=1, description="Version number for change tracking")
    quality_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Quality/confidence score"
    )
    relevancy: float | None = Field(
        None, ge=0.0, le=1.0, description="Relevancy score for meaning cluster ordering"
    )
    validation_status: str | None = Field(
        None, description="Validation state (pending, verified, flagged)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible metadata"
    )


class ProviderData(BaseModel):
    """Container for provider-specific definitions and metadata."""

    provider_name: str
    definitions: list[Definition] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    raw_metadata: dict[str, Any] | None = None

    # Enhanced metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When provider data was first created"
    )
    accessed_at: datetime | None = Field(
        None, description="Last access time for provider data"
    )
    version: int = Field(1, ge=1, description="Provider data version")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible provider metadata"
    )


class DictionaryEntry(Document):
    """Main entry point for word data - organized by provider for layered access."""

    word: str
    pronunciation: Pronunciation
    provider_data: dict[str, ProviderData] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

    # Enhanced metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When entry was first created"
    )
    accessed_at: datetime | None = Field(None, description="Last access time")
    quality: float | None = Field(
        None, ge=0.0, le=1.0, description="Overall entry quality score"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible entry metadata"
    )

    class Settings:
        name = "dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],
            "last_updated",
            "created_at",
            "accessed_at",
            "lookup_count",
            "status",
        ]


class SynthesizedDictionaryEntry(Document):
    """Finalized dictionary entry with all necessary data for display.

    The definitions herein are synthetic, aggregated at the word-type-meaning level
    across providers.

    For example, a word like "run" may have multiple definitions across providers,
    but this entry synthesizes them into a single coherent structure for easy access.
    """

    word: str
    pronunciation: Pronunciation
    definitions: list[Definition] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    provider_data: dict[str, ProviderData] = Field(default_factory=dict)

    # Enhanced metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When synthesized entry was created"
    )
    accessed_at: datetime | None = Field(None, description="Last access time")
    model: str | None = Field(
        None, description="AI model used for synthesis (e.g., gpt-4o)"
    )
    confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Overall synthesis confidence score"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible synthesis metadata"
    )

    class Settings:
        name = "synthesized_dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],
            "last_updated",
            "created_at",
            "accessed_at",
            "lookup_count",
            "status",
            "synthesis_quality",
        ]
