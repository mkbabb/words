"""Common utilities for API routers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PipelineMetrics(BaseModel):
    """Metrics for pipeline operations."""
    
    total_time_ms: int = 0
    steps_completed: int = 0
    errors_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return self.model_dump()