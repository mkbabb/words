"""Modern OpenAI API connector with structured outputs and proper model handling."""

from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from ..config import OpenAIConfig
from ..models import (
    Definition,
    Examples,
    GeneratedExample,
    ProviderData,
    Word,
    WordType,
)
from ..prompts.formatters import format_provider_context
from ..utils.logging import vprint
from .schemas import (
    DefinitionSynthesisResponse,
    ExampleGenerationResponse,
    WordTypeEnum,
    get_model_capabilities,
    is_reasoning_model,
)


class OpenAIConnector:
    """Modern OpenAI connector with structured outputs and proper model handling."""

    def __init__(self, config: OpenAIConfig, storage: Any = None) -> None:
        """Initialize OpenAI connector.

        Args:
            config: OpenAI configuration with API key and model settings
            storage: Optional MongoDB storage for caching
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key)
        self._rate_limiter = asyncio.Semaphore(5)  # Limit concurrent requests
        self.storage = storage

        # Get model capabilities
        self.capabilities = get_model_capabilities(config.model)

    async def generate_comprehensive_definition(
        self, word: str, provider_definitions: dict[str, ProviderData]
    ) -> ProviderData:
        """Generate AI-synthesized definition from multiple provider data with caching.

        Args:
            word: The word to generate definition for
            provider_definitions: Dictionary of provider data to synthesize

        Returns:
            ProviderData with AI-synthesized definitions and examples
        """
        # Try cache first if storage is available
        if self.storage:
            cache_key = f"ai_synthesis_{self.config.model}_{word}"
            cached_response = await self.storage.get_cached_response(
                word=cache_key,
                provider="ai_synthesis",
                max_age_hours=72,  # Cache AI synthesis for 3 days
            )
            if cached_response and "provider_data" in cached_response:
                vprint(f"Using cached AI synthesis for '{word}'")
                return ProviderData.model_validate(cached_response["provider_data"])

        async with self._rate_limiter:
            vprint(f"Generating new AI synthesis for '{word}'")
            # Generate synthesized definitions
            definitions = await self._generate_definitions_structured(word, provider_definitions)

            # Generate examples for each definition separately
            for definition in definitions:
                vprint(f"Generating examples for {word} ({definition.word_type.value})")
                examples = await self._generate_examples_structured(word, definition)
                definition.examples = examples

            result = ProviderData(
                provider_name="ai_synthesis",
                definitions=definitions,
                is_synthetic=True,
            )

            # Cache the result if storage is available
            if self.storage:
                cache_key = f"ai_synthesis_{self.config.model}_{word}"
                await self.storage.cache_api_response(
                    word=cache_key,
                    provider="ai_synthesis",
                    response_data={
                        "provider_data": result.model_dump(),
                        "model": self.config.model,
                        "generated_definitions": len(definitions),
                    },
                )
                vprint(f"Cached AI synthesis for '{word}' with {len(definitions)} definitions")

            return result

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate text embedding using OpenAI's embedding model with caching.

        Args:
            text: Text to generate embedding for

        Returns:
            Vector embedding as list of floats
        """
        # Try cache first if storage is available
        if self.storage:
            cache_key = f"embedding_{self.config.embedding_model}_{text}"
            cached_response = await self.storage.get_cached_response(
                word=cache_key,
                provider="openai_embeddings",
                max_age_hours=168,  # Cache embeddings for a week
            )
            if cached_response and "embedding" in cached_response:
                vprint(f"Using cached embedding for '{text}'")
                return list(cached_response["embedding"])

        async with self._rate_limiter:
            try:
                vprint(f"Generating new embedding for '{text}'")
                response = await self.client.embeddings.create(
                    model=self.config.embedding_model,
                    input=text,
                )
                embedding = response.data[0].embedding

                # Cache the embedding if storage is available
                if self.storage and embedding:
                    cache_key = f"embedding_{self.config.embedding_model}_{text}"
                    await self.storage.cache_api_response(
                        word=cache_key,
                        provider="openai_embeddings",
                        response_data={
                            "embedding": embedding,
                            "model": self.config.embedding_model,
                        },
                    )
                    vprint(f"Cached embedding for '{text}'")

                return embedding
            except Exception as e:
                print(f"Error generating embedding for '{text}': {e}")
                return []

    async def generate_word_embedding(self, word: Word) -> Word:
        """Generate embedding for a word and update the word object with caching.

        Args:
            word: Word object to generate embedding for

        Returns:
            Updated Word object with embedding
        """
        # Check if word already has embedding for this model
        if self.config.embedding_model in word.embedding:
            vprint(
                f"Word '{word.text}' already has embedding for model {self.config.embedding_model}"
            )
            return word

        embedding = await self.generate_embedding(word.text)
        if embedding:
            word.embedding[self.config.embedding_model] = embedding
            vprint(f"Added embedding to word '{word.text}' for model {self.config.embedding_model}")
        return word

    async def _generate_definitions_structured(
        self, word: str, provider_definitions: dict[str, ProviderData]
    ) -> list[Definition]:
        """Generate AI definitions using structured output.

        Args:
            word: The word to define
            provider_definitions: Dictionary of provider data

        Returns:
            List of AI-generated definitions
        """
        try:
            # Prepare context from all providers
            context = format_provider_context(word, provider_definitions)

            # Create structured prompt
            system_message = (
                "You are an expert lexicographer creating comprehensive dictionary entries. "
                "Analyze the provided dictionary definitions and create separate definitions for "
                "EACH word type/part of speech found in the source material."
            )

            user_prompt = f"""Analyze the following dictionary definitions and create comprehensive,
synthesized definitions for the word "{word}".

{context}

CRITICAL INSTRUCTIONS:
1. Create a SEPARATE definition for EACH different word type/part of speech 
   (noun, verb, adjective, etc.)
2. Do NOT combine different word types into a single definition
3. For words with multiple meanings within the same word type, choose the most 
   common/important meaning
4. Synthesize the best aspects of definitions within each word type
5. Include ALL major word types present in the source material
6. Make definitions clear, concise, and accessible to modern readers

Example: If "run" appears as both a verb and a noun in the sources, create TWO separate definitions:
- One definition with word_type: "verb" 
- One definition with word_type: "noun"

Return your response as a structured JSON with an array of definitions, one per word type."""

            # Build request parameters based on model capabilities
            request_params = self._build_request_params(
                system_message=system_message,
                user_prompt=user_prompt,
                response_schema=DefinitionSynthesisResponse,
            )

            response = await self.client.chat.completions.create(**request_params)

            # Parse structured response
            if response.choices[0].message.content:
                try:
                    parsed_response = DefinitionSynthesisResponse.model_validate_json(
                        response.choices[0].message.content
                    )
                    return self._convert_ai_definitions(parsed_response.definitions)
                except ValidationError as e:
                    vprint(f"Failed to parse structured response for '{word}': {e}")
                    return []

            return []

        except Exception as e:
            vprint(f"Error generating definitions for '{word}': {e}")
            return []

    async def _generate_examples_structured(self, word: str, definition: Definition) -> Examples:
        """Generate examples using structured output.

        Args:
            word: The word to generate examples for
            definition: Definition to generate examples for

        Returns:
            Examples object with generated sentences
        """
        try:
            system_message = (
                "You are a creative writing assistant generating natural, modern example sentences."
            )

            user_prompt = f"""Generate 2 natural, modern example sentences for the word "{word}" 
used as a {definition.word_type.value}.

Definition: {definition.definition}

Requirements:
- Use contemporary, natural language
- Show the word in realistic contexts
- Make examples engaging and memorable
- Ensure examples clearly demonstrate the meaning
- Use the EXACT word "{word}" in each sentence (not variations or related forms)

Return your response as structured JSON with an array of example sentences."""

            # Build request parameters
            request_params = self._build_request_params(
                system_message=system_message,
                user_prompt=user_prompt,
                response_schema=ExampleGenerationResponse,
            )

            response = await self.client.chat.completions.create(**request_params)

            # Parse structured response
            if response.choices[0].message.content:
                try:
                    parsed_response = ExampleGenerationResponse.model_validate_json(
                        response.choices[0].message.content
                    )

                    examples = Examples()
                    for ex in parsed_response.examples:
                        examples.generated.append(
                            GeneratedExample(sentence=ex.sentence, regenerable=True)
                        )
                    return examples
                except ValidationError as e:
                    vprint(f"Failed to parse examples response for '{word}': {e}")
                    return Examples()

            return Examples()

        except Exception as e:
            vprint(f"Error generating examples for '{word}': {e}")
            return Examples()

    def _build_request_params(
        self,
        system_message: str,
        user_prompt: str,
        response_schema: type[DefinitionSynthesisResponse] | type[ExampleGenerationResponse],
    ) -> dict[str, Any]:
        """Build request parameters based on model capabilities.

        Args:
            system_message: System message
            user_prompt: User prompt
            response_schema: Pydantic model for structured response

        Returns:
            Dictionary of request parameters
        """
        params: dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
        }

        # Add structured output if supported
        if self.capabilities.supports_structured_outputs:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": response_schema.model_json_schema(),
                    "strict": True,
                },
            }
        else:
            # Fallback to JSON mode for older models
            params["response_format"] = {"type": "json_object"}

        # Add reasoning effort for reasoning models
        if self.capabilities.uses_reasoning_effort and self.capabilities.default_reasoning_effort:
            params["reasoning_effort"] = self.config.reasoning_effort

        # Add temperature for non-reasoning models
        if self.capabilities.supports_temperature:
            # Use different temperatures for different tasks
            if "definitions" in response_schema.__name__.lower():
                params["temperature"] = 0.3  # Lower for consistency
            else:
                params["temperature"] = 0.7  # Higher for creativity

        # Add max_tokens for standard models (reasoning models use max_completion_tokens)
        if self.capabilities.supports_max_tokens:
            params["max_tokens"] = 1000
        elif is_reasoning_model(self.config.model):
            params["max_completion_tokens"] = 1000

        return params

    def _convert_ai_definitions(self, ai_definitions: list[Any]) -> list[Definition]:
        """Convert AI response definitions to internal Definition objects.

        Args:
            ai_definitions: List of AI definition responses

        Returns:
            List of Definition objects
        """
        definitions = []

        for ai_def in ai_definitions:
            try:
                # Map AI WordTypeEnum to internal WordType
                word_type = self._map_word_type(ai_def.word_type)
                if word_type:
                    definitions.append(
                        Definition(
                            word_type=word_type,
                            definition=ai_def.definition,
                            examples=Examples(),  # Will be filled separately
                        )
                    )
            except Exception as e:
                vprint(f"Error converting AI definition: {e}")
                continue

        return definitions

    def _map_word_type(self, ai_word_type: WordTypeEnum) -> WordType | None:
        """Map AI WordTypeEnum to internal WordType.

        Args:
            ai_word_type: AI word type enum

        Returns:
            Mapped WordType or None
        """
        mapping = {
            WordTypeEnum.NOUN: WordType.NOUN,
            WordTypeEnum.VERB: WordType.VERB,
            WordTypeEnum.ADJECTIVE: WordType.ADJECTIVE,
            WordTypeEnum.ADVERB: WordType.ADVERB,
            WordTypeEnum.PREPOSITION: WordType.PREPOSITION,
            WordTypeEnum.CONJUNCTION: WordType.CONJUNCTION,
            WordTypeEnum.INTERJECTION: WordType.INTERJECTION,
            WordTypeEnum.PRONOUN: WordType.PRONOUN,
            WordTypeEnum.DETERMINER: WordType.DETERMINER,
            WordTypeEnum.PHRASE: WordType.PHRASE,
            WordTypeEnum.OTHER: WordType.OTHER,
        }
        return mapping.get(ai_word_type)

    async def close(self) -> None:
        """Clean up OpenAI connector resources."""
        # Close the AsyncOpenAI client if it has a close method
        if hasattr(self.client, "close"):
            await self.client.close()
        elif hasattr(self.client, "aclose"):
            await self.client.aclose()
