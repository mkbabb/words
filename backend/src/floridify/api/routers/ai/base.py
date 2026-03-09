"""Shared base for AI router endpoints: error decorator and request models."""

import functools
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field

from ....utils.logging import get_logger

logger = get_logger(__name__)


def handle_ai_errors(func: Callable) -> Callable:
    """Decorator that maps OpenAI errors to appropriate HTTP status codes.

    - RateLimitError -> 429
    - APITimeoutError, APIConnectionError -> 502
    - AuthenticationError -> 500 (our config issue, not user's)
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            raise  # Already handled
        except RateLimitError as e:
            raise HTTPException(
                status_code=429,
                detail=f"AI provider rate limit exceeded: {e}",
            )
        except (APITimeoutError, APIConnectionError) as e:
            logger.error(f"AI provider unavailable: {e}")
            raise HTTPException(
                status_code=502,
                detail="AI provider temporarily unavailable",
            )
        except AuthenticationError:
            logger.error("OpenAI authentication failed - check API key")
            raise HTTPException(
                status_code=500,
                detail="AI service configuration error",
            )
        except Exception as e:
            logger.error(f"Unexpected AI error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"AI processing error: {type(e).__name__}",
            )

    return wrapper


# Request Models for Pure Generation Functions
class PronunciationRequest(BaseModel):
    """Request for pronunciation generation."""

    word: str = Field(..., min_length=1, max_length=100)


class SuggestionsRequest(BaseModel):
    """Request for vocabulary suggestions."""

    input_words: list[str] | None = Field(None, max_length=10)
    count: int = Field(10, ge=4, le=12)


class WordFormsRequest(BaseModel):
    """Request for word forms generation."""

    word: str = Field(..., min_length=1, max_length=100)
    part_of_speech: str = Field(..., min_length=1, max_length=50)


class FrequencyAssessmentRequest(BaseModel):
    """Request for frequency band assessment."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)


class CEFRAssessmentRequest(BaseModel):
    """Request for CEFR level assessment."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)


# Request Models for Definition-Dependent Functions
class SynonymRequest(BaseModel):
    """Request for synonym generation."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)
    part_of_speech: str = Field(..., min_length=1, max_length=50)
    existing_synonyms: list[str] = Field(default_factory=list, max_length=20)
    count: int = Field(10, ge=1, le=20)


class AntonymRequest(BaseModel):
    """Request for antonym generation."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)
    part_of_speech: str = Field(..., min_length=1, max_length=50)
    existing_antonyms: list[str] = Field(default_factory=list, max_length=20)
    count: int = Field(5, ge=1, le=10)


class ExampleRequest(BaseModel):
    """Request for example generation."""

    word: str = Field(..., min_length=1, max_length=100)
    part_of_speech: str = Field(..., min_length=1, max_length=50)
    definition: str = Field(..., min_length=1, max_length=1000)
    count: int = Field(3, ge=1, le=10)


class FactsRequest(BaseModel):
    """Request for facts generation."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)
    count: int = Field(5, ge=1, le=10)
    previous_words: list[str] | None = Field(None, max_length=50)


class RegisterClassificationRequest(BaseModel):
    """Request for register classification."""

    definition: str = Field(..., min_length=1, max_length=1000)


class DomainIdentificationRequest(BaseModel):
    """Request for domain identification."""

    definition: str = Field(..., min_length=1, max_length=1000)


class CollocationRequest(BaseModel):
    """Request for collocation identification."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)
    part_of_speech: str = Field(..., min_length=1, max_length=50)


class GrammarPatternRequest(BaseModel):
    """Request for grammar pattern extraction."""

    definition: str = Field(..., min_length=1, max_length=1000)
    part_of_speech: str = Field(..., min_length=1, max_length=50)


class UsageNotesRequest(BaseModel):
    """Request for usage notes generation."""

    word: str = Field(..., min_length=1, max_length=100)
    definition: str = Field(..., min_length=1, max_length=1000)


class RegionalVariantRequest(BaseModel):
    """Request for regional variant detection."""

    definition: str = Field(..., min_length=1, max_length=1000)


class SynthesizeRequest(BaseModel):
    """Request for synthesizing entry components."""

    entry_id: str = Field(..., description="Synthesized dictionary entry ID")
    components: list[str] | None = Field(None, description="Components to regenerate")


class ResynthesizeRequest(BaseModel):
    """Request for re-synthesizing a word from its existing provider data."""

    word: str = Field(..., min_length=1, max_length=200, description="Word to re-synthesize")
    languages: list[str] | None = Field(
        None,
        description="Override languages (defaults to word's existing languages)",
    )


class QueryValidationRequest(BaseModel):
    """Request for query validation."""

    query: str = Field(..., min_length=1, max_length=200)


class WordSuggestionRequest(BaseModel):
    """Request for word suggestions from descriptive query."""

    query: str = Field(..., min_length=1, max_length=200)
    count: int = Field(10, ge=1, le=25)
