"""Request models for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...constants import DictionaryProvider


class LookupParams(BaseModel):
    """Parameters for word lookup endpoint."""
    
    force_refresh: bool = Field(default=False, description="Force refresh of cached data")
    providers: list[DictionaryProvider] = Field(
        default=[DictionaryProvider.WIKTIONARY], 
        description="Dictionary providers to use"
    )
    no_ai: bool = Field(default=False, description="Skip AI synthesis")


class SearchParams(BaseModel):
    """Parameters for search endpoint."""
    
    q: str = Field(..., min_length=1, max_length=100, description="Search query")
    method: str = Field(default="hybrid", pattern="^(exact|fuzzy|semantic|hybrid)$")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum relevance score")


class SuggestionParams(BaseModel):
    """Parameters for suggestion endpoint."""
    
    q: str = Field(..., min_length=2, max_length=50, description="Partial query")
    limit: int = Field(default=10, ge=1, le=20, description="Maximum suggestions")


class SynonymParams(BaseModel):
    """Parameters for synonym endpoint."""
    
    max_results: int = Field(default=10, ge=1, le=20, description="Maximum synonyms")