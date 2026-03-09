"""Shared AI models — cross-cutting response types not tied to a specific prompt category."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ....models.base import AIResponseBase
from ....models.dictionary import DictionaryProvider
from ..synthesize.models import DefinitionResponse, EtymologyResponse, PronunciationResponse


class TextGenerationRequest(BaseModel):
    """Request for text generation."""

    prompt: str = Field(description="The prompt for text generation")
    max_tokens: int = Field(default=500, description="Maximum tokens to generate")
    temperature: float = Field(default=0.7, description="Temperature for generation")


class TextGenerationResponse(AIResponseBase):
    """Response from text generation."""

    text: str = Field(description="Generated text content")


class AIGeneratedProviderData(BaseModel):
    """AI fallback provider data with quality indicators."""

    word: str
    provider: DictionaryProvider = DictionaryProvider.AI_FALLBACK
    definitions: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str


class EnhancedDefinitionResponse(AIResponseBase):
    """Complete enhanced definition with all fields."""

    model_config = ConfigDict(populate_by_field_name=True)

    definition: DefinitionResponse
    antonyms: list[str]
    language_register: str | None = Field(alias="register")
    domain: str | None
    regions: list[str]
    cefr_level: str | None
    frequency_band: int | None
    grammar_patterns: list[dict[str, str]]
    collocations: list[dict[str, str | float]]
    usage_notes: list[dict[str, str]]


class ComprehensiveSynthesisResponse(AIResponseBase):
    """Complete synthesis response with all components."""

    pronunciation: PronunciationResponse | None
    etymology: EtymologyResponse | None
    word_forms: list[dict[str, str]]
    definitions: list[EnhancedDefinitionResponse]
    facts: list[str]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    model_info: dict[str, Any]


# Rebuild models with forward references
EnhancedDefinitionResponse.model_rebuild()
