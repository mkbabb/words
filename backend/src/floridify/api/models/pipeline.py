"""Pipeline state models for streaming progress."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineState(BaseModel):
    """Represents the current state of a pipeline operation."""
    
    stage: str = Field(..., description="Current stage of the pipeline")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress percentage (0-1)")
    message: str = Field(..., description="Human-readable status message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional stage-specific details")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this state was recorded")
    is_complete: bool = Field(default=False, description="Whether the pipeline has completed")
    error: str | None = Field(default=None, description="Error message if pipeline failed")