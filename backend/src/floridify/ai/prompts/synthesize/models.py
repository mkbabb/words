"""Synthesis response models — colocated with synthesis prompt templates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....models.base import AIResponseBase
from ....models.dictionary import DictionaryProvider


class PronunciationResponse(AIResponseBase):
    """Response from pronunciation generation."""

    phonetic: str
    ipa: str


class DefinitionResponse(AIResponseBase):
    """Clean definition model for AI responses without numpy arrays."""

    part_of_speech: str = Field(
        description="Part of speech of the word (noun, verb, etc.).",
    )

    definition: str = Field(
        max_length=500,
        description="Definition of the word type.",
    )

    relevancy: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relevancy score for this definition within its meaning cluster (0.0-1.0, where 1.0 is most commonly used).",
    )

    source_providers: list[DictionaryProvider] = Field(
        default_factory=list,
        description="List of providers that contributed to this definition.",
    )


class DictionaryEntryResponse(AIResponseBase):
    """Response from AI dictionary synthesis."""

    definitions: list[DefinitionResponse] = Field(
        max_length=20,
        description="Comprehensive list of synthesized definitions with provider attribution.",
    )


class SynthesisResponse(AIResponseBase):
    """Response from definition synthesis."""

    definitions: list[DefinitionResponse] = Field(
        max_length=20,
        description="Comprehensive list of definitions for this word across all word types, each with their source providers.",
    )
    sources_used: list[str] = Field(
        description="List of all unique provider names used in the synthesis.",
    )


class SynonymCandidate(BaseModel):
    """A single synonym candidate with relevance and efflorescence rating."""

    word: str = Field(description="The synonym word or phrase")
    language: str = Field(description="Language of origin (e.g., English, Latin, French)")
    relevance: float = Field(description="Relevance score (0.0 to 1.0)")
    efflorescence: float = Field(description="Beauty and expressive power score (0.0 to 1.0)")
    explanation: str = Field(
        max_length=100,
        description="Brief explanation of the relationship and why it's beautiful",
    )


class SynonymGenerationResponse(AIResponseBase):
    """Response for synonym generation with efflorescence ranking."""

    synonyms: list[SynonymCandidate] = Field(
        max_length=15,
        description="List of synonyms ordered by relevance and efflorescence",
    )


class AntonymCandidate(BaseModel):
    """A single antonym candidate with relevance and efflorescence rating."""

    word: str = Field(description="The antonym word or phrase")
    language: str = Field(description="Language of origin (e.g., English, Latin, French)")
    relevance: float = Field(description="Relevance score (0.0 to 1.0)")
    efflorescence: float = Field(description="Beauty and expressive power score (0.0 to 1.0)")
    explanation: str = Field(
        max_length=100,
        description="Brief explanation of the semantic inversion",
    )


class AntonymResponse(AIResponseBase):
    """Response for antonym generation with efflorescence ranking."""

    antonyms: list[AntonymCandidate] = Field(
        max_length=10,
        description="List of antonyms ordered by relevance and efflorescence",
    )


class EtymologyResponse(AIResponseBase):
    """Response for etymology extraction."""

    text: str = Field(description="Etymology text explaining word origin")
    origin_language: str | None = Field(None, description="Language of origin")
    root_words: list[str] = Field(description="Root words or morphemes")
    first_known_use: str | None = Field(None, description="Date or period of first use")


class DeduplicatedDefinition(BaseModel):
    """A deduplicated definition with quality assessment."""

    part_of_speech: str = Field(description="Part of speech")
    definition: str = Field(description="The highest quality definition text")
    source_indices: list[int] = Field(description="Indices of merged definitions (0-based)")
    quality_score: float = Field(description="Quality score (0.0-1.0)")
    reasoning: str = Field(description="Brief explanation (max 10 words)")


class DeduplicationResponse(AIResponseBase):
    """Response from definition deduplication."""

    deduplicated_definitions: list[DeduplicatedDefinition] = Field(
        description="Deduplicated definitions preserving highest quality",
    )
    removed_count: int = Field(description="Number of duplicate definitions removed")


class DefinitionSynthesisResponse(AIResponseBase):
    """Response for definition text synthesis from clusters."""

    definition_text: str = Field(
        description="Synthesized definition text combining clustered meanings",
    )
    part_of_speech: str = Field(description="Part of speech for this definition cluster")
    sources_used: list[str] = Field(description="Provider sources used in synthesis")


# Rebuild models with forward references
SynthesisResponse.model_rebuild()
