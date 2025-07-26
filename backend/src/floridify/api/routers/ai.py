"""AI endpoints for raw connector functions organized by prompts structure."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from ...ai.constants import SynthesisComponent
from ...ai.factory import get_definition_synthesizer, get_openai_connector
from ...models import SynthesizedDictionaryEntry
from ...utils.logging import get_logger
from ..core import ResourceResponse, handle_api_errors
from ..middleware.rate_limiting import ai_limiter, get_client_key

logger = get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


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


# Pure Generation Endpoints

@router.post("/synthesize/pronunciation")
async def generate_pronunciation(
    request: PronunciationRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate pronunciation for a word."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.pronunciation(request.word)
    
    return {"word": request.word, "pronunciation": result.model_dump()}


@router.post("/suggestions")
async def generate_suggestions(
    request: SuggestionsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate vocabulary suggestions."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=200)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.suggestions(request.input_words, request.count)
    
    return result.model_dump()


@router.post("/generate/word-forms")
async def generate_word_forms(
    request: WordFormsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate word forms."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=150)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.identify_word_forms(request.word, request.part_of_speech)
    
    return {"word": request.word, "word_forms": result.model_dump()}


@router.post("/assess/frequency")
async def assess_frequency(
    request: FrequencyAssessmentRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Assess frequency band."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.assess_frequency_band(request.word, request.definition)
    
    return result.model_dump()


@router.post("/assess/cefr")
async def assess_cefr(
    request: CEFRAssessmentRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Assess CEFR level."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.assess_cefr_level(request.word, request.definition)
    
    return result.model_dump()


# Definition-Dependent Generation Endpoints

@router.post("/synthesize/synonyms")
async def generate_synonyms(
    request: SynonymRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate synonyms for a word with definition context."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=300)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.synthesize_synonyms(
        request.word,
        request.definition,
        request.part_of_speech,
        request.existing_synonyms,
        request.count,
    )
    
    return {
        "word": request.word,
        "synonyms": [{"word": syn.word, "score": syn.relevance} for syn in result.synonyms],
        "confidence": result.confidence,
    }


@router.post("/synthesize/antonyms")
async def generate_antonyms(
    request: AntonymRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate antonyms for a word with definition context."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=250)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.synthesize_antonyms(
        request.word,
        request.definition,
        request.part_of_speech,
        request.existing_antonyms,
        request.count,
    )
    
    return {
        "word": request.word,
        "antonyms": result.antonyms,
        "confidence": result.confidence,
    }


@router.post("/generate/examples")
async def generate_examples(
    request: ExampleRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate examples for a word with definition context."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=400)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.generate_examples(
        request.word,
        request.part_of_speech,
        request.definition,
        request.count,
    )
    
    return {
        "word": request.word,
        "examples": result.example_sentences,
        "confidence": result.confidence,
    }


@router.post("/generate/facts")
async def generate_facts(
    request: FactsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Generate facts for a word with definition context."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=500)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.generate_facts(
        request.word,
        request.definition,
        request.count,
        request.previous_words,
    )
    
    return {
        "word": request.word,
        "facts": result.facts,
        "confidence": result.confidence,
        "categories": result.categories,
    }


@router.post("/assess/register")
async def classify_register(
    request: RegisterClassificationRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Classify language register."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    connector = get_openai_connector()
    result = await connector.classify_register(request.definition)
    
    return result.model_dump()


@router.post("/assess/domain")
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
    
    connector = get_openai_connector()
    result = await connector.assess_domain(request.definition)
    
    return result.model_dump()


@router.post("/assess/collocations")
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
    
    connector = get_openai_connector()
    result = await connector.assess_collocations(
        request.word,
        request.definition,
        request.part_of_speech,
    )
    
    return result.model_dump()


@router.post("/assess/grammar-patterns")
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
    
    connector = get_openai_connector()
    result = await connector.assess_grammar_patterns(
        request.definition,
        request.part_of_speech,
    )
    
    return result.model_dump()


@router.post("/usage-notes")
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
    
    connector = get_openai_connector()
    result = await connector.usage_note_generation(
        request.word,
        request.definition,
    )
    
    return result.model_dump()


@router.post("/assess/regional-variants")
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
    
    connector = get_openai_connector()
    result = await connector.assess_regional_variants(request.definition)
    
    return result.model_dump()


# Synthesize Endpoint

@router.post("/synthesize")
async def synthesize_entry_components(
    request: SynthesizeRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> ResourceResponse:
    """Regenerate specific components of an existing synthesized dictionary entry."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=1000)
    
    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)
    
    # Validate components if provided
    if request.components:
        valid_components = {comp.value for comp in SynthesisComponent}
        invalid_components = set(request.components) - valid_components
        if invalid_components:
            raise HTTPException(
                400,
                f"Invalid components: {invalid_components}. Valid components: {sorted(valid_components)}"
            )
        components = set(request.components)
    else:
        components = None
    
    # Get synthesizer and regenerate components
    synthesizer = get_definition_synthesizer()
    entry = await synthesizer.regenerate_entry_components(
        entry_id=request.entry_id,
        components=components,
    )
    
    if not entry:
        raise HTTPException(404, "Synthesized dictionary entry not found")
    
    return ResourceResponse(
        data=entry.model_dump(),
        metadata={
            "regenerated_components": list(components) if components else "default",
            "version": entry.version,
        },
        links={
            "self": "/ai/synthesize",
            "entry": f"/lookup/{entry.word_id}",
        },
    )