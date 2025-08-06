"""AI endpoints for raw connector functions organized by prompts structure."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ....ai.constants import SynthesisComponent
from ....ai.factory import get_definition_synthesizer, get_openai_connector
from ....core.state_tracker import StateTracker
from ....core.streaming import create_streaming_response
from ....utils.logging import get_logger
from ...core import ResourceResponse
from ...middleware.rate_limiting import ai_limiter, get_client_key

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

    connector = get_openai_connector()
    result = await connector.pronunciation(request.word)

    return {"word": request.word, "pronunciation": result.model_dump()}


@router.post("/suggestions")
async def generate_suggestions(
    request: SuggestionsRequest,
    api_request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """AI-generate related vocabulary suggestions.

    Body:
        - input_words: Seed words for context (optional, max 10)
        - count: Number of suggestions (4-12, default: 10)

    Returns:
        Suggested words with themes and difficulty levels.

    Rate Limited: ~200 tokens
    """
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

    connector = get_openai_connector()
    result = await connector.identify_word_forms(request.word, request.part_of_speech)

    return {"word": request.word, "word_forms": result.model_dump()}


@router.post("/assess/frequency")
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

    connector = get_openai_connector()
    result = await connector.assess_frequency_band(request.word, request.definition)

    return result.model_dump()


@router.post("/assess/cefr")
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


# New Word Suggestion Endpoints


class QueryValidationRequest(BaseModel):
    """Request for query validation."""

    query: str = Field(..., min_length=1, max_length=200)


class WordSuggestionRequest(BaseModel):
    """Request for word suggestions from descriptive query."""

    query: str = Field(..., min_length=1, max_length=200)
    count: int = Field(10, ge=1, le=25)


@router.post("/validate-query")
async def validate_query(
    request: QueryValidationRequest,
    api_request: Request,
) -> dict[str, Any]:
    """Validate if query seeks word suggestions."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=100)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    connector = get_openai_connector()
    result = await connector.validate_query(request.query)

    return result.model_dump()


@router.post("/suggest-words")
async def suggest_words(
    request: WordSuggestionRequest,
    api_request: Request,
) -> dict[str, Any]:
    """Generate word suggestions from descriptive query."""
    client_key = get_client_key(api_request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=500)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    # First validate the query
    connector = get_openai_connector()
    validation = await connector.validate_query(request.query)

    if not validation.is_valid:
        raise HTTPException(400, f"Invalid query: {validation.reason}")

    # Generate suggestions
    result = await connector.suggest_words(request.query, request.count)

    return result.model_dump()


@router.get("/suggest-words/stream", response_model=None)
async def suggest_words_stream(
    request: Request,
    query: str,
    count: int = 12,
) -> StreamingResponse:
    """Generate word suggestions with streaming progress updates.

    Returns Server-Sent Events (SSE) with progress updates.

    Query Parameters:
        - query: Descriptive query for word suggestions
        - count: Number of suggestions (1-25, default: 12)

    Event Types:
        - config: Stage definitions for progress visualization
        - progress: Update on current operation with stage and progress
        - complete: Final result with word suggestions
        - error: Error details if something goes wrong
    """
    # Validate count parameter
    if count < 1 or count > 25:
        raise HTTPException(400, "Count must be between 1 and 25")

    client_key = get_client_key(request)
    allowed, headers = await ai_limiter.check_request_allowed(client_key, estimated_tokens=500)

    if not allowed:
        raise HTTPException(429, "AI rate limit exceeded", headers=headers)

    # Create state tracker for suggestions
    state_tracker = StateTracker(category="suggestions")

    async def suggestions_process() -> None:
        """Run the suggestion pipeline with state tracking."""
        try:
            await state_tracker.update_stage("START")
            await state_tracker.update(
                stage="START", message=f"Starting word suggestions for '{query}'..."
            )

            # Validate query
            await state_tracker.update_stage("QUERY_VALIDATION")
            await state_tracker.update(stage="QUERY_VALIDATION", message="Validating query...")

            connector = get_openai_connector()
            validation = await connector.validate_query(query)

            if not validation.is_valid:
                raise ValueError(f"Invalid query: {validation.reason}")

            await state_tracker.update(
                stage="QUERY_VALIDATION", progress=30, message="Query validated successfully"
            )

            # Generate words
            await state_tracker.update_stage("WORD_GENERATION")
            await state_tracker.update(
                stage="WORD_GENERATION", message="Generating word suggestions..."
            )

            result = await connector.suggest_words(query, count)

            await state_tracker.update(
                stage="WORD_GENERATION",
                progress=70,
                message=f"Generated {len(result.suggestions)} suggestions",
            )

            # Score and rank
            await state_tracker.update_stage("SCORING")
            await state_tracker.update(
                stage="SCORING", message="Scoring and ranking suggestions..."
            )

            # Complete successfully
            await state_tracker.update_complete(message="Suggestions generated successfully!")

            # Return result data
            return result

        except Exception as e:
            await state_tracker.update_error(f"Failed to generate suggestions: {str(e)}")
            raise

    # Use the generalized streaming system
    return await create_streaming_response(
        state_tracker=state_tracker,
        process_func=suggestions_process,
        include_stage_definitions=True,
        include_completion_data=True,
    )


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
                f"Invalid components: {invalid_components}. Valid components: {sorted(valid_components)}",
            )
        components = {SynthesisComponent(comp) for comp in request.components}
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
