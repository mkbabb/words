"""State tracking for pipeline operations with async event streaming."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from ..api.models.pipeline import PipelineState
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StateTracker:
    """Tracks pipeline state and provides async event streaming."""
    
    def __init__(self):
        """Initialize the state tracker."""
        self._queue: asyncio.Queue[PipelineState] = asyncio.Queue()
        self._current_state: PipelineState | None = None
        self._subscribers: set[asyncio.Queue[PipelineState]] = set()
    
    async def update_state(
        self,
        stage: str,
        progress: float,
        message: str,
        details: dict[str, Any] | None = None,
        is_complete: bool = False,
        error: str | None = None,
    ) -> None:
        """Update the current pipeline state and notify all subscribers."""
        state = PipelineState(
            stage=stage,
            progress=progress,
            message=message,
            details=details or {},
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


# Global state tracker instances for different operations
lookup_state_tracker = StateTracker()
search_state_tracker = StateTracker()