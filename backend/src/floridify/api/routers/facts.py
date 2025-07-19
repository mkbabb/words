"""AI-powered fact generation endpoint for words."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ...ai.factory import get_openai_connector
from ...caching.decorators import cached_api_call
from ...storage.mongodb import get_synthesized_entry
from ...utils.logging import get_logger
from ..models.requests import FactParams
from ..models.responses import FactItem, FactsAPIResponse

logger = get_logger(__name__)
router = APIRouter()


def parse_fact_params(
    count: int = Query(default=5, ge=3, le=8, description="Number of facts to generate"),
    previous_words: list[str] | None = Query(default=None, description="Previously searched words for context"),
) -> FactParams:
    """Parse and validate fact generation parameters."""
    return FactParams(count=count, previous_words=previous_words)


@cached_api_call(
    ttl_hours=48.0,  # Facts are relatively stable
    key_func=lambda word, params: ("api_facts", word, params.count, tuple(sorted(params.previous_words)) if params.previous_words else None),
)
async def _cached_facts(word: str, params: FactParams) -> FactsAPIResponse:
    """Cached facts implementation."""
    logger.info(f"📚 Generating {params.count} facts for '{word}'")
    
    try:
        # Get synthesized entry for word
        entry = await get_synthesized_entry(word)
        
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Word '{word}' not found. Please lookup the word first."
            )
        
        # Get main definition for context
        main_definition = ""
        if entry.definitions:
            main_definition = entry.definitions[0].definition
        
        # Get OpenAI connector
        connector = get_openai_connector()
        
        # Generate facts using AI
        ai_response = await connector.generate_facts(
            word=word,
            definition=main_definition,
            count=params.count,
            previous_words=params.previous_words,
        )
        
        # Convert to API response format
        fact_items = [
            FactItem(
                content=fact,
                category="general",  # AI response includes categories in the future
                confidence=ai_response.confidence
            )
            for fact in ai_response.facts
        ]
        
        return FactsAPIResponse(
            word=word,
            facts=fact_items,
            confidence=ai_response.confidence,
            categories=ai_response.categories or ["general"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate facts for '{word}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error generating facts: {str(e)}"
        )


@router.get("/facts/{word}", response_model=FactsAPIResponse)
async def get_word_facts(
    word: str,
    params: FactParams = Depends(parse_fact_params),
) -> FactsAPIResponse:
    """Generate interesting facts about a word.
    
    Provides fascinating, educational insights about words including:
    - Etymology and historical development
    - Cultural significance and usage patterns  
    - Linguistic connections and word relationships
    - Modern vs historical usage examples
    - Connections to previously searched words
    
    The word must exist in the system (i.e., has been looked up previously).
    Facts are generated using AI and cached for performance.
    
    Args:
        word: The word to generate facts about
        count: Number of facts to generate (3-8, default: 5)
        previous_words: Previously searched words for context (optional)
        
    Returns:
        Structured response with interesting facts about the word
        
    Example:
        GET /api/v1/facts/serendipity?count=6
        
        Returns facts about etymology, usage, cultural impact, etc.
    """
    start_time = time.perf_counter()
    
    try:
        result = await _cached_facts(word.lower(), params)
        
        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        fact_count = len(result.facts)
        logger.info(
            f"Facts completed: '{word}' -> "
            f"{fact_count} facts in {elapsed_ms}ms "
            f"(confidence: {result.confidence:.1%})"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Facts request failed for '{word}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error generating facts: {str(e)}"
        )