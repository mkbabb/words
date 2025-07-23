# Refined Data Models - Floridify Dictionary

```python
from datetime import datetime
from typing import Literal

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from floridify.constants import Language, DictionaryProvider


# Base Models

class BaseMetadata(BaseModel):
    """Standard metadata for entities requiring CRUD tracking."""
    id: str = Field(default_factory=lambda: str(PydanticObjectId()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime | None = None  # Last access time
    access_count: int = 0  # Number of times accessed
    version: int = Field(default=1, ge=1)


class ModelInfo(BaseModel):
    """AI model metadata for synthesized content."""
    model: str  # e.g., "gpt-4o", "gpt-3.5-turbo"
    confidence: float = Field(ge=0.0, le=1.0)
    temperature: float = Field(ge=0.0, le=2.0, default=0.7)
    generation_count: int = Field(default=1, ge=1)  # Times regenerated
    last_generated: datetime = Field(default_factory=datetime.utcnow)


class ImageMedia(BaseMetadata):
    """Image media storage."""
    url: str
    format: str  # png, jpg, webp
    size_bytes: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    alt_text: str | None = None


class AudioMedia(BaseMetadata):
    """Audio media storage."""
    url: str
    format: str  # mp3, wav, ogg
    size_bytes: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    accent: str | None = None  # us, uk, au
    quality: Literal["low", "standard", "high"] = "standard"


class Etymology(BaseModel):
    """Word origin information."""
    origin: str  # e.g., "Latin 'florere' meaning 'to flower'"
    first_use: str | None = None  # e.g., "14th century"
    context: str | None = None  # Additional context or notes


# Example Models

class BaseExample(BaseModel):
    """Base model for examples."""
    text: str

class LiteratureSource(BaseModel):
    """Source metadata for literature examples."""
    title: str
    author: str | None = None
    year: int | None = None
    context: str | None = None  # Additional surrounding text for context


class GeneratedExample(BaseExample):
    """AI-generated example."""
    type: Literal["generated"] = "generated"
    model_info: ModelInfo
    context: str | None = None  # Optional user prompt/context


class LiteratureExample(BaseExample):
    """Real-world example from literature."""
    source: LiteratureSource


Example = BaseExample | GeneratedExample | LiteratureExample  # Union type


# Meaning Cluster

class MeaningCluster(BaseModel):
    """Semantic grouping metadata."""
    id: str
    name: str  # Human-readable cluster name
    description: str  # Brief description of this meaning
    order: int = Field(ge=0)  # Display order
    relevance: float = Field(ge=0.0, le=1.0)  # Usage frequency


# Core Dictionary Models

class Pronunciation(BaseMetadata):
    """Pronunciation with multi-format support."""
    phonetic: str  # e.g., "on koo-LEES"
    ipa: str | None = None  # e.g., "/ɑːn kəˈliːs/"
    audio_files: list[AudioMedia] = []
    syllables: list[str] = []


class Definition(BaseMetadata):
    """Single definition with examples."""
    word_id: str  # FK to Word
    word_type: str  # noun, verb, adjective, etc.
    text: str  # The definition text
    meaning_cluster: MeaningCluster
    examples: list[Example] = []
    synonyms: list[str] = []
    antonyms: list[str] = []
    usage_notes: str | None = None
    register: str | None = None  # formal, informal, slang
    domain: str | None = None  # medical, legal, computing
    images: list[ImageMedia] = []
    provider_id: str | None = None  # FK to ProviderData if from provider


class Fact(BaseMetadata):
    """Interesting fact about a word."""
    content: str
    category: Literal["etymology", "usage", "cultural", "linguistic", "historical"]
    model_info: ModelInfo | None = None  # If AI-generated
    source: str | None = None  # If from external source


class DictionaryEntry(BaseMetadata):
    """Raw data from a dictionary provider."""
    word_id: str  # FK to Word
    provider: DictionaryProvider
    dictionary_entry_id: str  # FK to DictionaryEntry
    definitions: list[Definition] = []
    pronunciation: Pronunciation | None = None
    etymology: Etymology | None = None
    raw_data: dict | None = None  # Original API response


class Word(BaseMetadata):
    """Core word entity."""
    text: str = Field(index=True, unique=True)
    normalized: str = Field(index=True)  # Lowercase, no accents
    language: Language = Language.ENGLISH

    class Settings:
        name = "words"
        indexes = [
            [("text", 1), ("language", 1)],
            "normalized"
        ]



class SynthesizedDictionaryEntry(BaseMetadata):
    """AI-synthesized entry with full provenance."""
    word_id: str = Field(index=True)  # FK to Word

    # Synthesized content
    pronunciation: Pronunciation
    definitions: list[Definition] = []
    etymology: Etymology | None = None
    facts: list[Fact] = []

    # Synthesis metadata
    model_info: ModelInfo
    source_entry_ids: list[str] = []  # Contributing entry IDs

    class Settings:
        name = "synthesized_dictionary_entries"
        indexes = [
            "word_id",
            [("word_id", 1), ("version", -1)],
            [("word_id", 1), ("model_info.generation_count", -1)],
            [("word_id", 1), ("accessed_at", -1)]
        ]
```
