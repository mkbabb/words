"""AI provider configuration models.

Ported from dns-analysis AI connector system. Supports OpenAI and Anthropic
providers with unified effort levels and per-provider configuration.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field


class Provider(str, Enum):
    """AI provider enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"

    def __str__(self) -> str:
        return self.value


class OpenAIEffort(str, Enum):
    """OpenAI effort levels for reasoning models."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __str__(self) -> str:
        return self.value


class AnthropicEffort(str, Enum):
    """Anthropic effort levels for structured outputs."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __str__(self) -> str:
        return self.value


Effort = OpenAIEffort | AnthropicEffort


def _parse_effort(v: str | Effort) -> Effort:
    """Parse effort string to appropriate enum."""
    if isinstance(v, (OpenAIEffort, AnthropicEffort)):
        return v
    if isinstance(v, str):
        try:
            return OpenAIEffort(v)
        except ValueError:
            pass
        try:
            return AnthropicEffort(v)
        except ValueError:
            pass
        raise ValueError(f"Invalid effort: {v}. Valid: minimal, low, medium, high")
    raise ValueError(f"Invalid effort type: {type(v)}")


ParsedEffort = Annotated[Effort, BeforeValidator(_parse_effort)]


class AIConfig(BaseModel):
    """Shared AI configuration."""

    max_concurrent_requests: int = Field(default=10, ge=1)
    effort: ParsedEffort = OpenAIEffort.MEDIUM
    enable_tournament: bool = Field(
        default=True, description="Enable tournament/ranker for high-complexity tasks"
    )
    tournament_n: int = Field(default=3, ge=2, le=8, description="Number of tournament candidates")


class AIProviderConfig(BaseModel):
    """Per-component AI provider override configuration."""

    provider: Provider = Provider.OPENAI
    model: str | None = None
    effort: ParsedEffort | None = None
    max_completion_tokens: int | None = None
    max_tokens: int | None = None


__all__ = [
    "AIConfig",
    "AIProviderConfig",
    "AnthropicEffort",
    "Effort",
    "OpenAIEffort",
    "ParsedEffort",
    "Provider",
]
