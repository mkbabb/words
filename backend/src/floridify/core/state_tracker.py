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


class ProcessStage(BaseModel):
    """Dynamic stage definition with flexible progress mapping."""

    name: str = Field(..., description="Stage identifier")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    label: str = Field(..., description="Human-readable stage name")
    description: str = Field("", description="Stage description for UI")
    category: str = Field("general", description="Stage category (lookup, upload, etc.)")


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

    # Upload stages
    UPLOAD_START = "UPLOAD_START"
    UPLOAD_READING = "UPLOAD_READING"
    UPLOAD_PARSING = "UPLOAD_PARSING"
    UPLOAD_PROCESSING = "UPLOAD_PROCESSING"
    UPLOAD_CREATING = "UPLOAD_CREATING"
    UPLOAD_FINALIZING = "UPLOAD_FINALIZING"

    # Image upload stages
    IMAGE_UPLOAD_START = "IMAGE_UPLOAD_START"
    IMAGE_UPLOAD_VALIDATING = "IMAGE_UPLOAD_VALIDATING"
    IMAGE_UPLOAD_PROCESSING = "IMAGE_UPLOAD_PROCESSING"
    IMAGE_UPLOAD_STORING = "IMAGE_UPLOAD_STORING"

    # Provider sub-stages (rarely used by frontend)
    PROVIDER_FETCH_HTTP_CONNECTING = "PROVIDER_FETCH_HTTP_CONNECTING"
    PROVIDER_FETCH_HTTP_DOWNLOADING = "PROVIDER_FETCH_HTTP_DOWNLOADING"
    PROVIDER_FETCH_HTTP_RATE_LIMITED = "PROVIDER_FETCH_HTTP_RATE_LIMITED"
    PROVIDER_FETCH_HTTP_PARSING = "PROVIDER_FETCH_HTTP_PARSING"
    PROVIDER_FETCH_HTTP_COMPLETE = "PROVIDER_FETCH_HTTP_COMPLETE"
    PROVIDER_FETCH_ERROR = "PROVIDER_FETCH_ERROR"

    # Progress mapping for automatic progress calculation
    PROGRESS_MAP = {
        # Lookup pipeline stages
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
        # Upload pipeline stages
        UPLOAD_START: 5,
        UPLOAD_READING: 15,
        UPLOAD_PARSING: 30,
        UPLOAD_PROCESSING: 60,
        UPLOAD_CREATING: 80,
        UPLOAD_FINALIZING: 95,
        # Image upload stages
        IMAGE_UPLOAD_START: 10,
        IMAGE_UPLOAD_VALIDATING: 30,
        IMAGE_UPLOAD_PROCESSING: 60,
        IMAGE_UPLOAD_STORING: 90,
    }

    @classmethod
    def get_stage_definitions(cls, category: str = "lookup") -> list[ProcessStage]:
        """Get predefined stage definitions for a process category."""
        if category == "lookup":
            return [
                ProcessStage(
                    name=cls.START,
                    progress=5,
                    label="Start",
                    description="Pipeline initialization and setup",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.SEARCH_START,
                    progress=10,
                    label="Search Start",
                    description="Beginning multi-method word search",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.SEARCH_COMPLETE,
                    progress=20,
                    label="Search Complete",
                    description="Found best matching word",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.PROVIDER_FETCH_START,
                    progress=25,
                    label="Provider Fetch",
                    description="Fetching from dictionary providers",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.PROVIDER_FETCH_COMPLETE,
                    progress=60,
                    label="Providers Complete",
                    description="All provider data collected",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.AI_CLUSTERING,
                    progress=70,
                    label="AI Clustering",
                    description="AI analyzing and clustering definitions",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.AI_SYNTHESIS,
                    progress=85,
                    label="AI Synthesis",
                    description="AI synthesizing comprehensive definitions",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.STORAGE_SAVE,
                    progress=95,
                    label="Storage",
                    description="Saving to knowledge base",
                    category="lookup",
                ),
                ProcessStage(
                    name=cls.COMPLETE,
                    progress=100,
                    label="Complete",
                    description="Pipeline complete!",
                    category="lookup",
                ),
            ]

        if category == "upload":
            return [
                ProcessStage(
                    name=cls.UPLOAD_START,
                    progress=5,
                    label="Start",
                    description="Initializing upload process",
                    category="upload",
                ),
                ProcessStage(
                    name=cls.UPLOAD_READING,
                    progress=15,
                    label="Reading File",
                    description="Reading uploaded file content",
                    category="upload",
                ),
                ProcessStage(
                    name=cls.UPLOAD_PARSING,
                    progress=30,
                    label="Parsing",
                    description="Parsing words from file",
                    category="upload",
                ),
                ProcessStage(
                    name=cls.UPLOAD_PROCESSING,
                    progress=60,
                    label="Processing",
                    description="Creating word entries",
                    category="upload",
                ),
                ProcessStage(
                    name=cls.UPLOAD_CREATING,
                    progress=80,
                    label="Creating List",
                    description="Finalizing wordlist creation",
                    category="upload",
                ),
                ProcessStage(
                    name=cls.UPLOAD_FINALIZING,
                    progress=95,
                    label="Finalizing",
                    description="Completing upload process",
                    category="upload",
                ),
                ProcessStage(
                    name=cls.COMPLETE,
                    progress=100,
                    label="Complete",
                    description="Upload complete!",
                    category="upload",
                ),
            ]

        if category == "image":
            return [
                ProcessStage(
                    name=cls.IMAGE_UPLOAD_START,
                    progress=10,
                    label="Start",
                    description="Starting image upload",
                    category="image",
                ),
                ProcessStage(
                    name=cls.IMAGE_UPLOAD_VALIDATING,
                    progress=30,
                    label="Validation",
                    description="Validating image format and size",
                    category="image",
                ),
                ProcessStage(
                    name=cls.IMAGE_UPLOAD_PROCESSING,
                    progress=60,
                    label="Processing",
                    description="Processing image metadata",
                    category="image",
                ),
                ProcessStage(
                    name=cls.IMAGE_UPLOAD_STORING,
                    progress=90,
                    label="Storing",
                    description="Storing image data",
                    category="image",
                ),
                ProcessStage(
                    name=cls.COMPLETE,
                    progress=100,
                    label="Complete",
                    description="Image uploaded!",
                    category="image",
                ),
            ]

        # Generic stages for unknown categories
        return [
            ProcessStage(
                name=cls.START,
                progress=10,
                label="Start",
                description="Starting process",
                category=category,
            ),
            ProcessStage(
                name="PROCESSING",
                progress=50,
                label="Processing",
                description="Processing data",
                category=category,
            ),
            ProcessStage(
                name=cls.COMPLETE,
                progress=100,
                label="Complete",
                description="Process complete!",
                category=category,
            ),
        ]


