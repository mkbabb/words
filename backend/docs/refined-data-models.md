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


class ImageMedia(Document, BaseMetadata):
    """Image media storage as separate collection."""
    url: str
    format: str  # png, jpg, webp
    size_bytes: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    alt_text: str | None = None
    word_id: str = Field(index=True)  # FK to Word
    
    class Settings:
        name = "image_media"
        indexes = ["word_id", "format"]


class AudioMedia(Document, BaseMetadata):
    """Audio media storage as separate collection."""
    url: str
    format: str  # mp3, wav, ogg
    size_bytes: int = Field(gt=0)
    duration_ms: int = Field(gt=0)
    accent: str | None = None  # us, uk, au
    quality: Literal["low", "standard", "high"] = "standard"
    word_id: str = Field(index=True)  # FK to Word
    
    class Settings:
        name = "audio_media"
        indexes = ["word_id", "accent"]


class Etymology(BaseModel):
    """Word origin information."""
    origin: str  # e.g., "Latin 'florere' meaning 'to flower'"
    first_known_use: str | None = None  # e.g., "14th century"
    context: str | None = None  # Additional context or notes


# Example Models

class LiteratureSource(BaseModel):
    """Source metadata for literature examples."""
    title: str
    author: str | None = None
    year: int | None = None
    context: str | None = None  # Additional surrounding text for context


# Meaning Cluster

class MeaningCluster(BaseModel):
    """Semantic grouping metadata."""
    id: str
    name: str  # Human-readable cluster name
    description: str  # Brief description of this meaning
    order: int = Field(ge=0)  # Display order
    relevance: float = Field(ge=0.0, le=1.0)  # Usage frequency


# Additional Models

class WordForm(BaseModel):
    """Word inflections and variations."""
    form_type: Literal["plural", "past", "past_participle", "present_participle", "comparative", "superlative", "variant"]
    text: str
    
    
class GrammarPattern(BaseModel):
    """Grammar patterns and verb frames."""
    pattern: str  # e.g., "[Tn]", "sb/sth"
    description: str | None = None
    

class Collocation(BaseModel):
    """Common word combinations."""
    text: str
    type: Literal["adjective", "verb", "noun", "adverb", "preposition"]
    frequency: float = Field(ge=0.0, le=1.0)


class UsageNote(BaseModel):
    """Usage guidance and warnings."""
    type: Literal["grammar", "confusion", "regional", "register", "error"]
    text: str
    

# Core Dictionary Models

class Pronunciation(Document, BaseMetadata):
    """Pronunciation with multi-format support."""
    word_id: str = Field(index=True)  # FK to Word
    phonetic: str  # e.g., "on koo-LEES"
    ipa_british: str | None = None  # British IPA
    ipa_american: str | None = None  # American IPA
    audio_file_ids: list[str] = []  # FK to AudioMedia documents
    syllables: list[str] = []
    stress_pattern: str | None = None  # Primary/secondary stress
    
    class Settings:
        name = "pronunciations"
        indexes = ["word_id"]


class Definition(Document, BaseMetadata):
    """Single definition with examples."""
    word_id: str = Field(index=True)  # FK to Word
    part_of_speech: str  # noun, verb, adjective, etc.
    text: str  # The definition text
    meaning_cluster: MeaningCluster
    sense_number: str | None = None  # e.g., "1a", "2b"
    
    # Examples and relationships
    example_ids: list[str] = []  # FK to Example documents
    synonyms: list[str] = []
    antonyms: list[str] = []
    
    # Usage and context
    register: Literal["formal", "informal", "neutral", "slang", "technical"] | None = None
    domain: str | None = None  # medical, legal, computing
    region: str | None = None  # US, UK, AU
    usage_notes: list[UsageNote] = []
    
    # Grammar and patterns
    grammar_patterns: list[GrammarPattern] = []
    collocations: list[Collocation] = []
    transitivity: Literal["transitive", "intransitive", "both"] | None = None
    
    # Educational metadata
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None
    frequency_band: int | None = None  # 1-5, Oxford 3000/5000 style
    
    # Media and provenance
    image_ids: list[str] = []  # FK to ImageMedia documents
    provider_data_id: str | None = None  # FK to ProviderData if from provider
    
    class Settings:
        name = "definitions"
        indexes = [
            "word_id",
            [("word_id", 1), ("meaning_cluster.order", 1)],
            [("word_id", 1), ("part_of_speech", 1)],
            "provider_data_id"
        ]


