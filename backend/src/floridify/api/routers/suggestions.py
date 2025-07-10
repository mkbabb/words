"""Florid word suggestions endpoint with AI-powered recommendations."""

from __future__ import annotations

import time

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from ...ai.factory import get_openai_connector
from ...caching.decorators import cached_api_call
from ...utils.logging import get_logger
from ..models.requests import SuggestionsParams
from ..models.responses import SuggestionsAPIResponse

logger = get_logger(__name__)
router = APIRouter()


def parse_suggestions_params_get(
    words: list[str] | None = Query(default=None, description="Input words to base suggestions on"),
    count: int = Query(default=10, ge=4, le=12, description="Number of suggestions"),
) -> SuggestionsParams:
    """Parse and validate suggestions parameters for GET requests."""
    return SuggestionsParams(words=words, count=count)


def parse_suggestions_params_post(
    params: SuggestionsParams = Body(..., description="Suggestions request parameters"),
) -> SuggestionsParams:
    """Parse and validate suggestions parameters for POST requests."""
    return params


@cached_api_call(
    ttl_hours=24.0,  # Suggestions are relatively stable
    key_func=lambda params: ("api_suggestions", tuple(sorted(params.words)) if params.words else None, params.count),
)
async def _cached_suggestions(params: SuggestionsParams) -> SuggestionsAPIResponse:
    """Cached suggestions implementation."""
    word_count = len(params.words) if params.words else 0
    logger.info(f"Generating suggestions based on {word_count} words")
    
    try:
        # Get OpenAI connector singleton
        connector = get_openai_connector()
        
        # Generate suggestions using AI
        ai_response = await connector.suggestions(
            input_words=params.words,
            count=params.count,
        )
        
        return SuggestionsAPIResponse(
            words=[suggestion.word for suggestion in ai_response.suggestions],
            confidence=ai_response.confidence,
        )
        
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}")
        raise


@router.get("/suggestions", response_model=SuggestionsAPIResponse)
async def get_suggestions_get(
    params: SuggestionsParams = Depends(parse_suggestions_params_get),
) -> SuggestionsAPIResponse:
    """Generate word suggestions via GET request (typically when no recent words available)."""
    return await _handle_suggestions_request(params)


@router.post("/suggestions", response_model=SuggestionsAPIResponse)
async def get_suggestions_post(
    params: SuggestionsParams = Depends(parse_suggestions_params_post),
) -> SuggestionsAPIResponse:
    """Generate word suggestions based on input vocabulary via POST request."""
    return await _handle_suggestions_request(params)


async def _handle_suggestions_request(params: SuggestionsParams) -> SuggestionsAPIResponse:
    """Handle suggestions request logic for both GET and POST endpoints.
    
    Analyzes the provided words and suggests sophisticated vocabulary
    that builds upon demonstrated interests and complexity levels. Perfect for:
    
    - Vocabulary expansion and intellectual growth
    - Writing enhancement with sophisticated alternatives
    - Language learning and exploration
    - Academic and creative writing improvement
    
    Features:
    - AI-powered semantic analysis of input words
    - Contextually relevant suggestions with explanations
    - Difficulty level indicators for progressive learning
    - Thematic categorization for organized exploration
    - High-quality caching for optimal performance
    
    Args:
        words: List of 1-10 words that represent current vocabulary interests (optional)
        count: Number of suggestions to generate (4-12, default: 10)
        
    Returns:
        Structured response with word suggestions, each including:
        - The suggested word with explanation
        - Difficulty level (1-5 scale) 
        - Semantic category/theme
        - Reasoning for suggestion relevance
        
    Example:
        POST /api/v1/suggestions
        {
            "words": ["serendipity", "eloquent", "paradigm"],
            "count": 10
        }
        
        Returns sophisticated vocabulary suggestions like "perspicacious",
        "efflorescence", "mellifluous" with detailed explanations.
    """
    start_time = time.perf_counter()
    
    try:
        result = await _cached_suggestions(params)
        
        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        word_count = len(params.words) if params.words else 0
        logger.info(
            f"Suggestions completed: {word_count} words -> "
            f"{len(result.words)} suggestions in {elapsed_ms}ms "
            f"(confidence: {result.confidence:.1%})"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Suggestions failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error generating suggestions: {str(e)}"
        )