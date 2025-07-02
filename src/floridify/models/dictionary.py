"""Core data models for dictionary entries and related structures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from beanie import Document
from pydantic import BaseModel, ConfigDict, Field

from .constants import WordType


class Word(BaseModel):
    """Represents a word with its text and associated embeddings."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    text: str
    embedding: dict[str, np.ndarray] = Field(default_factory=dict)


class Pronunciation(BaseModel):
    """Pronunciation data in multiple formats."""

    phonetic: str  # e.g. "en coulisses -> on koo-LEES"
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


class SynonymReference(BaseModel):
    """Forward declaration for synonym references."""

    word: Word
    word_type: WordType


class Definition(BaseModel):
    """Single word definition with bound synonyms and examples."""

    word_type: WordType
    definition: str
    synonyms: list[SynonymReference] = Field(default_factory=list)
    examples: Examples = Field(default_factory=Examples)
    meaning_cluster: str | None = None  # AI-extracted meaning cluster ID
    raw_metadata: dict[str, Any] | None = None


class ProviderData(BaseModel):
    """Container for provider-specific definitions and metadata."""

    provider_name: str
    definitions: list[Definition] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    raw_metadata: dict[str, Any] | None = None


class DictionaryEntry(Document):
    """Main entry point for word data - organized by provider for layered access."""

    word: Word
    pronunciation: Pronunciation
    providers: dict[str, ProviderData] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],
            "last_updated",
        ]

    def add_provider_data(self, provider_data: ProviderData) -> None:
        """Add or update provider data."""
        self.providers[provider_data.provider_name] = provider_data
        self.last_updated = datetime.now()


class SynthesizedDictionaryEntry(Document):
    """Finalized dictionary entry with all necessary data for display.

    The definitions herein are synthetic, aggregated at the word-type-meaning level
    across providers.

    For example, a word like "run" may have multiple definitions across providers,
    but this entry synthesizes them into a single coherent structure for easy access.
    """

    word: Word
    pronunciation: Pronunciation
    definitions: list[Definition] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "synthesized_dictionary_entries"
        indexes = [
            "word.text",
            [("word.text", "text")],
            "last_updated",
        ]


class APIResponseCache(Document):
    """Cache for API responses with TTL."""

    word: str
    provider: str
    response_data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "api_response_cache"
        indexes = [
            [("word", 1), ("provider", 1)],
            "timestamp",
        ]
