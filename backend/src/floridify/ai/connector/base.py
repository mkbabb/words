"""Multi-provider AI connector with structured outputs, validation retry, and caching.

Supports OpenAI (GPT-5 series) and Anthropic (Claude 4.5/4.6) with task-based
model selection, semaphore rate limiting, and budget tracking.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, TypeVar

import anthropic
import openai
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from ...caching.decorators import cached_api_call
from ...models.base import ModelInfo
from ...utils.logging import get_logger, log_metrics
from ..model_selection import ModelTier, get_model_for_task, get_temperature_for_model
from ..prompt_manager import PromptManager
from .assessment import AssessmentMixin
from .config import Effort, OpenAIEffort, Provider
from .generation import GenerationMixin
from .suggestions import SuggestionsMixin
from .synthesis import SynthesisMixin

T = TypeVar("T", bound=BaseModel)

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 600.0
MAX_VALIDATION_RETRIES = 2


class AIConnector(SynthesisMixin, GenerationMixin, AssessmentMixin, SuggestionsMixin):
    """Multi-provider AI connector with structured outputs and validation retry.

    Supports OpenAI and Anthropic via a unified interface. Uses task-based model
    selection, semaphore rate limiting, validation retry on parse failures,
    and L1/L2 caching via @cached_api_call.
    """

    def __init__(
        self,
        provider: Provider,
        client: AsyncOpenAI | anthropic.AsyncAnthropic,
        model: str,
        semaphore: asyncio.Semaphore,
        prompt_manager: PromptManager | None = None,
        effort: Effort = OpenAIEffort.MEDIUM,
        **kwargs: Any,
    ) -> None:
        self.provider = provider
        self.client = client
        self.model = model
        self.semaphore = semaphore
        self.effort = effort
        self.kwargs = kwargs
        self.prompt_manager = prompt_manager or PromptManager()
        self._last_model_info: ModelInfo | None = None

    @property
    def last_model_info(self) -> ModelInfo | None:
        return self._last_model_info

    @cached_api_call(
        ttl_hours=24.0,
        key_prefix="ai_structured",
        ignore_params=["system_prompt"],
    )
    async def _make_structured_request(
        self,
        prompt: str,
        response_model: type[T],
        task_name: str | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Make a structured AI request with model selection and validation retry.

        Args:
            prompt: User prompt text
            response_model: Pydantic model for structured output
            task_name: Task name for model selection routing
            system_prompt: Optional system/developer prompt
            **kwargs: Additional parameters (max_tokens, temperature, tier)
        """
        start_time = time.perf_counter()

        # Model selection based on task
        tier_override = kwargs.pop("tier", None)
        if task_name:
            model_tier = get_model_for_task(task_name, override=tier_override)
            active_model = model_tier.value
        else:
            active_model = self.model
            model_tier = ModelTier(active_model)

        # Temperature selection
        temperature = kwargs.pop("temperature", None)
        if temperature is None:
            temperature = get_temperature_for_model(model_tier, task_name) if model_tier else None

        # Token parameters
        max_tokens_value = kwargs.pop("max_tokens", None) or 1000

        # Budget check
        from ...api.middleware.rate_limiting import spending_tracker

        budget_ok, budget_reason = await spending_tracker.check_budget()
        if not budget_ok:
            raise RateLimitError(
                message=f"AI budget exceeded: {budget_reason}",
                response=None,
                body=None,
            )

        logger.debug(
            f"AI request: provider={self.provider}, model={active_model}, "
            f"task={task_name or 'default'}, response={response_model.__name__}",
        )

        # Validation retry loop (retries on ValidationError, not on API errors)
        last_error: Exception | None = None
        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            try:
                async with self.semaphore:
                    if self.provider == Provider.OPENAI:
                        result, usage = await self._openai_call(
                            prompt=prompt,
                            response_model=response_model,
                            system_prompt=system_prompt,
                            temperature=temperature,
                            model=active_model,
                            model_tier=model_tier,
                            max_tokens=max_tokens_value,
                        )
                    else:
                        result, usage = await self._anthropic_call(
                            prompt=prompt,
                            response_model=response_model,
                            system_prompt=system_prompt,
                            temperature=temperature,
                        )

                # Record spending
                total_tokens = usage.get("total_tokens", 0)
                await spending_tracker.record_spend(active_model, total_tokens)

                # Track model info
                api_duration = time.perf_counter() - start_time
                self._last_model_info = ModelInfo(
                    name=active_model,
                    confidence=0.9,
                    temperature=temperature or 0.7,
                    max_tokens=max_tokens_value,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=total_tokens,
                    response_time_ms=int(api_duration * 1000),
                )

                log_metrics(
                    api_call=str(self.provider),
                    model=active_model,
                    task=task_name or "default",
                    response_type=response_model.__name__,
                    duration=api_duration,
                    retry_count=attempt,
                    **usage,
                )

                logger.info(
                    f"AI success: {response_model.__name__} in {api_duration:.2f}s "
                    f"(tokens: {total_tokens})",
                )
                return result

            except ValidationError as e:
                last_error = e
                if attempt < MAX_VALIDATION_RETRIES:
                    logger.warning(
                        f"Validation failed (attempt {attempt + 1}/{MAX_VALIDATION_RETRIES + 1}), retrying..."
                    )
                    for error in e.errors():
                        field_path = ".".join(str(loc) for loc in error["loc"])
                        logger.warning(f"  Field '{field_path}': {error['type']}")
                    continue

                logger.error(
                    f"Validation error for {response_model.__name__} after "
                    f"{MAX_VALIDATION_RETRIES + 1} attempts"
                )
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    logger.error(f"  Field '{field_path}': {error['type']} - {error['msg']}")
                raise

        # Should not reach here, but satisfy type checker
        raise last_error or RuntimeError("Unexpected end of retry loop")

    async def _openai_call(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None,
        temperature: float | None,
        model: str,
        model_tier: ModelTier,
        max_tokens: int,
    ) -> tuple[T, dict[str, int]]:
        """OpenAI structured outputs via beta.chat.completions.parse.

        GPT-5 series API (March 2026):
        - All GPT-5 models use "developer" role (not "system")
        - All GPT-5 models use max_completion_tokens (not max_tokens)
        - reasoning.effort defaults to "none" — no reasoning tokens, supports temperature
        - Temperature errors when reasoning.effort != "none"
        - We use effort=none for structured outputs (fast, cheap, temperature works)
        """
        if not isinstance(self.client, AsyncOpenAI):
            raise TypeError(f"OpenAI call requires AsyncOpenAI client, got {type(self.client).__name__}")

        messages: list[dict[str, str]] = []
        if system_prompt:
            # GPT-5 and o-series use "developer" role; GPT-4 uses "system"
            role = "developer" if model_tier.uses_developer_role else "system"
            messages.append({"role": role, "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_params: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_format": response_model,
        }

        # Token parameter: GPT-5 and o-series use max_completion_tokens
        if model_tier.uses_completion_tokens:
            request_params["max_completion_tokens"] = max_tokens
        else:
            request_params["max_tokens"] = max_tokens

        # Temperature: supported for GPT-5 when reasoning.effort=none (our default)
        # NOT supported for o-series models
        if temperature is not None and not model_tier.is_o_series:
            request_params["temperature"] = temperature

        # Retry on transient API errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.beta.chat.completions.parse(**request_params)
                break
            except RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except (APITimeoutError, APIConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Transient API error (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(wait_time)
                else:
                    raise

        # Check for refusal
        if response.choices[0].message.refusal:
            logger.error(f"OpenAI refusal: {response.choices[0].message.refusal}")
            raise ValueError(f"OpenAI refused: {response.choices[0].message.refusal}")

        # Parse response
        content = response.choices[0].message.content
        if not content:
            raise ValueError("No content in OpenAI response")

        result = response_model.model_validate_json(content)

        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        return result, usage

    async def _anthropic_call(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None,
        temperature: float | None,
    ) -> tuple[T, dict[str, int]]:
        """Anthropic structured outputs — GA as of Jan 2026.

        Claude API (March 2026):
        - Structured outputs: GA for Sonnet 4.5, Opus 4.5, Haiku 4.5 (no beta header)
        - output_format moved to output_config.format
        - Effort parameter: GA (no beta header)
        - Uses messages.create() with output_config, not beta.messages.parse()
        """
        if not isinstance(self.client, anthropic.AsyncAnthropic):
            raise TypeError(
                f"Anthropic call requires AsyncAnthropic client, got {type(self.client).__name__}"
            )

        effort = self.effort
        if effort == OpenAIEffort.MINIMAL:
            raise ValueError("Anthropic does not support 'minimal' effort level")

        # GA structured outputs: output_config.format replaces output_format
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.kwargs.get("max_tokens", 8192),
            "system": system_prompt or "",
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {
                "format": response_model,
                "effort": effort.value,
            },
        }
        if temperature is not None:
            params["temperature"] = temperature

        response = await self.client.messages.create(**params)  # type: ignore[arg-type]

        if response.stop_reason == "refusal":
            raise ValueError("Anthropic refusal: content may not comply with guidelines")

        if response.stop_reason == "max_tokens":
            logger.warning("Anthropic response truncated (max_tokens reached)")

        # Extract structured output from response content
        result = None
        for block in response.content:
            if hasattr(block, "parsed"):
                result = block.parsed
                break

        if result is None:
            # Fallback: try to parse from text content
            for block in response.content:
                if block.type == "text":
                    result = response_model.model_validate_json(block.text)
                    break

        if result is None:
            raise ValueError("Anthropic returned no parseable content")

        assert isinstance(result, response_model), "Response type mismatch"

        usage = {
            "prompt_tokens": response.usage.input_tokens if response.usage else 0,
            "completion_tokens": response.usage.output_tokens if response.usage else 0,
            "total_tokens": (
                (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
            ),
        }

        return result, usage

    async def close(self) -> None:
        """Close the underlying async client."""
        try:
            if isinstance(self.client, AsyncOpenAI):
                await self.client.close()
            elif isinstance(self.client, anthropic.AsyncAnthropic):
                await self.client.close()
        except Exception as e:
            logger.warning(f"Error closing AI client: {e}")


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_ai_connector: AIConnector | None = None


def get_ai_connector(
    config_path: str | Path | None = None,
    force_recreate: bool = False,
) -> AIConnector:
    """Get or create the global AI connector singleton.

    Reads provider config from auth/config.toml. Supports [openai] and [anthropic]
    sections. Provider selection via [ai].provider or defaults to OpenAI.
    """
    global _ai_connector

    if _ai_connector is None or force_recreate:
        from ...utils.config import Config

        logger.info("Initializing AI connector singleton")
        config = Config.from_file(config_path)

        # Determine provider and effort from config
        ai_section = getattr(config, "ai", None)
        provider_str = ai_section.provider if ai_section and hasattr(ai_section, "provider") else "openai"
        provider = Provider(provider_str) if isinstance(provider_str, str) else provider_str

        effort_str = ai_section.effort if ai_section and hasattr(ai_section, "effort") else "medium"
        effort = OpenAIEffort(effort_str) if isinstance(effort_str, str) else effort_str

        max_concurrent = (
            ai_section.max_concurrent_requests
            if ai_section and hasattr(ai_section, "max_concurrent_requests")
            else 10
        )
        semaphore = asyncio.Semaphore(max_concurrent)

        if provider == Provider.ANTHROPIC and hasattr(config, "anthropic") and config.anthropic:
            anthropic_config = config.anthropic
            logger.info(f"Anthropic model: {anthropic_config.model}")

            client = anthropic.AsyncAnthropic(
                api_key=anthropic_config.api_key,
                timeout=DEFAULT_TIMEOUT,
            )
            _ai_connector = AIConnector(
                provider=Provider.ANTHROPIC,
                client=client,
                model=anthropic_config.model,
                semaphore=semaphore,
                effort=effort,
                max_tokens=anthropic_config.max_tokens,
            )
        else:
            # Default to OpenAI
            api_key = config.openai.api_key
            model_name = config.openai.model
            logger.info(f"OpenAI model: {model_name}")

            client = AsyncOpenAI(
                api_key=api_key,
                timeout=DEFAULT_TIMEOUT,
            )
            _ai_connector = AIConnector(
                provider=Provider.OPENAI,
                client=client,
                model=model_name,
                semaphore=semaphore,
                effort=effort,
            )

        logger.success(f"AI connector initialized: {provider}")

    return _ai_connector
