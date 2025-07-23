"""State tracking for pipeline operations with async event streaming."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logging import get_logger

logger = get_logger(__name__)


class Stages:
    """Optimized stage constants with progress mapping."""
    
    # Main pipeline stages with expected progress values
    START = "START"
    SEARCH_START = "SEARCH_START"
    SEARCH_COMPLETE = "SEARCH_COMPLETE" 
    PROVIDER_FETCH_START = "PROVIDER_FETCH_START"
    PROVIDER_FETCH_COMPLETE = "PROVIDER_FETCH_COMPLETE"
    AI_CLUSTERING = "AI_CLUSTERING"
    AI_SYNTHESIS = "AI_SYNTHESIS"
    AI_FALLBACK = "AI_FALLBACK"
    STORAGE_SAVE = "STORAGE_SAVE"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    
    # Provider sub-stages (rarely used by frontend)
    PROVIDER_FETCH_HTTP_CONNECTING = "PROVIDER_FETCH_HTTP_CONNECTING"
    PROVIDER_FETCH_HTTP_DOWNLOADING = "PROVIDER_FETCH_HTTP_DOWNLOADING"
    PROVIDER_FETCH_HTTP_RATE_LIMITED = "PROVIDER_FETCH_HTTP_RATE_LIMITED"
    PROVIDER_FETCH_HTTP_PARSING = "PROVIDER_FETCH_HTTP_PARSING"
    PROVIDER_FETCH_HTTP_COMPLETE = "PROVIDER_FETCH_HTTP_COMPLETE"
    PROVIDER_FETCH_ERROR = "PROVIDER_FETCH_ERROR"
    
    # Progress mapping for automatic progress calculation
    PROGRESS_MAP = {
        START: 5,
        SEARCH_START: 10,
        SEARCH_COMPLETE: 20,
        PROVIDER_FETCH_START: 25,
        PROVIDER_FETCH_COMPLETE: 60,
        AI_CLUSTERING: 70,
        AI_SYNTHESIS: 85,
        AI_FALLBACK: 90,
        STORAGE_SAVE: 95,
        COMPLETE: 100,
        ERROR: 0,
    }


class PipelineState(BaseModel):
    """Optimized pipeline state with minimal payload size."""

    stage: str = Field(..., description="Current stage identifier")
    progress: int = Field(0, ge=0, le=100, description="Progress from 0 to 100")
    message: str = Field("", description="Human-readable status message")
    details: dict[str, Any] | None = Field(
        default=None, description="Optional stage-specific details (for debugging)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When this state was recorded"
    )
    is_complete: bool = Field(
        default=False, description="Whether the pipeline has completed"
    )
    error: str | None = Field(
        default=None, description="Error message if pipeline failed"
    )

    def model_dump_optimized(self) -> dict[str, Any]:
        """Return optimized dict with only essential fields for frontend."""
        result = {
            "stage": self.stage,
            "progress": self.progress,
        }
        
        # Only include message if it differs from stage (avoid redundancy)
        if self.message and self.message.lower() != self.stage.lower().replace('_', ' '):
            result["message"] = self.message
            
        # Only include details for debugging or if explicitly needed
        if self.details:
            result["details"] = self.details
            
        # Include completion/error states
        if self.is_complete:
            result["is_complete"] = True
        if self.error:
            result["error"] = self.error
            
        return result


class StateTracker:
    """Tracks pipeline state and provides async event streaming."""

    def __init__(self) -> None:
        """Initialize the state tracker."""
        self._queue: asyncio.Queue[PipelineState] = asyncio.Queue()
        self._current_state: PipelineState | None = None
        self._subscribers: set[asyncio.Queue[PipelineState]] = set()

    async def update(
        self,
        stage: str,
        progress: int = 0,
        message: str = "",
        details: dict[str, Any] | None = None,
        is_complete: bool = False,
        error: str | None = None,
    ) -> None:
        """Update the current pipeline state and notify all subscribers."""
        state = PipelineState(
            stage=stage,
            progress=progress,
            message=message,
            details=details,
            timestamp=datetime.now(),
            is_complete=is_complete,
            error=error,
        )

        self._current_state = state

        # Put state in main queue
        await self._queue.put(state)

        # Notify all subscribers
        for subscriber in self._subscribers:
            try:
                # Non-blocking put to avoid deadlocks
                subscriber.put_nowait(state)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, skipping state update")

    async def update_stage(self, stage: str, progress: int | None = None) -> None:
        """Optimized update for stage-only changes (most common case)."""
        # Auto-calculate progress from stage if not provided
        if progress is None:
            progress = Stages.PROGRESS_MAP.get(stage, 0)
        await self.update(stage=stage, progress=progress)

    async def update_progress(self, progress: int) -> None:
        """Optimized update for progress-only changes."""
        if self._current_state:
            await self.update(
                stage=self._current_state.stage,
                progress=progress,
                message=self._current_state.message,
            )

    async def update_complete(self, stage: str = "COMPLETE", message: str = "Pipeline completed") -> None:
        """Optimized update for completion."""
        await self.update(stage=stage, progress=100, message=message, is_complete=True)

    async def update_error(self, error: str, stage: str = "ERROR") -> None:
        """Optimized update for errors."""
        await self.update(stage=stage, error=error, is_complete=True)

    async def get_states(self) -> AsyncGenerator[PipelineState, None]:
        """Get state updates as they occur."""
        while True:
            state = await self._queue.get()
            yield state
            if state.is_complete or state.error:
                break

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue[PipelineState], None]:
        """Subscribe to state updates with a dedicated queue."""
        subscriber_queue: asyncio.Queue[PipelineState] = asyncio.Queue(maxsize=100)
        self._subscribers.add(subscriber_queue)
        try:
            yield subscriber_queue
        finally:
            self._subscribers.discard(subscriber_queue)

    def reset(self) -> None:
        """Reset the state tracker."""
        self._current_state = None
        # Clear the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# Global state tracker instance for lookup operations
lookup_state_tracker = StateTracker()
