"""OpenAI connector with modern async API and structured outputs."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..caching.decorators import cached_api_call
from ..models import Definition, ModelInfo
from ..utils.logging import get_logger, log_metrics
from .model_selection import ModelTier, get_model_for_task, get_temperature_for_model
from .models import (
    AnkiFillBlankResponse,
    AnkiMultipleChoiceResponse,
    AntonymResponse,
    CEFRLevelResponse,
    ClusterMappingResponse,
    CollocationResponse,
    DeduplicationResponse,
    DictionaryEntryResponse,
    DomainIdentificationResponse,
    EtymologyResponse,
    ExampleGenerationResponse,
    FactGenerationResponse,
    FrequencyBandResponse,
    GrammarPatternResponse,
    LiteratureAnalysisResponse,
    LiteratureAugmentationRequest,
    LiteratureAugmentationResponse,
    PronunciationResponse,
    QueryValidationResponse,
    RegionalVariantResponse,
    RegisterClassificationResponse,
    SuggestionsResponse,
    SynonymGenerationResponse,
    SynthesisResponse,
    SyntheticCorpusResponse,
    TextGenerationRequest,
    TextGenerationResponse,
    UsageNoteResponse,
    WordFormResponse,
    WordOfTheDayResponse,
    WordSuggestionResponse,
)
from .prompt_manager import PromptManager

T = TypeVar("T", bound=BaseModel)

logger = get_logger(__name__)


class OpenAIConnector:
    """Modern OpenAI connector with structured outputs and caching."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-5-nano",
        embedding_model: str = "text-embedding-3-small",
        temperature: float | None = None,
        max_tokens: int = 1000,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.api_key = api_key
        self.default_model = model_name  # Keep default from config
        self.model_name = model_name  # Current active model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt_manager = PromptManager()
        self._last_model_info: ModelInfo | None = None  # Track last model info

    @property
    def last_model_info(self) -> ModelInfo | None:
        """Get the last model info that was actually used for a request."""
        return self._last_model_info

    @property
    def last_model_used(self) -> str:
        """Get the last model that was actually used for a request (backward compat)."""
        return self._last_model_info.name if self._last_model_info else self.model_name

    @cached_api_call(
        ttl_hours=24.0,  # Cache OpenAI responses for 24 hours
        key_prefix="openai_structured",
    )
    async def _make_structured_request(
        self,
        prompt: str,
        response_model: type[T],
        task_name: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Make a structured request to OpenAI with caching and model selection.

        Args:
            prompt: The prompt to send
            response_model: The Pydantic model for response parsing
            task_name: Optional task name for model selection
            **kwargs: Additional parameters for the API call

        """
        start_time = time.perf_counter()
        retry_count = 0
        max_retries = 3

        # Determine which model to use based on task
        model_tier = None

        if task_name:
            model_tier = get_model_for_task(task_name)
            active_model = model_tier.value
        else:
            active_model = self.model_name
            # Try to get ModelTier if the model name matches a known tier
            try:
                model_tier = ModelTier(active_model)
            except ValueError:
                model_tier = None

        # Get appropriate temperature
        temperature = (
            get_temperature_for_model(model_tier, task_name) if model_tier else self.temperature
        )

        # Handle max_tokens parameter from kwargs before adding to request_params
        max_tokens_value = kwargs.pop("max_tokens", None) or self.max_tokens

        # Prepare request parameters
        request_params: dict[str, Any] = {
            "model": active_model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }

        # Use correct token parameter based on model capabilities
        if model_tier and model_tier.uses_completion_tokens:
            if model_tier.is_reasoning_model:
                # Reasoning models need massive token allocation for internal thinking
                # For small outputs like 30-50 tokens, we need 10-20x more for reasoning
                reasoning_multiplier = 30 if max_tokens_value <= 50 else 15
                request_params["max_completion_tokens"] = max(
                    4000, max_tokens_value * reasoning_multiplier
                )
            else:
                # Non-reasoning models with completion tokens use standard allocation
                request_params["max_completion_tokens"] = max_tokens_value
        else:
            # Legacy models use max_tokens
            request_params["max_tokens"] = max_tokens_value

        # Add temperature if model supports it (reasoning/thinking models don't)
        if temperature is not None and model_tier and not model_tier.is_reasoning_model:
            request_params["temperature"] = temperature
        elif temperature is not None and not model_tier:
            # Fallback for unknown models
            request_params["temperature"] = temperature

        while retry_count < max_retries:
            try:
                # Log API call details
                logger.debug(
                    f"🤖 OpenAI API call: model={active_model}, "
                    f"task={task_name or 'default'}, "
                    f"response_type={response_model.__name__}, "
                    f"prompt_length={len(prompt)}, retry={retry_count}",
                )

                # Make the API call with structured output
                api_start = time.perf_counter()
                response = await self.client.beta.chat.completions.parse(
                    response_format=response_model,
                    **request_params,
                )
                api_duration = time.perf_counter() - api_start

                # Extract token usage
                token_usage = {}
                prompt_tokens = None
                completion_tokens = None
                total_tokens = None
                if hasattr(response, "usage") and response.usage:
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    total_tokens = response.usage.total_tokens
                    token_usage = {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    }

                # Log successful API call
                log_metrics(
                    api_call="openai",
                    model=active_model,
                    task=task_name or "default",
                    response_type=response_model.__name__,
                    duration=api_duration,
                    retry_count=retry_count,
                    **token_usage,
                )

                # Parse JSON response
                content = response.choices[0].message.content
                if content:
                    result = response_model.model_validate_json(content)
                    # Store token usage on the result if it has that attribute
                    if hasattr(result, "token_usage"):
                        result.token_usage = token_usage
                    # Store the actual model used on the result if it has model_info
                    if hasattr(result, "model_info") and result.model_info:
                        result.model_info.name = active_model
                    # Store the model name for tracking
                    if hasattr(result, "_model_used"):
                        result._model_used = active_model
                else:
                    raise ValueError("No content in response")

                # Track the last model info
                self._last_model_info = ModelInfo(
                    name=active_model,
                    confidence=0.9,  # Default high confidence for successful responses
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens_value,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    response_time_ms=int(api_duration * 1000),
                )

                total_duration = time.perf_counter() - start_time
                logger.info(
                    f"✅ OpenAI API success: {response_model.__name__} "
                    f"in {total_duration:.2f}s (tokens: {token_usage.get('total_tokens', 'N/A')})",
                )

                return result

            except Exception as e:
                retry_count += 1
                duration = time.perf_counter() - start_time

                if retry_count < max_retries:
                    wait_time = retry_count * 2  # Exponential backoff
                    logger.warning(
                        f"⚠️  OpenAI API error (attempt {retry_count}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s...",
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ OpenAI API failed after {max_retries} attempts "
                        f"({duration:.2f}s total): {e}",
                    )
                    log_metrics(
                        api_call="openai_error",
                        model=active_model,
                        task=task_name or "default",
                        response_type=response_model.__name__,
                        error=str(e),
                        duration=duration,
                        retry_count=retry_count,
                    )
                    raise

        # This should never be reached, but satisfies type checker
        raise RuntimeError(f"Failed to get response after {max_retries} retries")

    async def synthesize_definitions(
        self,
        word: str,
        definitions: list[Definition],
        meaning_cluster: str | None = None,
    ) -> SynthesisResponse:
        """Synthesize definitions from multiple providers using full Definition objects.

        Args:
            word: The word to synthesize definitions for.
            definitions: List of Definition objects serialized as dictionaries.
            meaning_cluster: The meaning cluster this definition belongs to.

        """
        prompt = self.prompt_manager.render(
            "synthesize/definitions",
            word=word,
            definitions=definitions,
            meaning_cluster=meaning_cluster,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                SynthesisResponse,
                task_name="synthesize_definitions",
            )
            # Success logging handled by synthesizer context
            return result
        except Exception as e:
            logger.error(f"❌ Definition synthesis failed for '{word}' ({meaning_cluster}): {e}")
            raise

    async def generate_examples(
        self,
        word: str,
        part_of_speech: str,
        definition: str,
        count: int = 1,
    ) -> ExampleGenerationResponse:
        """Generate modern usage examples."""
        logger.debug(f"📝 Generating {count} example sentence(s) for '{word}' ({part_of_speech})")

        prompt = self.prompt_manager.render(
            "generate/examples",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            count=count,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                ExampleGenerationResponse,
                task_name="generate_examples",
            )
            if result.example_sentences:
                first_example = result.example_sentences[0]
                truncated = first_example[:50] + "..." if len(first_example) > 50 else first_example
                logger.debug(f"✏️  Generated example for '{word}': \"{truncated}\"")
            return result
        except Exception as e:
            logger.error(f"❌ Example generation failed for '{word}': {e}")
            raise

    async def pronunciation(self, word: str) -> PronunciationResponse:
        """Generate pronunciation data."""
        prompt = self.prompt_manager.render("synthesize/pronunciation", word=word)

        return await self._make_structured_request(
            prompt,
            PronunciationResponse,
            task_name="generate_pronunciation",
        )

    async def lookup_fallback(self, word: str) -> DictionaryEntryResponse | None:
        """Generate AI fallback provider data."""
        logger.info(f"🤖 Generating AI fallback definition for '{word}'")

        prompt = self.prompt_manager.render("misc/lookup", word=word)

        try:
            result = await self._make_structured_request(
                prompt,
                DictionaryEntryResponse,
                task_name="lookup_word",
            )

            if result.definitions:
                def_count = len(result.definitions)
                logger.success(
                    f"✨ Generated {def_count} definitions for '{word}' "
                    f"(confidence: {result.confidence:.1%})",
                )
            else:
                logger.warning(f"⚠️  AI generated empty response for '{word}'")

            return result
        except Exception as e:
            logger.error(f"❌ AI fallback generation failed for '{word}': {e}")
            raise

    async def extract_cluster_mapping(
        self,
        word: str,
        definitions: list[tuple[str, str, str]],
    ) -> ClusterMappingResponse:
        """Extract numerical mapping of clusters to definition IDs.

        Args:
            word: The word to extract mappings for.
            definitions: list of: (provider, part_of_speech, definition) tuples from providers.

        """
        start_time = time.perf_counter()
        def_count = len(definitions)

        logger.info(f"🔢 Extracting cluster mappings for '{word}' from {def_count} definitions")

        prompt = self.prompt_manager.render(
            "misc/meaning_extraction",
            word=word,
            definitions=definitions,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                ClusterMappingResponse,
                task_name="extract_cluster_mapping",
            )
            duration = time.perf_counter() - start_time

            # Log detailed cluster information
            total_defs_mapped = sum(len(cm.definition_indices) for cm in result.cluster_mappings)
            logger.success(
                f"🧮 Extracted {len(result.cluster_mappings)} meaning clusters for '{word}' "
                f"in {duration:.2f}s (mapped {total_defs_mapped}/{def_count} definitions)",
            )

            # Log each cluster for debugging
            for cluster in result.cluster_mappings:
                logger.debug(
                    f"  • Cluster '{cluster.cluster_id}': {cluster.cluster_description} "
                    f"({len(cluster.definition_indices)} definitions)",
                )

            log_metrics(
                stage="cluster_extraction",
                word=word,
                cluster_count=len(result.cluster_mappings),
                definition_count=def_count,
                mapped_count=total_defs_mapped,
                confidence=result.confidence,
                duration=duration,
            )
            return result
        except Exception as e:
            logger.error(f"❌ Cluster mapping extraction failed for '{word}': {e}")
            raise

    async def generate_anki_fill_blank(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        examples: str | None = None,
    ) -> AnkiFillBlankResponse:
        """Generate fill-in-the-blank flashcard using structured output."""
        prompt = self.prompt_manager.render(
            "misc/anki_fill_blank",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            examples=examples or "",
        )
        try:
            result = await self._make_structured_request(
                prompt,
                AnkiFillBlankResponse,
                task_name="generate_anki_fill_blank",
            )
            logger.debug(f"Generated fill-blank card for '{word}'")
            return result
        except Exception as e:
            logger.error(f"❌ Fill-blank generation failed for '{word}': {e}")
            raise

    async def generate_anki_best_describes(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        examples: str | None = None,
    ) -> AnkiMultipleChoiceResponse:
        """Generate best describes flashcard using structured output."""
        prompt = self.prompt_manager.render(
            "misc/anki_best_describes",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            examples=examples or "",
        )
        try:
            result = await self._make_structured_request(
                prompt,
                AnkiMultipleChoiceResponse,
                task_name="generate_anki_best_describes",
            )
            logger.debug(f"Generated best describes card for '{word}'")
            return result
        except Exception as e:
            logger.error(f"❌ Best describes generation failed for '{word}': {e}")
            raise

    async def synthesize_synonyms(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        existing_synonyms: list[str],
        count: int = 10,
    ) -> SynonymGenerationResponse:
        """Generate synonyms with efflorescence ranking."""
        logger.debug(f"🔗 Generating {count} synonyms for '{word}' ({part_of_speech})")

        prompt = self.prompt_manager.render(
            "synthesize/synonyms",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_synonyms=existing_synonyms,
            count=count,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                SynonymGenerationResponse,
                task_name="generate_synonyms",
            )

            synonym_count = len(result.synonyms)
            logger.success(
                f"✨ Generated {synonym_count} synonyms for '{word}' (confidence: {result.confidence:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Synonym generation failed for '{word}': {e}")
            raise

    async def suggestions(
        self,
        input_words: list[str] | None,
        count: int = 10,
    ) -> SuggestionsResponse:
        """Generate word suggestions based on input words.

        Args:
            input_words: List of up to 10 input words to base suggestions on
            count: Number of suggestions to generate (8-12)

        Returns:
            SuggestionsResponse with suggestions and analysis

        """
        limited_words = input_words[:10] if input_words else None
        suggestion_count = max(8, min(12, count))

        logger.info(
            f"🌸 Generating {suggestion_count} suggestions from {len(limited_words) if limited_words else 0} words",
        )

        prompt = self.prompt_manager.render(
            "misc/suggestions",
            input_words=limited_words,
            count=suggestion_count,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                SuggestionsResponse,
                task_name="generate_suggestions",
            )

            suggestions_count = len(result.suggestions)
            logger.success(
                f"✨ Generated {suggestions_count} suggestions (confidence: {result.confidence:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Suggestions generation failed: {e}")
            raise

    async def generate_facts(
        self,
        word: str,
        definition: str,
        count: int = 5,
        previous_words: list[str] | None = None,
    ) -> FactGenerationResponse:
        """Generate interesting facts about a word.

        Args:
            word: The word to generate facts about
            definition: Main definition of the word for context
            count: Number of facts to generate (3-8)
            previous_words: Previously searched words for connections

        Returns:
            FactGenerationResponse with facts and metadata

        """
        fact_count = max(3, min(8, count))
        limited_previous = previous_words[:20] if previous_words else []

        logger.info(
            f"📚 Generating {fact_count} facts for '{word}' with {len(limited_previous)} previous words",
        )

        prompt = self.prompt_manager.render(
            "generate/facts",
            word=word,
            definition=definition,
            count=fact_count,
            previous_words=limited_previous,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                FactGenerationResponse,
                task_name="generate_facts",
            )

            facts_count = len(result.facts)
            categories_str = ", ".join(result.categories) if result.categories else "general"
            logger.success(
                f"✨ Generated {facts_count} facts for '{word}' "
                f"({categories_str}, confidence: {result.confidence:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Fact generation failed for '{word}': {e}")
            raise

    async def synthesize_antonyms(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
        existing_antonyms: list[str],
        count: int = 5,
    ) -> AntonymResponse:
        """Generate antonyms for a definition.

        Args:
            word: The word
            definition: The definition text
            part_of_speech: Part of speech

        Returns:
            AntonymResponse with list of antonyms

        """
        prompt = self.prompt_manager.render(
            "synthesize/antonyms",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
            existing_antonyms=existing_antonyms,
            count=count,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                AntonymResponse,
                task_name="generate_antonyms",
            )
            logger.info(f"Generated {len(result.antonyms)} antonyms for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Antonym generation failed for '{word}': {e}")
            raise

    async def extract_etymology(
        self,
        word: str,
        provider_data: list[dict[str, Any]],
    ) -> EtymologyResponse:
        """Extract etymology from provider data.

        Args:
            word: The word
            provider_data: Raw data from providers

        Returns:
            EtymologyResponse with etymology information

        """
        prompt = self.prompt_manager.render(
            "synthesize/etymology",
            word=word,
            provider_data=provider_data,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                EtymologyResponse,
                task_name="synthesize_etymology",
            )
            logger.info(f"Extracted etymology for '{word}' (origin: {result.origin_language})")
            return result
        except Exception as e:
            logger.error(f"Etymology extraction failed for '{word}': {e}")
            raise

    async def identify_word_forms(
        self,
        word: str,
        part_of_speech: str,
    ) -> WordFormResponse:
        """Identify word forms (plural, past tense, etc.).

        Args:
            word: The word
            part_of_speech: Part of speech

        Returns:
            WordFormResponse with word forms

        """
        prompt = self.prompt_manager.render(
            "generate/word_forms",
            word=word,
            part_of_speech=part_of_speech,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                WordFormResponse,
                task_name="generate_word_forms",
            )
            logger.info(f"Identified {len(result.forms)} word forms for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Word form identification failed for '{word}': {e}")
            raise

    async def assess_frequency_band(
        self,
        word: str,
        definition: str,
    ) -> FrequencyBandResponse:
        """Assess frequency band (1-5) for a word.

        Args:
            word: The word
            definition: The definition for context

        Returns:
            FrequencyBandResponse with band assessment

        """
        prompt = self.prompt_manager.render(
            "assess/frequency",
            word=word,
            definition=definition,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                FrequencyBandResponse,
                task_name="assess_frequency",
            )
            logger.info(f"Assessed frequency band {result.band} for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Frequency assessment failed for '{word}': {e}")
            raise

    async def classify_register(
        self,
        definition: str,
    ) -> RegisterClassificationResponse:
        """Classify register (formal, informal, etc.) of a definition.

        Args:
            definition: The definition text

        Returns:
            RegisterClassificationResponse with classification

        """
        prompt = self.prompt_manager.render("assess/register", definition=definition)

        try:
            result = await self._make_structured_request(
                prompt,
                RegisterClassificationResponse,
                task_name="classify_register",
            )
            logger.info(f"Classified register as '{result.language_register}'")
            return result
        except Exception as e:
            logger.error(f"Register classification failed: {e}")
            raise

    async def assess_domain(
        self,
        definition: str,
    ) -> DomainIdentificationResponse:
        """Identify domain/field of a definition.

        Args:
            definition: The definition text

        Returns:
            DomainIdentificationResponse with domain

        """
        prompt = self.prompt_manager.render("assess/domain", definition=definition)

        try:
            result = await self._make_structured_request(
                prompt,
                DomainIdentificationResponse,
                task_name="classify_domain",
            )
            logger.info(f"Identified domain as '{result.domain}'")
            return result
        except Exception as e:
            logger.error(f"Domain identification failed: {e}")
            raise

    async def assess_cefr_level(
        self,
        word: str,
        definition: str,
    ) -> CEFRLevelResponse:
        """Assess CEFR level (A1-C2) for a word.

        Args:
            word: The word
            definition: The definition for context

        Returns:
            CEFRLevelResponse with level assessment

        """
        prompt = self.prompt_manager.render(
            "assess/cefr",
            word=word,
            definition=definition,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                CEFRLevelResponse,
                task_name="assess_cefr_level",
            )
            logger.info(f"Assessed CEFR level {result.level} for '{word}'")
            return result
        except Exception as e:
            logger.error(f"CEFR assessment failed for '{word}': {e}")
            raise

    async def assess_grammar_patterns(
        self,
        definition: str,
        part_of_speech: str,
    ) -> GrammarPatternResponse:
        """Extract grammar patterns from a definition.

        Args:
            definition: The definition text
            part_of_speech: Part of speech

        Returns:
            GrammarPatternResponse with patterns

        """
        prompt = self.prompt_manager.render(
            "assess/grammar_patterns",
            definition=definition,
            part_of_speech=part_of_speech,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                GrammarPatternResponse,
                task_name="identify_grammar_patterns",
            )
            logger.info(f"Extracted {len(result.patterns)} grammar patterns")
            return result
        except Exception as e:
            logger.error(f"Grammar pattern extraction failed: {e}")
            raise

    async def assess_collocations(
        self,
        word: str,
        definition: str,
        part_of_speech: str,
    ) -> CollocationResponse:
        """Identify common collocations for a word.

        Args:
            word: The word
            definition: The definition for context
            part_of_speech: Part of speech

        Returns:
            CollocationResponse with collocations

        """
        prompt = self.prompt_manager.render(
            "assess/collocations",
            word=word,
            definition=definition,
            part_of_speech=part_of_speech,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                CollocationResponse,
                task_name="generate_collocations",
            )
            logger.info(f"Identified {len(result.collocations)} collocations for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Collocation identification failed for '{word}': {e}")
            raise

    async def usage_note_generation(
        self,
        word: str,
        definition: str,
    ) -> UsageNoteResponse:
        """Generate usage notes for a definition.

        Args:
            word: The word
            definition: The definition text

        Returns:
            UsageNoteResponse with usage guidance

        """
        prompt = self.prompt_manager.render(
            "misc/usage_note_generation",
            word=word,
            definition=definition,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                UsageNoteResponse,
                task_name="generate_usage_notes",
            )
            logger.info(f"Generated {len(result.notes)} usage notes for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Usage note generation failed for '{word}': {e}")
            raise

    async def assess_regional_variants(
        self,
        definition: str,
    ) -> RegionalVariantResponse:
        """Detect regional variants for a definition.

        Args:
            definition: The definition text

        Returns:
            RegionalVariantResponse with regions

        """
        prompt = self.prompt_manager.render("assess/regional_variants", definition=definition)

        try:
            result = await self._make_structured_request(
                prompt,
                RegionalVariantResponse,
                task_name="identify_regional_variants",
            )
            logger.info(f"Detected regional variants: {', '.join(result.regions)}")
            return result
        except Exception as e:
            logger.error(f"Regional variant detection failed: {e}")
            raise

    async def validate_query(
        self,
        query: str,
    ) -> QueryValidationResponse:
        """Validate if query seeks word suggestions.

        Args:
            query: User's search query

        Returns:
            QueryValidationResponse with validation result

        """
        prompt = self.prompt_manager.render("misc/query_validation", query=query)

        try:
            result = await self._make_structured_request(
                prompt,
                QueryValidationResponse,
                task_name="validate_query",
            )
            logger.info(f"Query validation: {result.is_valid} - {result.reason}")
            return result
        except Exception as e:
            logger.error(f"Query validation failed: {e}")
            raise

    async def suggest_words(
        self,
        query: str,
        count: int = 10,
    ) -> WordSuggestionResponse:
        """Generate word suggestions from descriptive query.

        Args:
            query: Descriptive query for word suggestions
            count: Number of suggestions to generate

        Returns:
            WordSuggestionResponse with ranked suggestions

        """
        prompt = self.prompt_manager.render(
            "misc/word_suggestion",
            query=query,
            count=count,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                WordSuggestionResponse,
                task_name="suggest_words",
            )
            logger.info(f"Generated {len(result.suggestions)} word suggestions")
            return result
        except Exception as e:
            logger.error(f"Word suggestion failed: {e}")
            raise

    async def deduplicate_definitions(
        self,
        word: str,
        definitions: list[Definition],
        part_of_speech: str | None = None,
    ) -> DeduplicationResponse:
        """Deduplicate near-duplicate definitions using semantic similarity.

        Args:
            word: The word being defined
            definitions: List of Definition objects to deduplicate
            part_of_speech: Optional specific part of speech to focus on

        Returns:
            DeduplicationResponse with deduplicated definitions

        """
        logger.info(
            f"🔍 Deduplicating {len(definitions)} definitions for '{word}'"
            f"{f' ({part_of_speech})' if part_of_speech else ''}",
        )

        prompt = self.prompt_manager.render(
            "synthesize/deduplicate",
            word=word,
            definitions=definitions,
            part_of_speech=part_of_speech,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                DeduplicationResponse,
                task_name="deduplicate_definitions",
            )

            logger.success(
                f"✨ Deduplicated {len(definitions)} → {len(result.deduplicated_definitions)} "
                f"definitions (removed {result.removed_count}, confidence: {result.confidence:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Definition deduplication failed for '{word}': {e}")
            raise

    async def generate_word_of_the_day(
        self,
        context: str | None = None,
        previous_words: list[str] | None = None,
    ) -> WordOfTheDayResponse:
        """Generate a compelling Word of the Day.

        Args:
            context: Optional context to steer word selection
            previous_words: Previously used words to avoid

        Returns:
            WordOfTheDayResponse with educational word content

        """
        logger.info(
            f"📖 Generating Word of the Day"
            f"{f' with context: {context}' if context else ''}"
            f"{f' avoiding {len(previous_words)} previous words' if previous_words else ''}",
        )

        prompt = self.prompt_manager.render(
            "wotd/word_of_the_day",
            context=context,
            previous_words=previous_words,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                WordOfTheDayResponse,
                task_name="generate_word_of_the_day",
            )

            logger.success(
                f"✨ Generated Word of the Day: '{result.word}' "
                f"({result.difficulty_level}, confidence: {result.confidence:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Word of the Day generation failed: {e}")
            raise

    async def generate_synthetic_corpus(
        self,
        style: str,
        complexity: str,
        era: str,
        num_words: int,
        theme: str | None = None,
        avoid_words: list[str] | None = None,
    ) -> SyntheticCorpusResponse:
        """Generate a synthetic corpus for WOTD training.

        Args:
            style: Target style category (classical, modern, romantic, neutral)
            complexity: Target complexity level (beautiful, simple, complex, plain)
            era: Target era (shakespearean, victorian, modernist, contemporary)
            num_words: Number of words to generate
            theme: Optional thematic focus
            avoid_words: Words to avoid in generation

        Returns:
            SyntheticCorpusResponse with generated corpus

        """
        logger.info(
            f"🧬 Generating synthetic corpus: {style}/{complexity}/{era} "
            f"({num_words} words)"
            f"{f' themed: {theme}' if theme else ''}",
        )

        prompt = self.prompt_manager.render(
            "wotd/synthetic_corpus",
            style=style,
            complexity=complexity,
            era=era,
            num_words=num_words,
            theme=theme,
            avoid_words=avoid_words,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                SyntheticCorpusResponse,
                task_name="generate_synthetic_corpus",
                tier=ModelTier.HIGH,  # Use GPT-5 or best available model
            )

            logger.success(
                f"✨ Generated {result.total_generated} words for {style}/{complexity}/{era} corpus "
                f"(quality: {result.quality_score:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Synthetic corpus generation failed: {e}")
            raise

    async def generate_text(
        self,
        request: TextGenerationRequest,
    ) -> TextGenerationResponse:
        """Generate text from a prompt.

        Args:
            request: Text generation request with prompt and parameters

        Returns:
            TextGenerationResponse with generated text

        """
        logger.info(
            f"📝 Generating text (max_tokens: {request.max_tokens}, temp: {request.temperature})",
        )

        try:
            result = await self._make_structured_request(
                request.prompt,
                TextGenerationResponse,
                task_name="text_generation",
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            logger.success(f"✨ Generated {len(result.text)} characters of text")
            return result
        except Exception as e:
            logger.error(f"❌ Text generation failed: {e}")
            raise

    async def augment_literature_vocabulary(
        self,
        request: LiteratureAugmentationRequest,
    ) -> LiteratureAugmentationResponse:
        """Generate augmented vocabulary based on literary samples.

        Args:
            request: Literature augmentation request

        Returns:
            LiteratureAugmentationResponse with augmented words

        """
        logger.info(
            f"📚 Augmenting {request.author}'s vocabulary: {len(request.sample_words)} samples → "
            f"{request.target_count} variants",
        )

        # Ultra-lean prompt - minimal tokens, maximum efficiency
        words = ", ".join(request.sample_words[:10])  # Use only 10 words max
        prompt = f"{request.transformation_prompt}: {words}\n{request.target_count} words:"

        try:
            result = await self._make_structured_request(
                prompt,
                LiteratureAugmentationResponse,
                task_name="literature_augmentation",
                max_tokens=50,  # Ultra-lean output
                # Temperature handled automatically for GPT-5 series models
            )

            logger.success(
                f"✨ Generated {len(result.words)} augmented words for {request.author} "
                f"(confidence: {result.confidence:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Literature augmentation failed for {request.author}: {e}")
            raise

    async def analyze_literature_corpus(
        self,
        author: str,
        words: list[str],
        period: str | None = None,
        genre: str | None = None,
        word_frequencies: dict[str, int] | None = None,
    ) -> LiteratureAnalysisResponse:
        """Analyze literature corpus and generate semantic ID using template system.

        This method uses the literature_analysis.md prompt template to perform
        comprehensive analysis of a literary corpus and generate semantic IDs.

        Args:
            author: Author name
            words: List of words to analyze
            period: Literary period (optional)
            genre: Primary genre (optional)
            word_frequencies: Word frequency data (optional)

        Returns:
            LiteratureAnalysisResponse with complete analysis and semantic ID

        """
        logger.info(f"📚 Analyzing literature corpus for {author}: {len(words)} words")

        # Use the ultra-lean literature analysis prompt template
        prompt = self.prompt_manager.render(
            "wotd/literature_analysis_lean",
            author=author,
            words=words,
        )

        try:
            result = await self._make_structured_request(
                prompt,
                LiteratureAnalysisResponse,
                task_name="literature_analysis",
                max_tokens=30,  # Ultra-lean semantic ID output
                # Temperature handled automatically based on model type (reasoning models don't use temperature)
            )

            logger.success(
                f"✨ Analyzed {author} corpus: semantic ID [{result.semantic_id.style},"
                f"{result.semantic_id.complexity},{result.semantic_id.era},"
                f"{result.semantic_id.variation}] (quality: {result.quality_score:.1%})",
            )
            return result
        except Exception as e:
            logger.error(f"❌ Literature corpus analysis failed for {author}: {e}")
            raise


# Global singleton instance
_openai_connector: OpenAIConnector | None = None


def get_openai_connector(
    config_path: str | Path | None = None,
    force_recreate: bool = False,
) -> OpenAIConnector:
    """Get or create the global OpenAI connector singleton.

    Args:
        config_path: Path to configuration file (defaults to auth/config.toml)
        force_recreate: Force recreation of the connector

    Returns:
        Initialized OpenAI connector instance

    """
    global _openai_connector

    if _openai_connector is None or force_recreate:

        from ..utils.config import Config

        logger.info("Initializing OpenAI connector singleton")
        config = Config.from_file(config_path)

        api_key = config.openai.api_key
        model_name = config.openai.model

        # Log configuration status (without exposing the key)
        logger.info(f"OpenAI model: {model_name}")
        logger.info(
            f"API key configured: {'Yes' if api_key and len(api_key) > 20 else 'No'}"
        )

        # Only set temperature for non-reasoning models
        temperature = None
        if not model_name.startswith(("o1", "o3")):
            temperature = 0.7  # Default temperature for non-reasoning models

        _openai_connector = OpenAIConnector(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
        )
        logger.success("OpenAI connector singleton initialized")

    return _openai_connector
