"""Core data models for dictionary entries and related structures."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field


class WordType(Enum):
    """Enumeration for part of speech types."""

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"


class LiteratureSourceType(Enum):
    """Enumeration for different types of literature sources."""

    BOOK = "book"
    ARTICLE = "article"
    DOCUMENT = "document"


class Word(BaseModel):
    """Represents a word with its text and associated embeddings."""

    text: str
    embedding: dict[str, list[float]] = Field(default_factory=dict)


class Pronunciation(BaseModel):
    """Pronunciation data in multiple formats."""

    phonetic: str
    ipa: str | None = None


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
    raw_metadata: dict[str, Any] | None = None


class ProviderData(BaseModel):
    """Container for provider-specific definitions and metadata."""

    provider_name: str
    definitions: list[Definition] = Field(default_factory=list)
    is_synthetic: bool = False
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
