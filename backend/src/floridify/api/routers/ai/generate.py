"""AI generation endpoints: pronunciation, synonyms, antonyms, examples, facts, usage-notes, word-forms."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ....ai.connector import get_ai_connector
from ...middleware.rate_limiting import ai_limiter, get_client_key
from .base import (
    AntonymRequest,
    AntonymResponse,
    ExampleRequest,
    ExampleResponse,
    FactsRequest,
    FactsResponse,
    PronunciationRequest,
    PronunciationResponse,
    SynonymEntry,
    SynonymRequest,
    SynonymResponse,
    UsageNotesRequest,
    WordFormsRequest,
    WordFormsResponse,
    handle_ai_errors,
)

router = APIRouter()


@router.post("/synthesize/pronunciation", response_model=PronunciationResponse)
@handle_ai_errors
async def generate_pronunciation(
    request: PronunciationRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> PronunciationResponse:
    """AI-generate phonetic pronunciation.

    Body:
        - word: Target word (1-100 chars)

    Returns:
        Pronunciation data with phonetic spelling and IPA.

    Rate Limited: ~100 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.pronunciation(request.word)

    return PronunciationResponse(word=request.word, pronunciation=result.model_dump())


@router.post("/generate/word-forms", response_model=WordFormsResponse)
@handle_ai_errors
async def generate_word_forms(
    request: WordFormsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> WordFormsResponse:
    """AI-identify morphological word forms.

    Body:
        - word: Base word (1-100 chars)
        - part_of_speech: Word class (noun, verb, etc.)

    Returns:
        Inflected forms (plurals, tenses, etc.).

    Rate Limited: ~150 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=150)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.identify_word_forms(request.word, request.part_of_speech)

    return WordFormsResponse(word=request.word, word_forms=result.model_dump())


@router.post("/synthesize/synonyms", response_model=SynonymResponse)
@handle_ai_errors
async def generate_synonyms(
    request: SynonymRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> SynonymResponse:
    """AI-generate contextual synonyms.

    Body:
        - word: Target word
        - definition: Specific meaning context
        - part_of_speech: Word class
        - existing_synonyms: Already known (max 20)
        - count: Desired count (1-20, default: 10)

    Returns:
        Synonyms with relevance scores.

    Rate Limited: ~300 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=300)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.synthesize_synonyms(
        request.word,
        request.definition,
        request.part_of_speech,
        request.existing_synonyms,
        request.count,
    )

    return SynonymResponse(
        word=request.word,
        synonyms=[SynonymEntry(word=syn.word, score=syn.relevance) for syn in result.synonyms],
        confidence=result.confidence,
    )


@router.post("/synthesize/antonyms", response_model=AntonymResponse)
@handle_ai_errors
async def generate_antonyms(
    request: AntonymRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> AntonymResponse:
    """AI-generate contextual antonyms.

    Body:
        - word: Target word
        - definition: Specific meaning context
        - part_of_speech: Word class
        - existing_antonyms: Already known (max 20)
        - count: Desired count (1-10, default: 5)

    Returns:
        Antonyms with confidence scores.

    Rate Limited: ~250 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=250)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.synthesize_antonyms(
        request.word,
        request.definition,
        request.part_of_speech,
        request.existing_antonyms,
        request.count,
    )

    return AntonymResponse(
        word=request.word,
        antonyms=[a.word for a in result.antonyms],
        confidence=result.confidence,
    )


@router.post("/generate/examples", response_model=ExampleResponse)
@handle_ai_errors
async def generate_examples(
    request: ExampleRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> ExampleResponse:
    """AI-generate contextual example sentences.

    Body:
        - word: Target word
        - part_of_speech: Word class
        - definition: Specific meaning
        - count: Number of examples (1-10, default: 3)

    Returns:
        Natural example sentences demonstrating usage.

    Rate Limited: ~400 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=400)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.generate_examples(
        request.word,
        request.part_of_speech,
        request.definition,
        request.count,
    )

    return ExampleResponse(
        word=request.word,
        examples=result.example_sentences,
        confidence=result.confidence,
    )


@router.post("/generate/facts", response_model=FactsResponse)
@handle_ai_errors
async def generate_facts(
    request: FactsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> FactsResponse:
    """AI-generate interesting word facts.

    Body:
        - word: Target word
        - definition: Context
        - count: Number of facts (1-10, default: 5)
        - previous_words: Avoid repetition (optional)

    Returns:
        Categorized facts (etymology, usage, cultural).

    Rate Limited: ~500 tokens

    """
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=500)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.generate_facts(
        request.word,
        request.definition,
        request.count,
        request.previous_words,
    )

    return FactsResponse(
        word=request.word,
        facts=result.facts,
        confidence=result.confidence,
        categories=result.categories,
    )


@router.post("/usage-notes")
@handle_ai_errors
async def generate_usage_notes(
    request: UsageNotesRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate usage notes."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=200)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_ai_connector()
    result = await connector.usage_note_generation(
        request.word,
        request.definition,
    )

    return result.model_dump()
