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

    synonyms: list[str] = Field(
        default_factory=list,
        description="List of synonyms for this definition, ordered by relevance and efflorescence.",
    )


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




class ClusterMapping(BaseModel):
    """A single cluster mapping entry."""
    
    cluster_id: str = Field(description="Unique cluster identifier (e.g., 'bank_financial')")
    cluster_description: str = Field(description="Human-readable description of this cluster")
    definition_indices: list[int] = Field(description="List of definition indices (0-based) in this cluster")


class ClusterMappingResponse(BaseModel):
    """Response containing numerical mapping of clusters to definition IDs."""

    word: str = Field(description="The word being analyzed")
    
    cluster_mappings: list[ClusterMapping] = Field(
        default_factory=list,
        description="List of cluster mappings with their descriptions and indices"
    )

    confidence: float = Field(description="Overall confidence in the clustering (0.0-1.0)")


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


class SynonymCandidate(BaseModel):
    """A single synonym candidate with relevance and efflorescence rating."""
    
    word: str = Field(description="The synonym word or phrase")
    language: str = Field(description="Language of origin (e.g., English, Latin, French)")
    relevance: float = Field(description="Relevance score (0.0 to 1.0)")
    efflorescence: float = Field(description="Beauty and expressive power score (0.0 to 1.0)")
    explanation: str = Field(description="Brief explanation of the relationship and why it's beautiful")


class SynonymGenerationResponse(BaseModel):
    """Response for synonym generation with efflorescence ranking."""
    
    synonyms: list[SynonymCandidate] = Field(
        description="List of synonyms ordered by relevance and efflorescence"
    )
    confidence: float = Field(description="Overall confidence in the synonym generation")


class AIGeneratedProviderData(ProviderData):
    """AI fallback provider data with quality indicators."""

    confidence_score: float
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str
