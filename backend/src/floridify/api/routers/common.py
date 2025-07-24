"""Common models and utilities for API routers."""

from pydantic import BaseModel, Field


class PipelineMetrics(BaseModel):
    """Metrics for pipeline execution."""
    
    start_time: float = Field(..., description="Pipeline start timestamp")
    end_time: float = Field(..., description="Pipeline end timestamp")
    duration_ms: float = Field(..., description="Total duration in milliseconds")
    provider_count: int = Field(..., description="Number of providers queried")
    definition_count: int = Field(..., description="Total definitions found")
    ai_synthesis: bool = Field(..., description="Whether AI synthesis was used")
    from_cache: bool = Field(..., description="Whether result was from cache")