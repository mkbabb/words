"""Enhanced core data models for dictionary entries."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from .base import BaseMetadata, Etymology, ModelInfo
from .relationships import (
    Collocation,
    GrammarPattern,
    MeaningCluster,
    UsageNote,
    WordForm,
)


class Language(Enum):
    """Supported languages with ISO codes."""

    ENGLISH = "en"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"


class DictionaryProvider(Enum):
    """Dictionary and data providers supported by the system."""

    WIKTIONARY = "wiktionary"
    OXFORD = "oxford"
    DICTIONARY_COM = "dictionary_com"
    APPLE_DICTIONARY = "apple_dictionary"
    AI_FALLBACK = "ai_fallback"
    SYNTHESIS = "synthesis"

    @property
    def display_name(self) -> str:
        """Get human-readable display name for the provider."""
        display_names: dict[DictionaryProvider, str] = {
            DictionaryProvider.WIKTIONARY: "Wiktionary",
            DictionaryProvider.OXFORD: "Oxford Dictionary",
            DictionaryProvider.DICTIONARY_COM: "Dictionary.com",
            DictionaryProvider.APPLE_DICTIONARY: "Apple Dictionary",
            DictionaryProvider.AI_FALLBACK: "AI Fallback",
            DictionaryProvider.SYNTHESIS: "Synthesis",
        }
        return display_names.get(self, self.value.title())


class OutputFormat(Enum):
    """Output formats for CLI commands and data export."""

    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    MD = "md"


class CorpusType(str, Enum):
    """Types of corpora in the system."""

    LANGUAGE_SEARCH = "language_search"  # Main search engine corpus
    WORDLIST = "wordlist"  # Individual wordlist corpus
    WORDLIST_NAMES = "wordlist_names"  # All wordlist names corpus
    CUSTOM = "custom"  # User-defined corpus


class LiteratureSourceType(Enum):
    """Enumeration for different types of literature sources."""

    BOOK = "book"
    ARTICLE = "article"
    DOCUMENT = "document"


class Pronunciation(Document, BaseMetadata):
    """Pronunciation with multi-format support."""

    word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    phonetic: str  # e.g., "on koo-LEES"
    ipa: str = ""  # American IPA - default to empty string for backwards compatibility
    audio_file_ids: list[
        PydanticObjectId
    ] = []  # FK to AudioMedia documents - optimized with ObjectIds
    syllables: list[str] = []
    stress_pattern: str | None = None  # Primary/secondary stress

    class Settings:
        name = "pronunciations"


class LiteratureSource(BaseModel):
    """Source metadata for literature examples."""

    title: str
    author: str | None = None
    year: int | None = None
    context: str | None = None  # Surrounding text for context


class Example(Document, BaseMetadata):
    """Example storage with type discrimination."""

    definition_id: PydanticObjectId  # FK to Definition - optimized with ObjectId
    text: str
    type: Literal["generated", "literature"]

    # Generated example fields
    model_info: ModelInfo | None = None
    context: str | None = None  # User prompt/context for generated

    # Literature example fields
    source: LiteratureSource | None = None

    class Settings:
        name = "examples"


class Fact(Document, BaseMetadata):
    """Interesting fact about a word."""

    word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    content: str
    category: Literal["etymology", "usage", "cultural", "linguistic", "historical"]
    model_info: ModelInfo | None = None  # If AI-generated
    source: str | None = None  # If from external source

    class Settings:
        name = "facts"


class Definition(Document, BaseMetadata):
    """Single definition with examples and comprehensive linguistic data."""

    word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    part_of_speech: str  # noun, verb, adjective, etc.
    text: str  # The definition text
    meaning_cluster: MeaningCluster | None = None
    sense_number: str | None = None  # e.g., "1a", "2b"
    word_forms: list[WordForm] = []  # List of WordForm objects

    # Examples and relationships
    example_ids: list[PydanticObjectId] = []  # FK to Example documents - optimized with ObjectIds
    synonyms: list[str] = []
    antonyms: list[str] = []

    # Usage and context
    language_register: Literal["formal", "informal", "neutral", "slang", "technical"] | None = None
    domain: str | None = None  # medical, legal, computing
    region: str | None = None  # US, UK, AU
    usage_notes: list[UsageNote] = []

    # Grammar and patterns
    grammar_patterns: list[GrammarPattern] = []
    collocations: list[Collocation] = []
    transitivity: Literal["transitive", "intransitive", "both"] | None = None

    # Educational metadata
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None
    frequency_band: int | None = Field(default=None, ge=1, le=5)  # 1-5, Oxford 3000/5000 style

    # Media and provenance
    image_ids: list[PydanticObjectId] = []  # FK to ImageMedia documents - optimized with ObjectIds
    provider_data_id: PydanticObjectId | None = (
        None  # FK to ProviderData if from provider - optimized with ObjectId
    )

    class Settings:
        name = "definitions"
        indexes = ["word_id", "part_of_speech", [("word_id", 1), ("part_of_speech", 1)]]


class ProviderData(Document, BaseMetadata):
    """Raw data from a dictionary provider."""

    word_id: PydanticObjectId  # FK to Word - optimized with ObjectId
    provider: DictionaryProvider
    definition_ids: list[
        PydanticObjectId
    ] = []  # FK to Definition documents - optimized with ObjectIds
    pronunciation_id: PydanticObjectId | None = (
        None  # FK to Pronunciation - optimized with ObjectId
    )
    etymology: Etymology | None = None
    raw_data: dict[str, Any] | None = None  # Original API response

    class Settings:
        name = "provider_data"
        indexes = ["word_id", "provider", [("word_id", 1), ("provider", 1)]]


class Word(Document, BaseMetadata):
    """Core word entity."""

    text: str
    normalized: str  # Lowercase, no accents
    language: Language = Language.ENGLISH

    # Word forms and variations
    homograph_number: int | None = None  # For identical spellings

    # Metadata
    offensive_flag: bool = False
    first_known_use: str | None = None  # Historical dating

    class Settings:
        name = "words"
        indexes = [
            [("text", 1), ("language", 1)],
            "normalized",
            [("text", 1), ("homograph_number", 1)],
        ]


class SynthesizedDictionaryEntry(Document, BaseMetadata):
    """AI-synthesized entry with full provenance."""

    word_id: PydanticObjectId  # FK to Word - optimized with ObjectId

    # Synthesized content references
    pronunciation_id: PydanticObjectId | None = (
        None  # FK to Pronunciation - optimized with ObjectId
    )
    definition_ids: list[
        PydanticObjectId
    ] = []  # FK to Definition documents - optimized with ObjectIds
    etymology: Etymology | None = None  # Embedded as it's lightweight
    fact_ids: list[PydanticObjectId] = []  # FK to Fact documents - optimized with ObjectIds
    image_ids: list[PydanticObjectId] = []  # FK to ImageMedia documents - optimized with ObjectIds

    # Synthesis metadata
    model_info: ModelInfo | None = None  # Optional for non-AI synthesized entries
    source_provider_data_ids: list[
        PydanticObjectId
    ] = []  # FK to ProviderData documents - optimized with ObjectIds

    # Access tracking
    accessed_at: datetime | None = None
    access_count: int = 0

    class Settings:
        name = "synthesized_dictionary_entries"
        indexes = [
            "word_id",
            [("word_id", 1), ("version", -1)],
            [("word_id", 1), ("model_info.generation_count", -1)],
            [("word_id", 1), ("accessed_at", -1)],
        ]
