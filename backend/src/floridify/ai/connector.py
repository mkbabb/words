"""OpenAI connector with modern async API and structured outputs."""

from __future__ import annotations

import asyncio
import time
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..caching.decorators import cached_api_call
from ..models import Definition
from ..utils.logging import get_logger, log_metrics
from .models import (
    AnkiFillBlankResponse,
    AnkiMultipleChoiceResponse,
    ClusterMappingResponse,
    DictionaryEntryResponse,
    ExampleGenerationResponse,
    FactGenerationResponse,
    PronunciationResponse,
    SuggestionsResponse,
    SynonymGenerationResponse,
    SynthesisResponse,
    AntonymResponse,
    EtymologyResponse,
    WordFormResponse,
    RegisterClassificationResponse,
    DomainIdentificationResponse,
    FrequencyBandResponse,
    RegionalVariantResponse,
    CEFRLevelResponse,
    UsageNoteResponse,
    CollocationResponse,
    GrammarPatternResponse,
)
from .templates import PromptTemplateManager

T = TypeVar("T", bound=BaseModel)

logger = get_logger(__name__)


class OpenAIConnector:
    """Modern OpenAI connector with structured outputs and caching."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        temperature: float | None = None,
        max_tokens: int = 1000,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key)

        self.model_name = model_name

        self.embedding_model = embedding_model

        self.temperature = temperature

        self.max_tokens = max_tokens

        self.template_manager = PromptTemplateManager()

    @cached_api_call(
        ttl_hours=24.0,  # Cache OpenAI responses for 24 hours
        use_file_cache=False,  # Use in-memory cache for API responses
        key_func=lambda self, prompt, response_model, **kwargs: (
            "openai_structured",
            self.model_name,
            hash(prompt),
            response_model.__name__,
            tuple(sorted(kwargs.items())),
        ),
    )
    async def _make_structured_request(
        self,
        prompt: str,
        response_model: type[T],
        **kwargs: Any,
    ) -> T:
        """Make a structured request to OpenAI with caching."""
        start_time = time.perf_counter()
        retry_count = 0
        max_retries = 3

        # Prepare request parameters
        request_params: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            **kwargs,
        }

        # Add temperature if supported
        if self.temperature is not None:
            request_params["temperature"] = self.temperature

        # Use structured outputs if available
        if hasattr(self.client.beta.chat.completions, "parse"):
            request_params["response_format"] = response_model

        while retry_count < max_retries:
            try:
                # Log API call details
                logger.debug(
                    f"🤖 OpenAI API call: model={self.model_name}, "
                    f"response_type={response_model.__name__}, "
                    f"prompt_length={len(prompt)}, retry={retry_count}"
                )

                # Make the API call
                api_start = time.perf_counter()
                response = await self.client.beta.chat.completions.parse(**request_params)
                api_duration = time.perf_counter() - api_start

                # Extract token usage
                token_usage = {}
                if hasattr(response, "usage") and response.usage:
                    token_usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }

                # Log successful API call
                log_metrics(
                    api_call="openai",
                    model=self.model_name,
                    response_type=response_model.__name__,
                    duration=api_duration,
                    retry_count=retry_count,
                    **token_usage,
                )

                if response.choices[0].message.parsed:
                    result = response.choices[0].message.parsed
                    # Store token usage on the result if it has that attribute
                    if hasattr(result, "token_usage"):
                        result.token_usage = token_usage
                else:
                    # Fallback to manual parsing
                    content = response.choices[0].message.content
                    if content:
                        result = response_model.model_validate_json(content)
                    else:
                        raise ValueError("No content in response")

                total_duration = time.perf_counter() - start_time
                logger.info(
                    f"✅ OpenAI API success: {response_model.__name__} "
                    f"in {total_duration:.2f}s (tokens: {token_usage.get('total_tokens', 'N/A')})"
                )

                return result

            except Exception as e:
                retry_count += 1
                duration = time.perf_counter() - start_time

                if retry_count < max_retries:
                    wait_time = retry_count * 2  # Exponential backoff
                    logger.warning(
                        f"⚠️  OpenAI API error (attempt {retry_count}/{max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ OpenAI API failed after {max_retries} attempts "
                        f"({duration:.2f}s total): {e}"
                    )
                    log_metrics(
                        api_call="openai_error",
                        model=self.model_name,
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

        prompt = self.template_manager.get_synthesis_prompt(
            word=word,
            definitions=definitions,
            meaning_cluster=meaning_cluster,
        )

        try:
            result = await self._make_structured_request(prompt, SynthesisResponse)
            # Success logging handled by synthesizer context
            return result
        except Exception as e:
            logger.error(f"❌ Definition synthesis failed for '{word}' ({meaning_cluster}): {e}")
            raise

    async def examples(
        self,
        word: str,
        word_type: str,
        definition: str,
        count: int = 1,
    ) -> ExampleGenerationResponse:
        """Generate modern usage examples."""
        logger.debug(f"📝 Generating {count} example sentence(s) for '{word}' ({word_type})")

        prompt = self.template_manager.get_example_prompt(word, definition, word_type, count)

        try:
            result = await self._make_structured_request(prompt, ExampleGenerationResponse)
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
        prompt = self.template_manager.get_pronunciation_prompt(word)

        return await self._make_structured_request(prompt, PronunciationResponse)

    async def lookup_fallback(self, word: str) -> DictionaryEntryResponse | None:
        """Generate AI fallback provider data."""
        logger.info(f"🤖 Generating AI fallback definition for '{word}'")

        prompt = self.template_manager.get_lookup_prompt(word)

        try:
            result = await self._make_structured_request(prompt, DictionaryEntryResponse)

            if result.provider_data is None:
                logger.info(f"🚫 AI identified '{word}' as nonsense/invalid")
                return None
            elif result.provider_data:
                def_count = len(result.provider_data.definitions)
                logger.success(
                    f"✨ Generated {def_count} definitions for '{word}' "
                    f"(confidence: {result.confidence:.1%})"
                )
            else:
                logger.warning(f"⚠️  AI generated empty response for '{word}'")

            return result
        except Exception as e:
            logger.error(f"❌ AI fallback generation failed for '{word}': {e}")
            raise

    async def extract_cluster_mapping(
        self, word: str, definitions: list[tuple[str, str, str]]
    ) -> ClusterMappingResponse:
        """Extract numerical mapping of clusters to definition IDs.

        Args:
            word: The word to extract mappings for.
            definitions: list of: (provider, word_type, definition) tuples from providers.
        """
        start_time = time.perf_counter()
        def_count = len(definitions)

        logger.info(f"🔢 Extracting cluster mappings for '{word}' from {def_count} definitions")

        prompt = self.template_manager.get_meaning_extraction_prompt(word, definitions)

        try:
            result = await self._make_structured_request(prompt, ClusterMappingResponse)
            duration = time.perf_counter() - start_time

            # Log detailed cluster information
            total_defs_mapped = sum(len(cm.definition_indices) for cm in result.cluster_mappings)
            logger.success(
                f"🧮 Extracted {len(result.cluster_mappings)} meaning clusters for '{word}' "
                f"in {duration:.2f}s (mapped {total_defs_mapped}/{def_count} definitions)"
            )

            # Log each cluster for debugging
            for cluster in result.cluster_mappings:
                logger.debug(
                    f"  • Cluster '{cluster.cluster_id}': {cluster.cluster_description} "
                    f"({len(cluster.definition_indices)} definitions)"
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
        self, word: str, definition: str, word_type: str, examples: str | None = None
    ) -> AnkiFillBlankResponse:
        """Generate fill-in-the-blank flashcard using structured output."""
        prompt = self.template_manager.render_template(
            "anki_fill_blank",
            word=word,
            definition=definition,
            word_type=word_type,
            examples=examples or "",
        )
        try:
            result = await self._make_structured_request(prompt, AnkiFillBlankResponse)
            logger.debug(f"Generated fill-blank card for '{word}'")
            return result
        except Exception as e:
            logger.error(f"❌ Fill-blank generation failed for '{word}': {e}")
            raise

    async def generate_anki_best_describes(
        self, word: str, definition: str, word_type: str, examples: str | None = None
    ) -> AnkiMultipleChoiceResponse:
        """Generate best describes flashcard using structured output."""
        prompt = self.template_manager.render_template(
            "anki_best_describes",
            word=word,
            definition=definition,
            word_type=word_type,
            examples=examples or "",
        )
        try:
            result = await self._make_structured_request(prompt, AnkiMultipleChoiceResponse)
            logger.debug(f"Generated best describes card for '{word}'")
            return result
        except Exception as e:
            logger.error(f"❌ Best describes generation failed for '{word}': {e}")
            raise

    async def synonyms(
        self, word: str, definition: str, word_type: str, count: int = 10
    ) -> SynonymGenerationResponse:
        """Generate synonyms with efflorescence ranking."""
        logger.debug(f"🔗 Generating {count} synonyms for '{word}' ({word_type})")

        prompt = self.template_manager.get_synonyms_prompt(
            word=word,
            definition=definition,
            word_type=word_type,
            count=count,
        )

        try:
            result = await self._make_structured_request(prompt, SynonymGenerationResponse)

            synonym_count = len(result.synonyms)
            logger.success(
                f"✨ Generated {synonym_count} synonyms for '{word}' (confidence: {result.confidence:.1%})"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Synonym generation failed for '{word}': {e}")
            raise

    @cached_api_call(
        ttl_hours=24.0,  # Suggestions change slowly
        key_func=lambda self, input_words, count: (
            "suggestions",
            tuple(sorted(input_words)) if input_words else None,
            count,
        ),
    )
    async def suggestions(
        self, input_words: list[str] | None, count: int = 10
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
            f"🌸 Generating {suggestion_count} suggestions from {len(limited_words) if limited_words else 0} words"
        )

        prompt = self.template_manager.get_suggestions_prompt(
            input_words=limited_words,
            count=suggestion_count,
        )

        try:
            result = await self._make_structured_request(prompt, SuggestionsResponse)

            suggestions_count = len(result.suggestions)
            logger.success(
                f"✨ Generated {suggestions_count} suggestions (confidence: {result.confidence:.1%})"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Suggestions generation failed: {e}")
            raise

    @cached_api_call(
        ttl_hours=48.0,  # Facts don't change frequently
        key_func=lambda self, word, definition, count, previous_words: (
            "facts",
            word,
            definition[:100],  # Truncate for cache key
            count,
            tuple(sorted(previous_words)) if previous_words else None,
        ),
    )
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
            f"📚 Generating {fact_count} facts for '{word}' with {len(limited_previous)} previous words"
        )

        prompt = self.template_manager.get_fact_generation_prompt(
            word=word,
            definition=definition,
            count=fact_count,
            previous_words=limited_previous,
        )

        try:
            result = await self._make_structured_request(prompt, FactGenerationResponse)

            facts_count = len(result.facts)
            categories_str = ", ".join(result.categories) if result.categories else "general"
            logger.success(
                f"✨ Generated {facts_count} facts for '{word}' "
                f"({categories_str}, confidence: {result.confidence:.1%})"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Fact generation failed for '{word}': {e}")
            raise
    
    # Alias for router compatibility
    async def _make_request(self, prompt: str, response_model: type[T], **kwargs: Any) -> T:
        """Alias for _make_structured_request for backward compatibility."""
        return await self._make_structured_request(prompt, response_model, **kwargs)

    async def generate_antonyms(
        self,
        word: str,
        definition: str,
        word_type: str,
    ) -> AntonymResponse:
        """Generate antonyms for a definition.

        Args:
            word: The word
            definition: The definition text
            word_type: Part of speech

        Returns:
            AntonymResponse with list of antonyms
        """
        prompt = self.template_manager.get_antonym_prompt(
            word=word,
            definition=definition,
            word_type=word_type,
        )
        
        try:
            result = await self._make_structured_request(prompt, AntonymResponse)
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
        prompt = self.template_manager.get_etymology_prompt(
            word=word,
            provider_data=provider_data,
        )
        
        try:
            result = await self._make_structured_request(prompt, EtymologyResponse)
            logger.info(f"Extracted etymology for '{word}' (origin: {result.origin_language})")
            return result
        except Exception as e:
            logger.error(f"Etymology extraction failed for '{word}': {e}")
            raise

    async def identify_word_forms(
        self,
        word: str,
        word_type: str,
    ) -> WordFormResponse:
        """Identify word forms (plural, past tense, etc.).

        Args:
            word: The word
            word_type: Part of speech

        Returns:
            WordFormResponse with word forms
        """
        prompt = self.template_manager.get_word_forms_prompt(
            word=word,
            word_type=word_type,
        )
        
        try:
            result = await self._make_structured_request(prompt, WordFormResponse)
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
        prompt = self.template_manager.get_frequency_prompt(
            word=word,
            definition=definition,
        )
        
        try:
            result = await self._make_structured_request(prompt, FrequencyBandResponse)
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
        prompt = self.template_manager.get_register_prompt(definition=definition)
        
        try:
            result = await self._make_structured_request(prompt, RegisterClassificationResponse)
            logger.info(f"Classified register as '{result.register}'")
            return result
        except Exception as e:
            logger.error(f"Register classification failed: {e}")
            raise

    async def identify_domain(
        self,
        definition: str,
    ) -> DomainIdentificationResponse:
        """Identify domain/field of a definition.

        Args:
            definition: The definition text

        Returns:
            DomainIdentificationResponse with domain
        """
        prompt = self.template_manager.get_domain_prompt(definition=definition)
        
        try:
            result = await self._make_structured_request(prompt, DomainIdentificationResponse)
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
        prompt = self.template_manager.get_cefr_prompt(
            word=word,
            definition=definition,
        )
        
        try:
            result = await self._make_structured_request(prompt, CEFRLevelResponse)
            logger.info(f"Assessed CEFR level {result.level} for '{word}'")
            return result
        except Exception as e:
            logger.error(f"CEFR assessment failed for '{word}': {e}")
            raise

    async def extract_grammar_patterns(
        self,
        definition: str,
        word_type: str,
    ) -> GrammarPatternResponse:
        """Extract grammar patterns from a definition.

        Args:
            definition: The definition text
            word_type: Part of speech

        Returns:
            GrammarPatternResponse with patterns
        """
        prompt = self.template_manager.get_grammar_patterns_prompt(
            definition=definition,
            word_type=word_type,
        )
        
        try:
            result = await self._make_structured_request(prompt, GrammarPatternResponse)
            logger.info(f"Extracted {len(result.patterns)} grammar patterns")
            return result
        except Exception as e:
            logger.error(f"Grammar pattern extraction failed: {e}")
            raise

    async def identify_collocations(
        self,
        word: str,
        definition: str,
        word_type: str,
    ) -> CollocationResponse:
        """Identify common collocations for a word.

        Args:
            word: The word
            definition: The definition for context
            word_type: Part of speech

        Returns:
            CollocationResponse with collocations
        """
        prompt = self.template_manager.get_collocations_prompt(
            word=word,
            definition=definition,
            word_type=word_type,
        )
        
        try:
            result = await self._make_structured_request(prompt, CollocationResponse)
            logger.info(f"Identified {len(result.collocations)} collocations for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Collocation identification failed for '{word}': {e}")
            raise

    async def generate_usage_notes(
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
        prompt = self.template_manager.get_usage_notes_prompt(
            word=word,
            definition=definition,
        )
        
        try:
            result = await self._make_structured_request(prompt, UsageNoteResponse)
            logger.info(f"Generated {len(result.notes)} usage notes for '{word}'")
            return result
        except Exception as e:
            logger.error(f"Usage note generation failed for '{word}': {e}")
            raise

    async def detect_regional_variants(
        self,
        definition: str,
    ) -> RegionalVariantResponse:
        """Detect regional variants for a definition.

        Args:
            definition: The definition text

        Returns:
            RegionalVariantResponse with regions
        """
        prompt = self.template_manager.get_regional_variants_prompt(definition=definition)
        
        try:
            result = await self._make_structured_request(prompt, RegionalVariantResponse)
            logger.info(f"Detected regional variants: {', '.join(result.regions)}")
            return result
        except Exception as e:
            logger.error(f"Regional variant detection failed: {e}")
            raise
