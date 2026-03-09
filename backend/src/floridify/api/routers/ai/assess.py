"""AI assessment endpoints: CEFR, frequency, register, domain, collocations, grammar, regional."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ....ai.connector import get_ai_connector
from ...middleware.rate_limiting import ai_limiter, get_client_key
from .base import (
    CEFRAssessmentRequest,
    CollocationRequest,
    DomainIdentificationRequest,
    FrequencyAssessmentRequest,
    GrammarPatternRequest,
    RegionalVariantRequest,
    RegisterClassificationRequest,
    handle_ai_errors,
)

router = APIRouter()


@router.post("/assess/frequency")
@handle_ai_errors
async def assess_frequency(
    request: FrequencyAssessmentRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """AI-assess word frequency band (1-5).

    Body:
        - word: Target word
        - definition: Context definition

    Returns:
        Frequency band (1=most common, 5=rare).

    Rate Limited: ~100 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.assess_frequency_band(request.word, request.definition)

    return result.model_dump()


@router.post("/assess/cefr")
@handle_ai_errors
async def assess_cefr(
    request: CEFRAssessmentRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """AI-assess CEFR difficulty level.

    Body:
        - word: Target word
        - definition: Context definition

    Returns:
        CEFR level (A1-C2) with reasoning.

    Rate Limited: ~100 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.assess_cefr_level(request.word, request.definition)

    return result.model_dump()


@router.post("/assess/register")
@handle_ai_errors
async def classify_register(
    request: RegisterClassificationRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """AI-classify language register.

    Body:
        - definition: Definition text

    Returns:
        Register: formal/informal/neutral/slang/technical.

    Rate Limited: ~100 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.classify_register(request.definition)

    return result.model_dump()


@router.post("/assess/domain")
@handle_ai_errors
async def identify_domain(
    request: DomainIdentificationRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Identify domain."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.assess_domain(request.definition)

    return result.model_dump()


@router.post("/assess/collocations")
@handle_ai_errors
async def identify_collocations(
    request: CollocationRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Identify collocations."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=200)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.assess_collocations(
        request.word,
        request.definition,
        request.part_of_speech,
    )

    return result.model_dump()


@router.post("/assess/grammar-patterns")
@handle_ai_errors
async def extract_grammar_patterns(
    request: GrammarPatternRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Extract grammar patterns."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=150)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.assess_grammar_patterns(
        request.definition,
        request.part_of_speech,
    )

    return result.model_dump()


@router.post("/assess/regional-variants")
@handle_ai_errors
async def detect_regional_variants(
    request: RegionalVariantRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Detect regional variants."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=150)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.assess_regional_variants(request.definition)

    return result.model_dump()
