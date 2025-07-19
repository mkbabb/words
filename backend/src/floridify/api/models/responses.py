"""Response models for API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ...models.models import Definition, Pronunciation
from ...search.constants import SearchMethod


class StageMetrics(BaseModel):
    """Performance metrics for a single pipeline stage."""
    
    name: str = Field(..., description="Stage name", example="lookup_dictionary")
    duration_ms: int = Field(..., ge=0, description="Time spent in this stage (milliseconds)", example=125)
    success: bool = Field(..., description="Whether the stage completed successfully", example=True)
    items_processed: int | None = Field(None, ge=0, description="Number of items processed", example=10)
    metadata: dict[str, Any] | None = Field(None, description="Additional stage-specific metrics")


class ProviderMetrics(BaseModel):
    """Metrics for an external provider (dictionary API, AI service, etc.)."""
    
    name: str = Field(..., description="Provider name", example="Webster API")
    response_time_ms: int = Field(..., ge=0, description="API response time (milliseconds)", example=250)
    success: bool = Field(..., description="Whether the request succeeded", example=True)
    rate_limited: bool = Field(default=False, description="Whether rate limiting was encountered")
    cached: bool = Field(default=False, description="Whether the response was served from cache")


class AIMetrics(BaseModel):
    """Metrics specific to AI operations."""
    
    model: str = Field(..., description="AI model used", example="gpt-4")
    prompt_tokens: int = Field(..., ge=0, description="Number of tokens in the prompt", example=150)
    completion_tokens: int = Field(..., ge=0, description="Number of tokens in the completion", example=350)
    total_tokens: int = Field(..., ge=0, description="Total tokens used", example=500)
    temperature: float = Field(..., ge=0.0, le=2.0, description="Temperature setting used", example=0.7)
    duration_ms: int = Field(..., ge=0, description="Total AI processing time (milliseconds)", example=1200)


class SearchMethodMetrics(BaseModel):
    """Metrics for a specific search method."""
    
    method: SearchMethod = Field(..., description="Search method used")
    candidates_found: int = Field(..., ge=0, description="Number of candidates found", example=25)
    candidates_returned: int = Field(..., ge=0, description="Number of candidates returned after filtering", example=10)
    duration_ms: int = Field(..., ge=0, description="Search method execution time (milliseconds)", example=50)
    index_size: int | None = Field(None, ge=0, description="Size of the search index used", example=50000)


class PipelineMetrics(BaseModel):
    """Comprehensive metrics for a complete pipeline execution."""
    
    total_duration_ms: int = Field(..., ge=0, description="Total pipeline execution time (milliseconds)", example=1500)
    stages: list[StageMetrics] = Field(default_factory=list, description="Metrics for each pipeline stage")
    providers: list[ProviderMetrics] = Field(default_factory=list, description="External provider performance metrics")
    ai_metrics: AIMetrics | None = Field(None, description="AI usage metrics (if AI was used)")
    search_methods: list[SearchMethodMetrics] | None = Field(None, description="Search method performance (for search operations)")
    cache_hits: int = Field(default=0, ge=0, description="Number of cache hits during execution")
    cache_misses: int = Field(default=0, ge=0, description="Number of cache misses during execution")
    
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
                        "items_processed": 5
                    },
                    {
                        "name": "lookup_ai_synthesis",
                        "duration_ms": 1200,
                        "success": True,
                        "items_processed": 1
                    }
                ],
                "providers": [
                    {
                        "name": "Webster API",
                        "response_time_ms": 200,
                        "success": True,
                        "rate_limited": False,
                        "cached": False
                    }
                ],
                "ai_metrics": {
                    "model": "gpt-4",
                    "prompt_tokens": 150,
                    "completion_tokens": 350,
                    "total_tokens": 500,
                    "temperature": 0.7,
                    "duration_ms": 1000
                },
                "cache_hits": 2,
                "cache_misses": 3
            }
        }


class SearchResultItem(BaseModel):
    """Single search result item."""
    
    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: SearchMethod = Field(..., description="Search method that found this result")
    is_phrase: bool = Field(default=False, description="Whether this is a phrase")


class LookupResponse(BaseModel):
    """Response for word lookup."""
    
    word: str = Field(..., description="The word that was looked up")
    pronunciation: Pronunciation = Field(..., description="Pronunciation information")
    definitions: list[Definition] = Field(default_factory=list, description="Word definitions")
    last_updated: datetime = Field(..., description="When this entry was last updated")
    pipeline_metrics: PipelineMetrics | None = Field(None, description="Pipeline execution metrics (optional)")


class SearchResponse(BaseModel):
    """Response for search query."""
    
    query: str = Field(..., description="Original search query")
    results: list[SearchResultItem] = Field(default_factory=list, description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results")
    search_time_ms: int = Field(..., ge=0, description="Search execution time")
    pipeline_metrics: PipelineMetrics | None = Field(None, description="Pipeline execution metrics (optional)")


class SynonymItem(BaseModel):
    """Single synonym item."""
    
    word: str = Field(..., description="Synonym word")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class SynonymResponse(BaseModel):
    """Response for synonym query."""
    
    word: str = Field(..., description="Original word")
    synonyms: list[SynonymItem] = Field(default_factory=list, description="List of synonyms")


class SuggestionsAPIResponse(BaseModel):
    """Response for suggestions query."""
    
    words: list[str] = Field(default_factory=list, description="Suggested words")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in suggestions")


class FactItem(BaseModel):
    """Single fact item."""
    
    content: str = Field(..., description="The fact content")
    category: str = Field(..., description="Category of fact (etymology, usage, cultural, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in fact accuracy")


class FactsAPIResponse(BaseModel):
    """Response for facts query."""
    
    word: str = Field(..., description="The word the facts are about")
    facts: list[FactItem] = Field(default_factory=list, description="List of interesting facts")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in facts")
    categories: list[str] = Field(default_factory=list, description="Categories of facts included")


class HealthResponse(BaseModel):
    """Response for health check."""
    
    status: str = Field(..., description="Overall service status")
    database: str = Field(..., description="Database connection status")
    search_engine: str = Field(..., description="Search engine status")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    uptime_seconds: int = Field(..., ge=0, description="Service uptime in seconds")


class RegenerateExamplesResponse(BaseModel):
    """Response for regenerating examples."""
    
    word: str = Field(..., description="The word examples were regenerated for")
    definition_index: int = Field(..., description="Index of the definition")
    examples: list[dict[str, Any]] = Field(..., description="New generated examples")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence in examples")