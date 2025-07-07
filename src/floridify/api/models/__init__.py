"""API models for requests and responses."""

from .requests import LookupParams, SearchParams, SuggestionParams, SynonymParams
from .responses import (
    HealthResponse,
    LookupResponse,
    SearchResponse,
    SearchResultItem,
    SuggestionResponse,
    SynonymItem,
    SynonymResponse,
)

__all__ = [
    "LookupParams",
    "SearchParams", 
    "SuggestionParams",
    "SynonymParams",
    "HealthResponse",
    "LookupResponse",
    "SearchResponse",
    "SearchResultItem",
    "SuggestionResponse",
    "SynonymItem",
    "SynonymResponse",
]