class PipelineState(BaseModel):
    """Optimized pipeline state with minimal payload size."""

    stage: str = Field(..., description="Current stage identifier")
    progress: int = Field(0, ge=0, le=100, description="Progress from 0 to 100")
    message: str = Field("", description="Human-readable status message")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional stage-specific details (for debugging)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this state was recorded",
    )
    is_complete: bool = Field(default=False, description="Whether the pipeline has completed")
    error: str | None = Field(default=None, description="Error message if pipeline failed")

    def model_dump_optimized(self) -> dict[str, Any]:
        """Return optimized dict with only essential fields for frontend."""
        result = {
            "stage": self.stage,
            "progress": self.progress,
        }

        # Only include message if it differs from stage (avoid redundancy)
        if self.message and self.message.lower() != self.stage.lower().replace("_", " "):
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

    def __init__(
        self,
        category: str = "general",
        custom_stages: list[ProcessStage] | None = None,
    ) -> None:
        """Initialize the state tracker.

        Args:
            category: Process category (lookup, upload, image, etc.)
            custom_stages: Optional custom stage definitions

        """
        self._queue: asyncio.Queue[PipelineState] = asyncio.Queue()
        self._current_state: PipelineState | None = None
        self._subscribers: set[asyncio.Queue[PipelineState]] = set()
        self._category = category
        self._stages = custom_stages or Stages.get_stage_definitions(category)

        # Build progress map from stages
        self._progress_map = {stage.name: stage.progress for stage in self._stages}
        # Include default progress map as fallback
        self._progress_map.update(Stages.PROGRESS_MAP)

    async def update(
        self,
        stage: str,
        progress: int | None = None,
        message: str = "",
        details: dict[str, Any] | None = None,
        is_complete: bool = False,
        error: str | None = None,
    ) -> None:
        """Update the current pipeline state and notify all subscribers."""
        # Smart progress handling:
        # 1. If progress is explicitly provided, use it
        # 2. If stage has a mapped progress, use that
        # 3. Otherwise maintain current progress
        if progress is None:
            if stage in self._progress_map:
                progress = self._progress_map[stage]
            elif self._current_state:
                progress = self._current_state.progress
            else:
                progress = 0

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
                # Drop oldest event and enqueue the new one to prevent data loss
                try:
                    subscriber.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    subscriber.put_nowait(state)
                except asyncio.QueueFull:
                    logger.warning(
                        "Subscriber queue persistently full, dropping state update",
                        extra={"stage": state.stage, "progress": state.progress},
                    )

    async def update_stage(self, stage: str, progress: int | None = None) -> None:
        """Optimized update for stage-only changes (most common case)."""
        # Auto-calculate progress from stage if not provided
        if progress is None:
            progress = self._progress_map.get(stage, 0)
        await self.update(stage=stage, progress=progress)

    async def update_progress(self, progress: int) -> None:
        """Optimized update for progress-only changes."""
        if self._current_state:
            await self.update(
                stage=self._current_state.stage,
                progress=progress,
                message=self._current_state.message,
            )

    async def update_complete(
        self,
        stage: str = "COMPLETE",
        message: str = "Pipeline completed",
    ) -> None:
        """Optimized update for completion."""
        await self.update(stage=stage, progress=100, message=message, is_complete=True)

    async def update_error(self, error: str, stage: str = "ERROR") -> None:
        """Optimized update for errors."""
        # Maintain current progress or use stage progress if available
        progress = self._current_state.progress if self._current_state else 0
        if stage != "ERROR" and stage in self._progress_map:
            progress = self._progress_map[stage]
        await self.update(stage=stage, progress=progress, error=error, is_complete=True)

    async def get_states(self) -> AsyncGenerator[PipelineState]:
        """Get state updates as they occur."""
        while True:
            state = await self._queue.get()
            yield state
            if state.is_complete or state.error:
                break

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue[PipelineState]]:
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

    def get_stage_definitions(self) -> list[ProcessStage]:
        """Get the stage definitions for this tracker."""
        return self._stages.copy()

    def get_current_state(self) -> PipelineState | None:
        """Get the current state."""
        return self._current_state

    @property
    def category(self) -> str:
        """Get the process category."""
        return self._category


# Global state tracker instance for lookup operations
lookup_state_tracker = StateTracker()
