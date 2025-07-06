"""AI-specific data models for Floridify."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..models import ProviderData


class ExampleGenerationResponse(BaseModel):
    """Response from example generation."""

    example_sentences: list[str] = Field(
        default_factory=list,
        description="List of example sentences generated for the word.",
    )
    confidence: float


class PronunciationResponse(BaseModel):
    """Response from pronunciation generation."""

    phonetic: str
    ipa: str | None = None
    confidence: float


class DefinitionResponse(BaseModel):
    """Clean definition model for AI responses without numpy arrays."""

    word_type: str = Field(
        description="Type of the word (noun, verb, etc.).",
    )

    definition: str = Field(
        description="Definition of the word type.",
    )

    synonyms: list[str] = Field(default_factory=list)


class ProviderDataResponse(BaseModel):
    """Clean definition model for AI responses without numpy arrays."""

    definitions: list[DefinitionResponse] = Field(
        default_factory=list,
        description="Comprehensive list of definitions for this word across all word types.",
    )


class DictionaryEntryResponse(BaseModel):
    """Response from AI fallback provider."""

    provider_data: ProviderDataResponse | None

    confidence: float


class MeaningClusterDefinition(BaseModel):
    """A definition item within a meaning cluster."""

    provider: str = Field(description="The dictionary provider")
    word_type: str = Field(description="The word type (noun, verb, etc.)")
    definition: str = Field(description="The definition text")


class MeaningCluster(BaseModel):
    """A distinct meaning/sense of a word with associated word types."""

    meaning_cluster: str = Field(
        description="""Unique identifier for this meaning cluster, typically a combination of word and context,
        e.g., 'bank_financial', 'bank_geographic', 'bank_arrangement'""",
    )

    core_meaning: str = Field(
        description="Brief description of this meaning cluster",
    )

    definitions: list[MeaningClusterDefinition] = Field(
        default_factory=list,
        description="List of definitions for this meaning cluster",
    )

    confidence: float = 0.0


class MeaningClusterResponse(BaseModel):
    """Response containing distinct meaning clusters for a word."""

    word: str

    meaning_clusters: list[MeaningCluster]

    confidence: float


class SynthesisResponse(BaseModel):
    """Response from definition synthesis."""

    definitions: list[DefinitionResponse] = Field(
        default_factory=list,
        description="Comprehensive list of definitions for this word across all word types.",
    )
    confidence: float
    sources_used: list[str]


class AnkiFillBlankResponse(BaseModel):
    """Response for fill-in-the-blank flashcard generation."""

    sentence: str = Field(description="Sentence with _____ where the word belongs")
    hint: str | None = Field(
        default=None, description="Optional hint about context or meaning"
    )


class AnkiMultipleChoiceResponse(BaseModel):
    """Response for multiple choice flashcard generation."""

    choice_a: str = Field(description="First answer choice")
    choice_b: str = Field(description="Second answer choice")
    choice_c: str = Field(description="Third answer choice")
    choice_d: str = Field(description="Fourth answer choice")
    correct_choice: str = Field(description="Letter of correct answer (A, B, C, or D)")


class AIGeneratedProviderData(ProviderData):
    """AI fallback provider data with quality indicators."""

    confidence_score: float
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str
