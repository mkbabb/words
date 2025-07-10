"""Response models for API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ...ai.models import Suggestion
from ...models.models import Definition, Pronunciation
from ...search.constants import SearchMethod


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


class SearchResponse(BaseModel):
    """Response for search query."""
    
    query: str = Field(..., description="Original search query")
    results: list[SearchResultItem] = Field(default_factory=list, description="Search results")
    total_results: int = Field(..., ge=0, description="Total number of results")
    search_time_ms: int = Field(..., ge=0, description="Search execution time")


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


class HealthResponse(BaseModel):
    """Response for health check."""
    
    status: str = Field(..., description="Overall service status")
    database: str = Field(..., description="Database connection status")
    search_engine: str = Field(..., description="Search engine status")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    uptime_seconds: int = Field(..., ge=0, description="Service uptime in seconds")