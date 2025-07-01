"""OpenAI connector with modern async API and structured outputs."""

from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..storage.mongodb import get_cache_entry, save_cache_entry
from ..utils.logging import get_logger
from .models import (
    EmbeddingResponse,
    ExampleGenerationResponse,
    FallbackResponse,
    ModelCapabilities,
    PronunciationResponse,
    SynthesisResponse,
)
from .templates import PromptTemplateManager

T = TypeVar('T', bound=BaseModel)
logger = get_logger(__name__)


def detect_model_capabilities(model_name: str) -> ModelCapabilities:
    """Detect model capabilities based on model name."""
    reasoning_models = {"o1-preview", "o1-mini", "o3-mini", "o3"}
    return ModelCapabilities(
        supports_reasoning=model_name in reasoning_models,
        supports_temperature=model_name not in reasoning_models,
        supports_structured_output=True,
    )


class OpenAIConnector:
    """Modern OpenAI connector with structured outputs and caching."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4o",
        temperature: float | None = None,
        max_tokens: int = 1000,
    ) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        self.capabilities = detect_model_capabilities(model_name)
        self.temperature = temperature if self.capabilities.supports_temperature else None
        self.max_tokens = max_tokens
        self.template_manager = PromptTemplateManager()

    async def _make_structured_request(
        self,
        prompt: str,
        response_model: type[T],
        cache_key: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Make a structured request to OpenAI with caching."""
        # Check cache first
        if cache_key:
            cached = await get_cache_entry("openai", cache_key)
            if cached:
                try:
                    return response_model.model_validate(cached)
                except Exception as e:
                    logger.warning(f"Failed to deserialize cached response: {e}")

        # Prepare request parameters
        request_params: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            **kwargs,
        }

        # Add temperature if supported
        if self.temperature is not None and self.capabilities.supports_temperature:
            request_params["temperature"] = self.temperature

        # Use structured outputs if available
        if self.capabilities.supports_structured_output:
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

            # Cache the result
            if cache_key:
                await save_cache_entry("openai", cache_key, result.model_dump())

            return result

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def synthesize_definition(
        self, word: str, word_type: str, provider_definitions: list[tuple[str, str]]
    ) -> SynthesisResponse:
        """Synthesize definitions from multiple providers."""
        prompt = self.template_manager.get_synthesis_prompt(
            word, word_type, provider_definitions
        )
        cache_key = f"synthesis_{word}_{word_type}_{hash(str(provider_definitions))}"

        return await self._make_structured_request(
            prompt, SynthesisResponse, cache_key
        )

    async def generate_example(
        self, word: str, definition: str, word_type: str
    ) -> ExampleGenerationResponse:
        """Generate modern usage example."""
        prompt = self.template_manager.get_example_prompt(word, definition, word_type)
        cache_key = f"example_{word}_{word_type}_{hash(definition)}"

        return await self._make_structured_request(
            prompt, ExampleGenerationResponse, cache_key
        )

    async def generate_pronunciation(self, word: str) -> PronunciationResponse:
        """Generate pronunciation data."""
        prompt = self.template_manager.get_pronunciation_prompt(word)
        cache_key = f"pronunciation_{word}"

        return await self._make_structured_request(
            prompt, PronunciationResponse, cache_key
        )

    async def generate_fallback_entry(self, word: str) -> FallbackResponse:
        """Generate AI fallback provider data."""
        prompt = self.template_manager.get_fallback_prompt(word)
        cache_key = f"fallback_{word}"

        return await self._make_structured_request(
            prompt, FallbackResponse, cache_key
        )

    async def generate_embeddings(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        cache_key = f"embeddings_{hash(str(texts))}"
        
        # Check cache first
        cached = await get_cache_entry("openai", cache_key)
        if cached:
            try:
                return EmbeddingResponse.model_validate(cached)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached embeddings: {e}")

        try:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )

            result = EmbeddingResponse(
                embeddings=[data.embedding for data in response.data],
                usage=response.usage.model_dump() if response.usage else {},
            )

            # Cache the result
            await save_cache_entry("openai", cache_key, result.model_dump())
            return result

        except Exception as e:
            logger.error(f"OpenAI embeddings error: {e}")
            raise

    async def batch_process(
        self, requests: list[tuple[str, type[BaseModel], str]]
    ) -> list[Any]:
        """Process multiple requests in parallel for efficiency."""
        tasks = []
        for prompt, response_model, cache_key in requests:
            task = self._make_structured_request(prompt, response_model, cache_key)
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)