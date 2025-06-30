"""Pydantic schemas for structured AI responses."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class WordTypeEnum(str, Enum):
    """Word types for definitions."""

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"
    PRONOUN = "pronoun"
    DETERMINER = "determiner"
    PHRASE = "phrase"
    OTHER = "other"


class AIDefinition(BaseModel):
    """Structured AI definition response."""

    model_config = {"extra": "forbid"}

    word_type: WordTypeEnum
    definition: str


class DefinitionSynthesisResponse(BaseModel):
    """Complete structured response for definition synthesis."""

    model_config = {"extra": "forbid"}

    definitions: list[AIDefinition]


class ExampleSentence(BaseModel):
    """A generated example sentence."""

    model_config = {"extra": "forbid"}

    sentence: str


class ExampleGenerationResponse(BaseModel):
    """Structured response for example generation."""

    model_config = {"extra": "forbid"}

    examples: list[ExampleSentence]


class ModelCapabilities(BaseModel):
    """Capabilities and constraints for different model types."""

    supports_temperature: bool = Field(
        default=True, description="Whether model supports temperature parameter"
    )
    supports_max_tokens: bool = Field(
        default=True, description="Whether model supports max_tokens parameter"
    )
    supports_structured_outputs: bool = Field(
        default=True, description="Whether model supports structured outputs"
    )
    uses_reasoning_effort: bool = Field(
        default=False, description="Whether model uses reasoning_effort parameter"
    )
    default_reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None, description="Default reasoning effort"
    )


# Model capability registry
MODEL_CAPABILITIES: dict[str, ModelCapabilities] = {
    # Reasoning models (o-series)
    "o3": ModelCapabilities(
        supports_temperature=False,
        supports_max_tokens=False,  # Uses max_completion_tokens instead
        supports_structured_outputs=True,
        uses_reasoning_effort=True,
        default_reasoning_effort="high",
    ),
    "o3-mini": ModelCapabilities(
        supports_temperature=False,
        supports_max_tokens=False,
        supports_structured_outputs=True,
        uses_reasoning_effort=True,
        default_reasoning_effort="medium",
    ),
    "o1": ModelCapabilities(
        supports_temperature=False,
        supports_max_tokens=False,
        supports_structured_outputs=True,
        uses_reasoning_effort=True,
        default_reasoning_effort="medium",
    ),
    "o1-mini": ModelCapabilities(
        supports_temperature=False,
        supports_max_tokens=False,
        supports_structured_outputs=True,
        uses_reasoning_effort=True,
        default_reasoning_effort="low",
    ),
    # Standard chat models
    "gpt-4": ModelCapabilities(),
    "gpt-4o": ModelCapabilities(),
    "gpt-4o-mini": ModelCapabilities(),
    "gpt-4-turbo": ModelCapabilities(),
    "gpt-3.5-turbo": ModelCapabilities(),
}


def get_model_capabilities(model_name: str) -> ModelCapabilities:
    """Get capabilities for a specific model.

    Args:
        model_name: Name of the model

    Returns:
        ModelCapabilities object
    """
    # Check for exact match first
    if model_name in MODEL_CAPABILITIES:
        return MODEL_CAPABILITIES[model_name]

    # Check for prefix match (e.g., "o3-2024-12-01" -> "o3")
    for prefix, capabilities in MODEL_CAPABILITIES.items():
        if model_name.startswith(prefix):
            return capabilities

    # Default to standard model capabilities
    return ModelCapabilities()


def is_reasoning_model(model_name: str) -> bool:
    """Check if a model is a reasoning model (o-series).

    Args:
        model_name: Name of the model

    Returns:
        True if reasoning model, False otherwise
    """
    return get_model_capabilities(model_name).uses_reasoning_effort
