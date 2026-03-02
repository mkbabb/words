"""OpenAI connector base: class definition, structured request, singleton."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import BaseModel

from ...caching.decorators import cached_api_call
from ...models.base import ModelInfo
from ...utils.logging import get_logger, log_metrics
from ..model_selection import ModelTier, get_model_for_task, get_temperature_for_model
from ..prompt_manager import PromptManager
from .assessment import AssessmentMixin
from .generation import GenerationMixin
from .suggestions import SuggestionsMixin
from .synthesis import SynthesisMixin

T = TypeVar("T", bound=BaseModel)

logger = get_logger(__name__)


class OpenAIConnector(SynthesisMixin, GenerationMixin, AssessmentMixin, SuggestionsMixin):
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

        Raises:
            APIConnectionError: Network connection failed
            APITimeoutError: Request timed out
            RateLimitError: Rate limit exceeded
            APIStatusError: HTTP status error from API
            AuthenticationError: Authentication failed
            ValueError: No content in API response
            IndexError: Missing choices in response

        """
        start_time = time.perf_counter()

        # Determine which model to use based on task
        if task_name:
            model_tier = get_model_for_task(task_name)
            active_model = model_tier.value
        else:
            active_model = self.model_name
            model_tier = ModelTier(active_model)

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
        if model_tier.uses_completion_tokens:
            if model_tier.is_reasoning_model:
                # Reasoning models need token allocation for internal thinking
                # Cap multiplier to prevent runaway token usage
                reasoning_multiplier = 30 if max_tokens_value <= 50 else 15
                request_params["max_completion_tokens"] = min(
                    16000,
                    max(4000, max_tokens_value * reasoning_multiplier),
                )
            else:
                # Non-reasoning models with completion tokens use standard allocation
                request_params["max_completion_tokens"] = max_tokens_value
        else:
            # Legacy models use max_tokens
            request_params["max_tokens"] = max_tokens_value

        # Add temperature if model supports it (reasoning/thinking models don't)
        if temperature is not None and not model_tier.is_reasoning_model:
            request_params["temperature"] = temperature

        # Log API call details
        logger.debug(
            f"🤖 OpenAI API call: model={active_model}, "
            f"task={task_name or 'default'}, "
            f"response_type={response_model.__name__}, "
            f"prompt_length={len(prompt)}",
        )

        # Check AI spending budget before making API call
        from ...api.middleware.rate_limiting import spending_tracker

        budget_ok, budget_reason = await spending_tracker.check_budget()
        if not budget_ok:
            raise RateLimitError(
                message=f"AI budget exceeded: {budget_reason}",
                response=None,
                body=None,
            )

        # Make the API call with structured output (retry on transient errors)
        max_retries = 3
        api_start = time.perf_counter()

        for attempt in range(max_retries):
            try:
                response = await self.client.beta.chat.completions.parse(
                    response_format=response_model,
                    **request_params,
                )
                break
            except RateLimitError:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2**attempt
                    logger.warning(
                        f"Rate limited (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (APITimeoutError, APIConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Transient API error (attempt {attempt + 1}/{max_retries}): {e}, "
                        f"retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

        api_duration = time.perf_counter() - api_start

        # Extract token usage from response
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

        # Record actual AI spending
        await spending_tracker.record_spend(active_model, total_tokens)

        # Log successful API call
        log_metrics(
            api_call="openai",
            model=active_model,
            task=task_name or "default",
            response_type=response_model.__name__,
            duration=api_duration,
            retry_count=0,
            **token_usage,
        )

        # Parse JSON response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("No content in response")

        result = response_model.model_validate_json(content)

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
            f"in {total_duration:.2f}s (tokens: {total_tokens})",
        )

        return result


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
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
        from ...utils.config import Config

        logger.info("Initializing OpenAI connector singleton")
        config = Config.from_file(config_path)

        api_key = config.openai.api_key
        model_name = config.openai.model

        # Log configuration status (without exposing the key)
        logger.info(f"OpenAI model: {model_name}")
        logger.info(f"API key configured: {'Yes' if api_key and len(api_key) > 20 else 'No'}")

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
