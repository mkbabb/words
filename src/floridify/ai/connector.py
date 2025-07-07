"""OpenAI connector with modern async API and structured outputs."""

from __future__ import annotations

from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..caching.decorators import cached_api_call, openai_cache_key
from ..utils.logging import get_logger
from .models import (
    AnkiFillBlankResponse,
    AnkiMultipleChoiceResponse,
    DictionaryEntryResponse,
    ExampleGenerationResponse,
    MeaningClusterResponse,
    PronunciationResponse,
    SynonymGenerationResponse,
    SynthesisResponse,
)
from .templates import PromptTemplateManager

T = TypeVar('T', bound=BaseModel)

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

        try:
            # Make the API call
            response = await self.client.beta.chat.completions.parse(**request_params)

            if response.choices[0].message.parsed:
                result = response.choices[0].message.parsed
            else:
                # Fallback to manual parsing
                content = response.choices[0].message.content
                if content:
                    result = response_model.model_validate_json(content)
                else:
                    raise ValueError("No content in response")

            return result

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def synthesize_definitions(
        self,
        word: str,
        provider_definitions: list[tuple[str, str, str]],
        meaning_cluster: str | None = None,
    ) -> SynthesisResponse:
        """Synthesize definitions from multiple providers.

        Args:
            word: The word to synthesize definitions for.
            word_type: The type of the word (e.g., noun, verb).
            provider_definitions: List of (provider_name, definition) tuples.
        """

        prompt = self.template_manager.get_synthesis_prompt(
            word=word,
            provider_definitions=provider_definitions,
            meaning_cluster=meaning_cluster,
        )

        try:
            result = await self._make_structured_request(
                prompt, SynthesisResponse
            )
            # Success logging handled by synthesizer context
            return result
        except Exception as e:
            logger.error(
                f"❌ Definition synthesis failed for '{word}' ({meaning_cluster}): {e}"
            )
            raise

    async def generate_example(
        self,
        word: str,
        word_type: str,
        definition: str,
    ) -> ExampleGenerationResponse:
        """Generate modern usage example."""
        logger.debug(f"📝 Generating example sentence for '{word}' ({word_type})")

        prompt = self.template_manager.get_example_prompt(word, definition, word_type)

        try:
            result = await self._make_structured_request(
                prompt, ExampleGenerationResponse
            )
            if result.example_sentences:
                first_example = result.example_sentences[0]
                truncated = (
                    first_example[:50] + "..."
                    if len(first_example) > 50
                    else first_example
                )
                logger.debug(f"✏️  Generated example for '{word}': \"{truncated}\"")
            return result
        except Exception as e:
            logger.error(f"❌ Example generation failed for '{word}': {e}")
            raise

    async def generate_pronunciation(self, word: str) -> PronunciationResponse:
        """Generate pronunciation data."""
        prompt = self.template_manager.get_pronunciation_prompt(word)

        return await self._make_structured_request(
            prompt, PronunciationResponse
        )

    async def generate_fallback_entry(
        self, word: str
    ) -> DictionaryEntryResponse | None:
        """Generate AI fallback provider data."""
        logger.info(f"🤖 Generating AI fallback definition for '{word}'")

        prompt = self.template_manager.get_fallback_prompt(word)

        try:
            result = await self._make_structured_request(
                prompt, DictionaryEntryResponse
            )

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

    async def extract_meaning_clusters(
        self, word: str, definitions: list[tuple[str, str, str]]
    ) -> MeaningClusterResponse:
        """Extract distinct meaning clusters from provider definitions.

        Args:
            word: The word to extract meanings for.
            definitions: list of: (provider, word_type, definition) tuples from providers.
        """
        def_count = len(definitions)

        logger.info(
            f"🧠 Extracting meaning clusters for '{word}' from {def_count} definitions"
        )

        prompt = self.template_manager.get_meaning_extraction_prompt(word, definitions)

        try:
            result = await self._make_structured_request(
                prompt, MeaningClusterResponse
            )
            logger.success(
                f"🎯 Extracted {len(result.meaning_clusters)} meaning clusters for '{word}' "
                f"(confidence: {result.confidence:.1%})"
            )
            return result
        except Exception as e:
            logger.error(f"❌ Meaning extraction failed for '{word}': {e}")
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
            result = await self._make_structured_request(
                prompt, AnkiFillBlankResponse
            )
            logger.debug(f"Generated fill-blank card for '{word}'")
            return result
        except Exception as e:
            logger.error(f"❌ Fill-blank generation failed for '{word}': {e}")
            raise

    async def generate_anki_multiple_choice(
        self, word: str, definition: str, word_type: str, examples: str | None = None
    ) -> AnkiMultipleChoiceResponse:
        """Generate multiple choice flashcard using structured output."""
        prompt = self.template_manager.render_template(
            "anki_multiple_choice",
            word=word,
            definition=definition,
            word_type=word_type,
            examples=examples or "",
        )
        try:
            result = await self._make_structured_request(
                prompt, AnkiMultipleChoiceResponse
            )
            logger.debug(f"Generated multiple choice card for '{word}'")
            return result
        except Exception as e:
            logger.error(f"❌ Multiple choice generation failed for '{word}': {e}")
            raise

    async def generate_synonyms(
        self, word: str, definition: str, word_type: str, count: int = 10
    ) -> SynonymGenerationResponse:
        """Generate synonyms with efflorescence ranking."""
        logger.debug(f"🔗 Generating {count} synonyms for '{word}' ({word_type})")

        prompt = self.template_manager.get_synonym_generation_prompt(
            word=word,
            definition=definition,
            word_type=word_type,
            count=count,
        )

        try:
            result = await self._make_structured_request(
                prompt, SynonymGenerationResponse
            )
            
            synonym_count = len(result.synonyms)
            logger.success(f"✨ Generated {synonym_count} synonyms for '{word}' (confidence: {result.confidence:.1%})")
            return result
        except Exception as e:
            logger.error(f"❌ Synonym generation failed for '{word}': {e}")
            raise
