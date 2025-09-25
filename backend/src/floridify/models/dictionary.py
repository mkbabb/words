"""Enhanced core data models for dictionary entries."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from ..text.normalize import lemmatize_comprehensive, normalize_basic
from .base import BaseMetadata, Language, ModelInfo
from .relationships import (
    Collocation,
    GrammarPattern,
    MeaningCluster,
    UsageNote,
    WordForm,
)


class DictionaryProvider(Enum):
    """Dictionary and data providers supported by the system."""

    WIKTIONARY = "wiktionary"
    OXFORD = "oxford"
    APPLE_DICTIONARY = "apple_dictionary"
    MERRIAM_WEBSTER = "merriam_webster"
    FREE_DICTIONARY = "free_dictionary"
    # DICTIONARY_COM removed - JavaScript-heavy site
    WORDHIPPO = "wordhippo"
    AI_FALLBACK = "ai_fallback"
    SYNTHESIS = "synthesis"

    @property
    def display_name(self) -> str:
        """Get human-readable display name for the provider."""
        display_names: dict[DictionaryProvider, str] = {
            DictionaryProvider.WIKTIONARY: "Wiktionary",
            DictionaryProvider.OXFORD: "Oxford Dictionary",
            DictionaryProvider.APPLE_DICTIONARY: "Apple Dictionary",
            DictionaryProvider.MERRIAM_WEBSTER: "Merriam-Webster",
            DictionaryProvider.FREE_DICTIONARY: "Free Dictionary",
            # DictionaryProvider.DICTIONARY_COM removed
            DictionaryProvider.WORDHIPPO: "WordHippo",
            DictionaryProvider.AI_FALLBACK: "AI Fallback",
            DictionaryProvider.SYNTHESIS: "Synthesis",
        }
        return display_names.get(self, self.value.title())


class Word(Document, BaseMetadata):
    """Core word entity."""

    text: str
    normalized: str = ""  # Will be auto-populated
    lemma: str = ""  # Will be auto-populated
    language: Language = Language.ENGLISH

    # Word forms and variations
    homograph_number: int | None = None  # For identical spellings

    def __init__(self, **data: Any) -> None:
        """Initialize Word with automatic normalization and lemmatization."""
        # If normalized not provided, compute it
        if "normalized" not in data or not data["normalized"]:
            data["normalized"] = normalize_basic(data.get("text", ""))
        # If lemma not provided, compute it
        if "lemma" not in data or not data["lemma"]:
            data["lemma"] = lemmatize_comprehensive(data.get("text", ""))

        super().__init__(**data)

    class Settings:
        name = "words"
        indexes = [
            [("text", 1), ("language", 1)],
            "normalized",
            "lemma",
            [("text", 1), ("homograph_number", 1)],
        ]


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
    model_info: ModelInfo | None = None  # If AI-generated

    class Settings:
        name = "pronunciations"


class LiteratureSourceExample(BaseModel):
    """Source ID for the piece of literature, and contextual information
    for where the example came from.
    """

    literature_id: PydanticObjectId  # FK to LiteratureSource document
    text_pos: int


class Example(Document, BaseMetadata):
    """Example storage with type discrimination."""

    definition_id: PydanticObjectId  # FK to Definition - optimized with ObjectId
    text: str
    type: Literal["generated", "literature"]

    # Generated example fields
    model_info: ModelInfo | None = None
    context: str | None = None  # User prompt/context for generated

    # Literature example fields
    source: LiteratureSourceExample | None = None

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


class Etymology(BaseModel):
    """Word origin information."""

    text: str  # e.g., "Latin 'florere' meaning 'to flower'"
    origin_language: str | None = None  # e.g., "Latin", "Greek"
    root_words: list[str] = Field(default_factory=list)
    first_known_use: str | None = None  # e.g., "14th century"
    model_info: ModelInfo | None = None  # If AI-generated


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
    frequency_band: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )  # 1-5, Oxford 3000/5000 style

    # Media and provenance
    image_ids: list[PydanticObjectId] = []  # FK to ImageMedia documents - optimized with ObjectIds
    dictionary_entry_id: PydanticObjectId | None = (
        None  # FK to DictionaryEntry - optimized with ObjectId
    )
    providers: list[DictionaryProvider] = []  # List of providers this definition is sourced from
    model_info: ModelInfo | None = None  # If AI-generated/synthesized

    class Settings:
        name = "definitions"
        indexes = ["word_id", "part_of_speech", [("word_id", 1), ("part_of_speech", 1)]]


class DictionaryEntry(Document, BaseMetadata):
    # Foreign keys to related entities
    word_id: PydanticObjectId  # FK to Word document
    definition_ids: list[PydanticObjectId] = Field(
        default_factory=list,
    )  # FK to Definition documents
    pronunciation_id: PydanticObjectId | None = None  # FK to Pronunciation document
    fact_ids: list[PydanticObjectId] = Field(default_factory=list)  # FK to Fact documents
    image_ids: list[PydanticObjectId] = Field(default_factory=list)  # FK to ImageMedia documents

    # Provider information
    provider: DictionaryProvider
    language: Language = Language.ENGLISH

    # Etymology and raw data
    etymology: Etymology | None = None
    raw_data: dict[str, Any] | None = None  # Original API response

    # Synthesis metadata (populated for synthesized entries)
    model_info: ModelInfo | None = None  # AI model info for synthesized entries


# Explicit exports
__all__ = [
    "Definition",
    "DictionaryEntry",
    "DictionaryProvider",
    "Example",
    "Fact",
    "LiteratureSourceExample",
    "Pronunciation",
    "Word",
]
