"""Enhanced core data models for dictionary entries."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from beanie import Document
from pydantic import BaseModel, Field

from ..constants import DictionaryProvider, Language
from .base import BaseMetadata, Etymology, ModelInfo
from .relationships import (
    Collocation,
    GrammarPattern,
    MeaningCluster,
    UsageNote,
    WordForm,
)


class Pronunciation(Document, BaseMetadata):
    """Pronunciation with multi-format support."""

    word_id: str  # FK to Word
    phonetic: str  # e.g., "on koo-LEES"
    ipa_british: str | None = None  # British IPA
    ipa_american: str | None = None  # American IPA
    audio_file_ids: list[str] = []  # FK to AudioMedia documents
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

    definition_id: str  # FK to Definition
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

    word_id: str  # FK to Word
    content: str
    category: Literal["etymology", "usage", "cultural", "linguistic", "historical"]
    model_info: ModelInfo | None = None  # If AI-generated
    source: str | None = None  # If from external source

    class Settings:
        name = "facts"


class Definition(Document, BaseMetadata):
    """Single definition with examples and comprehensive linguistic data."""

    word_id: str  # FK to Word
    part_of_speech: str  # noun, verb, adjective, etc.
    text: str  # The definition text
    meaning_cluster: MeaningCluster | None = None
    sense_number: str | None = None  # e.g., "1a", "2b"
    word_forms: list[WordForm] = []  # List of WordForm objects

    # Examples and relationships
    example_ids: list[str] = []  # FK to Example documents
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
    image_ids: list[str] = []  # FK to ImageMedia documents
    provider_data_id: str | None = None  # FK to ProviderData if from provider

    class Settings:
        name = "definitions"
        indexes = ["word_id", "part_of_speech", [("word_id", 1), ("part_of_speech", 1)]]


class ProviderData(Document, BaseMetadata):
    """Raw data from a dictionary provider."""

    word_id: str  # FK to Word
    provider: DictionaryProvider
    definition_ids: list[str] = []  # FK to Definition documents
    pronunciation_id: str | None = None  # FK to Pronunciation
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

    word_id: str  # FK to Word

    # Synthesized content references
    pronunciation_id: str | None = None  # FK to Pronunciation
    definition_ids: list[str] = []  # FK to Definition documents
    etymology: Etymology | None = None  # Embedded as it's lightweight
    fact_ids: list[str] = []  # FK to Fact documents

    # Synthesis metadata
    model_info: ModelInfo
    source_provider_data_ids: list[str] = []  # FK to ProviderData documents

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
