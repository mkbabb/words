"""Synonym endpoints for semantic word relationships."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ...caching.decorators import cached_api_call
from ...constants import Language
from ...core.search_manager import get_search_engine
from ...search.constants import SearchMethod
from ...utils.logging import get_logger
from ..models.requests import SynonymParams
from ..models.responses import SynonymItem, SynonymResponse

logger = get_logger(__name__)
router = APIRouter()


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
    """Cached synonym lookup implementation."""
    search_engine = await get_search_engine([Language.ENGLISH])
    
    # Use semantic search to find similar words
    results = await search_engine.search(
        query=word,
        max_results=params.max_results + 1,  # +1 to exclude original word
        methods=[SearchMethod.SEMANTIC],
    )
    
    # Filter out the original word and convert to synonyms
    synonyms = []
    for result in results:
        if result.word.lower() != word.lower():
            synonyms.append(SynonymItem(
                word=result.word,
                score=result.score,
            ))
    
    # Limit to requested number
    synonyms = synonyms[:params.max_results]
    
    return SynonymResponse(
        word=word,
        synonyms=synonyms,
    )


@router.get("/synonyms/{word}", response_model=SynonymResponse)
async def get_synonyms(
    word: str,
    params: SynonymParams = Depends(parse_synonym_params),
) -> SynonymResponse:
    """Get semantically similar words (synonyms) for the given word.
    
    Uses advanced semantic search to find words with similar meanings,
    ranked by similarity score. Ideal for:
    
    - Finding alternative word choices for writing
    - Vocabulary expansion and exploration  
    - Semantic analysis and word relationships
    - Language learning and comprehension
    
    Args:
        word: Target word to find synonyms for
        max_results: Maximum number of synonyms to return (1-20, default: 10)
        
    Returns:
        List of semantically similar words with similarity scores (0.0-1.0)
        
    Example:
        GET /api/v1/synonyms/happy?max_results=5
        Returns: ["joyful", "cheerful", "content", "pleased", "delighted"]
    """
    start_time = time.perf_counter()
    
    try:
        result = await _cached_synonyms(word, params)
        
        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Synonyms completed: '{word}' -> {len(result.synonyms)} results in {elapsed_ms}ms")
        
        return result
        
    except Exception as e:
        logger.error(f"Synonyms failed for '{word}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error getting synonyms: {str(e)}"
        )