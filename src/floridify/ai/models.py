"""AI-specific data models for Floridify."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..models import ProviderData, WordType


class ModelCapabilities(BaseModel):
    """Model capability detection for OpenAI models."""

    supports_reasoning: bool
    supports_temperature: bool
    supports_structured_output: bool


class AIProviderConfig(BaseModel):
    """Configuration for AI provider integration."""

    model_name: str
    temperature: float | None = None
    max_tokens: int = 1000
    capabilities: ModelCapabilities


class SynthesisRequest(BaseModel):
    """Request for definition synthesis."""

    word: str
    word_type: WordType
    provider_definitions: list[str]


class SynthesisResponse(BaseModel):
    """Response from definition synthesis."""

    synthesized_definition: str
    confidence: float
    sources_used: list[str]


class ExampleGenerationRequest(BaseModel):
    """Request for example generation."""

    word: str
    definition: str
    word_type: WordType


class ExampleGenerationResponse(BaseModel):
    """Response from example generation."""

    example_sentence: str
    confidence: float


class PronunciationRequest(BaseModel):
    """Request for pronunciation generation."""

    word: str


class PronunciationResponse(BaseModel):
    """Response from pronunciation generation."""

    phonetic: str
    ipa: str | None = None
    confidence: float


class FallbackRequest(BaseModel):
    """Request for AI fallback provider data."""

    word: str


class FallbackResponse(BaseModel):
    """Response from AI fallback provider."""

    provider_data: ProviderData | None
    confidence: float
    is_nonsense: bool = False


class EmbeddingRequest(BaseModel):
    """Request for text embeddings."""

    texts: list[str]
    model: str = "text-embedding-3-small"


class EmbeddingResponse(BaseModel):
    """Response from embedding generation."""

    embeddings: list[list[float]]
    usage: dict[str, Any]


class AIGeneratedProviderData(ProviderData):
    """AI fallback provider data with quality indicators."""

    confidence_score: float
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str