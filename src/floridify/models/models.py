"""Core data models for dictionary entries and related structures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from beanie import Document
from pydantic import BaseModel, Field

from .constants import WordType


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


class Definition(BaseModel):
    """Single word definition with bound synonyms and examples."""

    word_type: str

    definition: str

    synonyms: list[str] = Field(default_factory=list)

    examples: Examples = Field(default_factory=Examples)

    meaning_cluster: str | None = None

    raw_metadata: dict[str, Any] | None = None


class ProviderData(BaseModel):
    """Container for provider-specific definitions and metadata."""

    provider_name: str

    definitions: list[Definition] = Field(default_factory=list)

    last_updated: datetime = Field(default_factory=datetime.now)

    raw_metadata: dict[str, Any] | None = None


class DictionaryEntry(Document):
    """Main entry point for word data - organized by provider for layered access."""

    word: str

    pronunciation: Pronunciation

    provider_data: dict[str, ProviderData] = Field(default_factory=dict)

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
        self.provider_data[provider_data.provider_name] = provider_data
        self.last_updated = datetime.now()

    def get_providers_data_dict(self) -> dict[str, dict[str, list[str]]]:
        """Get all provider data as a nested dictionary:

        {provider_name: word_type -> [definition]}.
        """
        providers_data_dict: dict[str, dict[str, list[str]]] = {}

        for provider_name, provider_data in self.provider_data.items():
            providers_data_dict[provider_name] = {
                definition.word_type: [x.definition for x in provider_data.definitions]
                for definition in provider_data.definitions
            }

        return providers_data_dict


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
