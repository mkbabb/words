"""Synonym endpoints for semantic word relationships."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...ai.factory import get_openai_connector
from ...caching.decorators import cached_api_call
from ...constants import Language
from ...core.search_pipeline import find_best_match
from ...utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class SynonymParams(BaseModel):
    """Parameters for synonym endpoint."""

    max_results: int = Field(default=10, ge=1, le=20, description="Maximum synonyms")


class SynonymItem(BaseModel):
    """Single synonym item."""

    word: str = Field(..., description="Synonym word")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class SynonymResponse(BaseModel):
    """Response for synonym query."""

    word: str = Field(..., description="Original word")
    synonyms: list[SynonymItem] = Field(default_factory=list, description="List of synonyms")


def parse_synonym_params(
    max_results: int = Query(default=10, ge=1, le=20, description="Maximum synonyms"),
) -> SynonymParams:
    """Parse and validate synonym parameters."""
    return SynonymParams(max_results=max_results)


@cached_api_call(
    ttl_hours=24.0,  # Synonyms change rarely
    key_func=lambda word, params: ("api_synonyms", word, params.max_results),
)
async def _cached_synonyms(word: str, params: SynonymParams) -> SynonymResponse:
    """Cached synonym lookup implementation using AI."""
    logger.info(f"Generating AI synonyms for '{word}'")

    try:
        # Find best match for the word
        best_match = await find_best_match(word=word, languages=[Language.ENGLISH], semantic=False)

        if best_match:
            word = best_match.word

        # Use generic definition for now
        definition = f"The word '{word}'"
        part_of_speech = "word"

        # Create OpenAI connector and generate synonyms
        # Get OpenAI connector singleton
        connector = get_openai_connector()
        ai_response = await connector.synthesize_synonyms(
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_synonyms=[],  # Empty existing synonyms
            count=params.max_results,
        )

        # Convert AI response to API format
        synonyms = []
        for syn_candidate in ai_response.synonyms:
            synonyms.append(
                SynonymItem(
                    word=syn_candidate.word,
                    score=syn_candidate.relevance,
                )
            )

        return SynonymResponse(
            word=word,
            synonyms=synonyms,
        )

    except Exception as e:
        logger.error(f"AI synonym generation failed for '{word}': {e}")
        # Fallback to empty response rather than failing
        return SynonymResponse(
            word=word,
            synonyms=[],
        )


@router.get("/synonyms/{word}", response_model=SynonymResponse)
async def get_synonyms(
    word: str,
    params: SynonymParams = Depends(parse_synonym_params),
) -> SynonymResponse:
    """Get AI-generated synonyms for the given word.

    Uses advanced AI language models to generate contextually appropriate
    synonyms with sophisticated understanding of semantic relationships,
    nuanced meanings, and appropriate difficulty levels. Perfect for:

    - Enhanced writing with precise word choices
    - Vocabulary development and sophistication
    - Creative writing and eloquent expression
    - Academic and professional communication

    Features:
    - AI-powered semantic understanding beyond simple similarity
    - Context-aware synonym generation with relevance scoring
    - Sophisticated vocabulary suggestions for enhanced expression
    - High-quality caching for optimal performance

    Args:
        word: Target word to find synonyms for
        max_results: Maximum number of synonyms to return (1-20, default: 10)

    Returns:
        List of AI-generated synonyms with relevance scores (0.0-1.0)

    Example:
        GET /api/v1/synonyms/eloquent?max_results=5
        Returns: ["articulate", "fluent", "expressive", "persuasive", "mellifluous"]
    """
    start_time = time.perf_counter()

    try:
        result = await _cached_synonyms(word, params)

        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"Synonyms completed: '{word}' -> {len(result.synonyms)} results in {elapsed_ms}ms"
        )

        return result

    except Exception as e:
        logger.error(f"Synonyms failed for '{word}': {e}")
        raise HTTPException(status_code=500, detail=f"Internal error getting synonyms: {str(e)}")
