"""Pipeline state tracking infrastructure for progress reporting."""

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Standard pipeline stage identifiers."""

    # Common stages
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"

    # Lookup pipeline stages
    LOOKUP_DICTIONARY = "lookup_dictionary"
    LOOKUP_AI_SYNTHESIS = "lookup_ai_synthesis"
    LOOKUP_MEANING_EXTRACTION = "lookup_meaning_extraction"
    LOOKUP_CLUSTERING = "lookup_clustering"
    LOOKUP_SAVING = "lookup_saving"


class PipelineState(BaseModel):
    """Represents the current state of a pipeline operation."""

    stage: str = Field(..., description="Current stage identifier")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress from 0.0 to 1.0")
    message: str = Field("", description="Human-readable status message")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional stage-specific details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this state was recorded"
    )
    is_complete: bool = Field(default=False, description="Whether the pipeline has completed")
    error: str | None = Field(default=None, description="Error message if pipeline failed")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class StateTracker:
    """Manages pipeline state updates with thread-safe operations."""

    def __init__(self, loop: asyncio.AbstractEventLoop | None = None):
        """Initialize the state tracker.

        Args:
            loop: Event loop to use. If None, will get current loop when needed.
        """
        self._loop = loop
        self._queue: asyncio.Queue[PipelineState] = asyncio.Queue()
        self._current_state: PipelineState | None = None
        self._start_time: float = time.time()

    @property
    def start_time(self) -> float:
        """Get the pipeline start time."""
        return self._start_time

    def reset(self) -> None:
        """Reset the tracker to initial state."""
        self._current_state = None
        self._start_time = time.time()
        # Create new queue to clear any pending items
        self._queue = asyncio.Queue()

    def _get_timestamp(self) -> float:
        """Calculate seconds elapsed since start."""
        return time.time() - self._start_time

    async def update_state(
        self,
        stage: str,
        progress: float = 0.0,
        message: str = "",
        details: dict[str, Any] | None = None,
        is_complete: bool = False,
        error: str | None = None,
    ) -> PipelineState:
        """Update the pipeline state asynchronously.

        Args:
            stage: Stage identifier (can be PipelineStage enum or custom string)
            progress: Progress value from 0.0 to 1.0
            message: Human-readable status message
            details: Optional additional stage-specific details
            is_complete: Whether the pipeline has completed
            error: Optional error message

        Returns:
            The updated pipeline state
        """
        state = PipelineState(
            stage=stage.value if isinstance(stage, PipelineStage) else stage,
            progress=progress,
            message=message,
            details=details or {},
            timestamp=datetime.now(),
            is_complete=is_complete,
            error=error,
        )

        self._current_state = state
        await self._queue.put(state)
        return state

    def update_state_sync(
        self,
        stage: str,
        progress: float = 0.0,
        message: str = "",
        details: dict[str, Any] | None = None,
        is_complete: bool = False,
        error: str | None = None,
    ) -> PipelineState:
        """Update the pipeline state synchronously.

        This method creates a task in the event loop to handle the async update.

        Args:
            stage: Stage identifier (can be PipelineStage enum or custom string)
            progress: Progress value from 0.0 to 1.0
            message: Human-readable status message
            details: Optional additional stage-specific details
            is_complete: Whether the pipeline has completed
            error: Optional error message

        Returns:
            The updated pipeline state
        """
        state = PipelineState(
            stage=stage.value if isinstance(stage, PipelineStage) else stage,
            progress=progress,
            message=message,
            details=details or {},
            timestamp=datetime.now(),
            is_complete=is_complete,
            error=error,
        )

        self._current_state = state

        # Schedule async queue update
        loop = self._loop or asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self._queue.put(state), loop)

        return state

    def get_current_state(self) -> PipelineState | None:
        """Get the current pipeline state.

        Returns:
            Current state or None if no updates yet
        """
        return self._current_state

    def get_progress(self) -> float:
        """Get the current progress value.

        Returns:
            Progress from 0.0 to 1.0, or 0.0 if no state
        """
        return self._current_state.progress if self._current_state else 0.0

    async def get_state_updates(self) -> AsyncIterator[PipelineState]:
        """Async iterator for consuming state updates.

        Yields:
            Pipeline states as they are added to the queue
        """
        while True:
            state = await self._queue.get()
            yield state

            # Exit if completed or error
            if state.stage in (PipelineStage.COMPLETED, PipelineStage.ERROR):
                break

    def has_updates(self) -> bool:
        """Check if there are pending state updates.

        Returns:
            True if updates are queued
        """
        return not self._queue.empty()