class Example(Document, BaseMetadata):
    """Example storage as separate collection."""
    definition_id: str = Field(index=True)  # FK to Definition
    text: str
    type: Literal["generated", "literature"]
    # Generated example fields
    model_info: ModelInfo | None = None
    context: str | None = None  # User prompt/context for generated
    # Literature example fields
    source: LiteratureSource | None = None
    
    class Settings:
        name = "examples"
        indexes = ["definition_id", "type"]


class Fact(Document, BaseMetadata):
    """Interesting fact about a word."""
    word_id: str = Field(index=True)  # FK to Word
    content: str
    category: Literal["etymology", "usage", "cultural", "linguistic", "historical"]
    model_info: ModelInfo | None = None  # If AI-generated
    source: str | None = None  # If from external source
    
    class Settings:
        name = "facts"
        indexes = ["word_id", "category"]


class PhrasalExpression(Document, BaseMetadata):
    """Phrasal verbs, idioms, and multi-word expressions."""
    base_word_id: str = Field(index=True)  # FK to main Word
    expression: str  # Full expression text
    type: Literal["phrasal_verb", "idiom", "colloquialism", "proverb"]
    definition_ids: list[str] = []  # FK to Definition documents
    separable: bool | None = None  # For phrasal verbs
    
    class Settings:
        name = "phrasal_expressions"
        indexes = ["base_word_id", "type", "expression"]


class ProviderData(Document, BaseMetadata):
    """Raw data from a dictionary provider."""
    word_id: str = Field(index=True)  # FK to Word
    provider: DictionaryProvider
    definition_ids: list[str] = []  # FK to Definition documents
    pronunciation_id: str | None = None  # FK to Pronunciation
    etymology: Etymology | None = None
    raw_data: dict | None = None  # Original API response
    
    class Settings:
        name = "provider_data"
        indexes = [
            "word_id",
            [("word_id", 1), ("provider", 1)],
            [("word_id", 1), ("updated_at", -1)]
        ]


class Word(Document, BaseMetadata):
    """Core word entity."""
    text: str = Field(index=True, unique=True)
    normalized: str = Field(index=True)  # Lowercase, no accents
    language: Language = Language.ENGLISH
    
    # Word forms and variations
    word_forms: list[WordForm] = []
    homograph_number: int | None = None  # For identical spellings
    
    # Metadata
    offensive_flag: bool = False
    first_known_use: str | None = None  # Historical dating
    
    class Settings:
        name = "words"
        indexes = [
            [("text", 1), ("language", 1)],
            "normalized",
            [("text", 1), ("homograph_number", 1)]
        ]


class SynthesizedDictionaryEntry(Document, BaseMetadata):
    """AI-synthesized entry with full provenance."""
    word_id: str = Field(index=True)  # FK to Word

    # Synthesized content references
    pronunciation_id: str | None = None  # FK to Pronunciation
    definition_ids: list[str] = []  # FK to Definition documents
    etymology: Etymology | None = None  # Embedded as it's lightweight
    fact_ids: list[str] = []  # FK to Fact documents

    # Synthesis metadata
    model_info: ModelInfo
    source_provider_data_ids: list[str] = []  # FK to ProviderData documents

    class Settings:
        name = "synthesized_dictionary_entries"
        indexes = [
            "word_id",
            [("word_id", 1), ("version", -1)],
            [("word_id", 1), ("model_info.generation_count", -1)],
            [("word_id", 1), ("accessed_at", -1)]
        ]


# Cross-Reference Models

class WordRelationship(Document):
    """Relationships between words."""
    from_word_id: str = Field(index=True)
    to_word_id: str = Field(index=True)
    relationship_type: Literal["synonym", "antonym", "related", "compare", "see_also", "derived_from"]
    strength: float = Field(ge=0.0, le=1.0, default=1.0)
    context: str | None = None
    
    class Settings:
        name = "word_relationships"
        indexes = [
            [("from_word_id", 1), ("relationship_type", 1)],
            [("to_word_id", 1), ("relationship_type", 1)]
        ]
```

## Model Enhancements Summary

Based on research of Merriam-Webster, Dictionary.com, and Oxford dictionaries, we've added:

1. **Part of Speech & Grammar**: Proper part_of_speech field, grammar patterns, transitivity
2. **Word Forms**: Inflections, variants, and morphological variations
3. **Educational Metadata**: CEFR levels, frequency bands for learners
4. **Usage Context**: Register, domain, region, and usage notes
5. **Pronunciations**: British/American variants, stress patterns
6. **Relationships**: Cross-references between related words
7. **Phrasal Expressions**: Support for idioms and phrasal verbs
8. **Collocations**: Common word combinations with frequency
9. **Temporal Data**: First known use dates
10. **Content Warnings**: Offensive content flagging
