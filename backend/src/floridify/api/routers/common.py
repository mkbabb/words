"""Common models shared across multiple API routers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ...search.constants import SearchMethod


class StageMetrics(BaseModel):
    """Performance metrics for a single pipeline stage."""

    name: str = Field(..., description="Stage name")
    duration_ms: int = Field(..., ge=0, description="Time spent in this stage (milliseconds)")
    success: bool = Field(..., description="Whether the stage completed successfully")
    items_processed: int | None = Field(None, ge=0, description="Number of items processed")
    metadata: dict[str, Any] | None = Field(None, description="Additional stage-specific metrics")


class ProviderMetrics(BaseModel):
    """Metrics for an external provider (dictionary API, AI service, etc.)."""

    name: str = Field(..., description="Provider name")
    response_time_ms: int = Field(..., ge=0, description="API response time (milliseconds)")
    success: bool = Field(..., description="Whether the request succeeded")
    rate_limited: bool = Field(default=False, description="Whether rate limiting was encountered")
    cached: bool = Field(default=False, description="Whether the response was served from cache")


class AIMetrics(BaseModel):
    """Metrics specific to AI operations."""

    model: str = Field(..., description="AI model used")
    prompt_tokens: int = Field(..., ge=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(..., ge=0, description="Number of tokens in the completion")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Temperature setting used")
    duration_ms: int = Field(..., ge=0, description="Total AI processing time (milliseconds)")


class SearchMethodMetrics(BaseModel):
    """Metrics for a specific search method."""

    method: SearchMethod = Field(..., description="Search method used")
    candidates_found: int = Field(..., ge=0, description="Number of candidates found")
    candidates_returned: int = Field(
        ..., ge=0, description="Number of candidates returned after filtering"
    )
    duration_ms: int = Field(..., ge=0, description="Search method execution time (milliseconds)")
    index_size: int | None = Field(None, ge=0, description="Size of the search index used")


class PipelineMetrics(BaseModel):
    """Comprehensive metrics for a complete pipeline execution."""

    total_duration_ms: int = Field(
        ..., ge=0, description="Total pipeline execution time (milliseconds)"
    )
    stages: list[StageMetrics] = Field(
        default_factory=list, description="Metrics for each pipeline stage"
    )
    providers: list[ProviderMetrics] = Field(
        default_factory=list, description="External provider performance metrics"
    )
    ai_metrics: AIMetrics | None = Field(None, description="AI usage metrics (if AI was used)")
    search_methods: list[SearchMethodMetrics] | None = Field(
        None, description="Search method performance (for search operations)"
    )
    cache_hits: int = Field(default=0, ge=0, description="Number of cache hits during execution")
    cache_misses: int = Field(
        default=0, ge=0, description="Number of cache misses during execution"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "total_duration_ms": 1500,
                "stages": [
                    {
                        "name": "lookup_dictionary",
                        "duration_ms": 250,
                        "success": True,
                        "items_processed": 5,
                    },
                    {
                        "name": "lookup_ai_synthesis",
                        "duration_ms": 1200,
                        "success": True,
                        "items_processed": 1,
                    },
                ],
                "providers": [
                    {
                        "name": "Webster API",
                        "response_time_ms": 200,
                        "success": True,
                        "rate_limited": False,
                        "cached": False,
                    }
                ],
                "ai_metrics": {
                    "model": "gpt-4",
                    "prompt_tokens": 150,
                    "completion_tokens": 350,
                    "total_tokens": 500,
                    "temperature": 0.7,
                    "duration_ms": 1000,
                },
                "cache_hits": 2,
                "cache_misses": 3,
            }
        }


class PipelineState(BaseModel):
    """Real-time pipeline progress tracking."""

    id: str = Field(..., description="Unique pipeline execution ID")
    stage: str = Field(..., description="Current stage being executed")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0 to 1.0)")
    message: str = Field(default="", description="Human-readable status message")
    error: str | None = Field(None, description="Error message if pipeline failed")
    completed: bool = Field(default=False, description="Whether pipeline has completed")
    created_at: datetime = Field(default_factory=datetime.now, description="Pipeline start time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
