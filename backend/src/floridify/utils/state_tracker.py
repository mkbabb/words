"""State tracking utilities for monitoring pipeline progress."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


class PipelineStage(Enum):
    """Pipeline stages for progress tracking."""

    SEARCH = "search"
    PROVIDER_FETCH = "provider_fetch"
    PROVIDER_START = "provider_start"
    PROVIDER_CONNECTED = "provider_connected"
    PROVIDER_DOWNLOADING = "provider_downloading"
    PROVIDER_PARSING = "provider_parsing"
    PROVIDER_COMPLETE = "provider_complete"
    AI_CLUSTERING = "ai_clustering"
    AI_SYNTHESIS = "ai_synthesis"
    AI_EXAMPLES = "ai_examples"
    AI_SYNONYMS = "ai_synonyms"
    STORAGE_SAVE = "storage_save"
    COMPLETE = "complete"


@dataclass
class ProviderMetrics:
    """Metrics for tracking provider performance and data quality."""

    provider_name: str
    response_time_ms: float
    response_size_bytes: int
    connection_time_ms: float | None = None
    download_time_ms: float | None = None
    parse_time_ms: float | None = None
    definitions_count: int = 0
    has_pronunciation: bool = False
    has_etymology: bool = False
    has_examples: bool = False
    completeness_score: float = 0.0  # 0-1 score based on data availability
    success: bool = True
    error_message: str | None = None

    def calculate_completeness_score(self) -> None:
        """Calculate data completeness score based on available fields."""
        score = 0.0
        if self.definitions_count > 0:
            score += 0.4
        if self.has_pronunciation:
            score += 0.2
        if self.has_etymology:
            score += 0.2
        if self.has_examples:
            score += 0.2
        self.completeness_score = min(1.0, score)


@dataclass
class StateUpdate:
    """Represents a single state update."""

    stage: PipelineStage
    progress: float  # 0-100
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float | None = None
    partial_data: Any | None = None
    provider_metrics: ProviderMetrics | None = None


class StateTracker:
    """Tracks state and progress through the lookup pipeline."""

    def __init__(self, callback: Callable[[StateUpdate], None] | None = None):
        """Initialize state tracker with optional callback.

        Args:
            callback: Optional async callback function to call on state updates
        """
        self.callback = callback
        self.updates: list[StateUpdate] = []
        self.start_time = time.time()
        self.stage_start_times: dict[PipelineStage, float] = {}

    async def update(
        self,
        stage: PipelineStage,
        progress: float,
        message: str,
        metadata: dict[str, Any] | None = None,
        partial_data: Any | None = None,
    ) -> None:
        """Update the current state and progress.

        Args:
            stage: Current pipeline stage
            progress: Progress percentage (0-100)
            message: Human-readable status message
            metadata: Additional metadata about the update
            partial_data: Partial results available at this stage
        """
        # Calculate duration if we have a previous stage time
        duration_ms = None
        if stage in self.stage_start_times:
            duration_ms = (time.time() - self.stage_start_times[stage]) * 1000
        else:
            self.stage_start_times[stage] = time.time()

        update = StateUpdate(
            stage=stage,
            progress=progress,
            message=message,
            metadata=metadata or {},
            duration_ms=duration_ms,
            partial_data=partial_data,
        )

        self.updates.append(update)

        # Call callback if provided
        if self.callback:
            try:
                await self.callback(update)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    async def start_stage(self, stage: PipelineStage) -> None:
        """Mark the start of a new stage for timing."""
        self.stage_start_times[stage] = time.time()

    def get_total_duration_ms(self) -> float:
        """Get total duration since tracking started."""
        return (time.time() - self.start_time) * 1000

    def get_stage_duration_ms(self, stage: PipelineStage) -> float | None:
        """Get duration for a specific stage if completed."""
        for update in reversed(self.updates):
            if update.stage == stage and update.duration_ms is not None:
                return update.duration_ms
        return None

    def get_latest_update(self) -> StateUpdate | None:
        """Get the most recent state update."""
        return self.updates[-1] if self.updates else None

    def get_updates_by_stage(self, stage: PipelineStage) -> list[StateUpdate]:
        """Get all updates for a specific stage."""
        return [u for u in self.updates if u.stage == stage]
