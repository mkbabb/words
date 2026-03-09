"""Tournament/ranker pattern: generate N candidates in parallel, rank, select best.

Ported from gaggle's BestOfNConnector. Generates diverse candidates using a cheaper
model tier, then ranks them with a dedicated ranker model to select the highest quality.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from ..utils.logging import get_logger
from .model_selection import ModelTier
from .models import RankingResponse

T = TypeVar("T", bound=BaseModel)

logger = get_logger(__name__)


class TournamentConfig(BaseModel):
    """Configuration for tournament-style generation."""

    n: int = Field(default=3, ge=2, le=8, description="Number of candidates to generate")
    generator_tier: ModelTier = ModelTier.MEDIUM
    ranker_tier: ModelTier = ModelTier.LOW
    temperature_boost: float = Field(default=0.15, ge=0.0, le=0.5)


class TournamentResult[T](BaseModel):
    """Result from tournament selection."""

    model_config = {"arbitrary_types_allowed": True}

    response: T
    candidates: list[T]
    scores: list[float]
    selected_index: int
    total_tokens: int


async def run_tournament(
    ai: Any,  # AIConnector — forward reference to avoid circular import
    prompt: str,
    response_model: type[T],
    task_name: str,
    config: TournamentConfig,
    rank_prompt_builder: Callable[[list[T]], str],
    system_prompt: str | None = None,
) -> TournamentResult[T]:
    """Generate N candidates in parallel (uncached) then rank and select best.

    Args:
        ai: AIConnector instance
        prompt: The generation prompt
        response_model: Pydantic model for structured output
        task_name: Task name for model selection
        config: Tournament configuration
        rank_prompt_builder: Function that takes list of candidates and returns ranking prompt
        system_prompt: Optional system prompt for generation
    """
    logger.info(
        f"Tournament: generating {config.n} candidates for '{task_name}' "
        f"(generator={config.generator_tier.value}, ranker={config.ranker_tier.value})"
    )

    # Phase 1: Generate N candidates in parallel using cheaper model
    generation_tasks = [
        ai._make_structured_request_impl(
            prompt,
            response_model,
            task_name=task_name,
            system_prompt=system_prompt,
            tier=config.generator_tier,
            temperature_boost=config.temperature_boost,
        )
        for _ in range(config.n)
    ]

    candidates: list[T] = await asyncio.gather(*generation_tasks, return_exceptions=True)  # type: ignore[assignment]

    # Filter out failures
    valid_candidates: list[T] = [c for c in candidates if not isinstance(c, BaseException)]

    if not valid_candidates:
        raise RuntimeError(f"Tournament: all {config.n} candidates failed for '{task_name}'")

    if len(valid_candidates) == 1:
        logger.warning("Tournament: only 1 valid candidate, skipping ranking")
        return TournamentResult(
            response=valid_candidates[0],
            candidates=valid_candidates,
            scores=[10.0],
            selected_index=0,
            total_tokens=0,
        )

    failed_count = len(candidates) - len(valid_candidates)
    if failed_count > 0:
        logger.warning(f"Tournament: {failed_count}/{config.n} candidates failed")

    # Phase 2: Rank candidates
    rank_prompt = rank_prompt_builder(valid_candidates)

    try:
        ranking_result: RankingResponse = await ai._make_structured_request_impl(
            rank_prompt,
            RankingResponse,
            task_name="rank_candidates",
            tier=config.ranker_tier,
        )

        # Extract scores, find best
        scores = [0.0] * len(valid_candidates)
        for ranking in ranking_result.rankings:
            if 0 <= ranking.index < len(valid_candidates):
                scores[ranking.index] = ranking.score

        selected_index = scores.index(max(scores))

    except Exception as e:
        logger.warning(f"Tournament: ranking failed ({e}), selecting first candidate")
        scores = [10.0] + [0.0] * (len(valid_candidates) - 1)
        selected_index = 0

    selected = valid_candidates[selected_index]

    logger.info(
        f"Tournament: selected candidate {selected_index} "
        f"(score={scores[selected_index]:.1f}) from {len(valid_candidates)} candidates"
    )

    return TournamentResult(
        response=selected,
        candidates=valid_candidates,
        scores=scores,
        selected_index=selected_index,
        total_tokens=0,  # Tracked by individual calls
    )
