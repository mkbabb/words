"""Lookup endpoints for word definitions."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ...caching.decorators import cached_api_call
from ...constants import DictionaryProvider, Language
from ...core.lookup_pipeline import lookup_word_pipeline
from ...utils.logging import get_logger
from ..models.requests import LookupParams
from ..models.responses import LookupResponse

logger = get_logger(__name__)
router = APIRouter()


def parse_lookup_params(
    force_refresh: bool = Query(default=False, description="Force refresh of cached data"),
    providers: list[str] = Query(default=["wiktionary"], description="Dictionary providers"),
    no_ai: bool = Query(default=False, description="Skip AI synthesis"),
) -> LookupParams:
    """Parse and validate lookup parameters."""
    # Convert string providers to enum
    provider_enums = []
    for provider_str in providers:
        try:
            provider_enums.append(DictionaryProvider(provider_str.lower()))
        except ValueError:
            # Skip invalid providers
            logger.warning(f"Invalid provider: {provider_str}")
    
    if not provider_enums:
        provider_enums = [DictionaryProvider.WIKTIONARY]
    
    return LookupParams(
        force_refresh=force_refresh,
        providers=provider_enums,
        no_ai=no_ai,
    )


@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda word, params: ("api_lookup", word, params.force_refresh, tuple(params.providers), params.no_ai),
)
async def _cached_lookup(word: str, params: LookupParams) -> LookupResponse | None:
    """Cached word lookup implementation."""
    logger.info(f"Looking up word: {word}")
    
    # Use existing lookup pipeline
    entry = await lookup_word_pipeline(
        word=word,
        providers=params.providers,
        languages=[Language.ENGLISH],
        force_refresh=params.force_refresh,
        no_ai=params.no_ai,
    )
    
    if not entry:
        return None
    
    return LookupResponse(
        word=entry.word,
        pronunciation=entry.pronunciation,
        definitions=entry.definitions,
        last_updated=entry.last_updated,
    )


@router.get("/lookup/{word}", response_model=LookupResponse)
async def lookup_word(
    word: str,
    params: LookupParams = Depends(parse_lookup_params),
) -> LookupResponse:
    """Comprehensive word definition lookup with AI-enhanced synthesis.
    
    Performs intelligent word resolution through multi-stage processing:
    1. Word normalization and search across indexed lexicon
    2. Provider-based definition retrieval (Wiktionary, Dictionary.com)
    3. AI-powered meaning extraction and synthesis
    4. Semantic clustering of related definitions
    
    Features:
    - Multi-provider aggregation for comprehensive coverage
    - AI synthesis for coherent, unified definitions
    - Pronunciation data in multiple formats (phonetic, IPA)
    - Rich examples from literature and AI generation
    - Semantic clustering to prevent confusion between unrelated meanings
    
    Performance:
    - Cached responses (1-hour TTL) for optimal speed
    - Typical response time: < 500ms for cached entries
    - Force refresh available for latest data
    
    Args:
        word: Target word for definition lookup (path parameter)
        force_refresh: Bypass all caches for fresh data (default: false)
        providers: Dictionary sources to query (default: wiktionary)
        no_ai: Skip AI synthesis, return raw provider data (default: false)
        
    Returns:
        Comprehensive word entry with pronunciation, definitions, examples,
        and metadata. Each definition includes word type, meaning cluster,
        synonyms, and contextual examples.
        
    Raises:
        404: Word not found in any provider or search index
        500: Internal processing error (provider failure, AI synthesis error)
        422: Invalid parameters (malformed word, unsupported provider)
        
    Example:
        GET /api/v1/lookup/serendipity?providers=wiktionary&force_refresh=false
        
        Returns detailed entry with pronunciation, multiple meanings,
        examples, and AI-synthesized coherent definitions.
    """
    start_time = time.perf_counter()
    
    try:
        result = await _cached_lookup(word, params)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No definition found for word: {word}"
            )
        
        # Log performance
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Lookup completed: {word} in {elapsed_ms}ms")
        
        return result
        
    except Exception as e:
        logger.error(f"Lookup failed for {word}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during lookup: {str(e)}"
        )