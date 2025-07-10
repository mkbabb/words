"""API models for requests and responses."""

from .requests import LookupParams, SearchParams, SuggestionsParams, SynonymParams
from .responses import (
    HealthResponse,
    LookupResponse,
    SearchResponse,
    SearchResultItem,
    SuggestionsAPIResponse,
    SynonymItem,
    SynonymResponse,
)

__all__ = [
    "SuggestionsParams",
    "LookupParams",
    "SearchParams", 
    "SynonymParams",
    "SuggestionsAPIResponse",
    "HealthResponse",
    "LookupResponse",
    "SearchResponse",
    "SearchResultItem",
    "SynonymItem",
    "SynonymResponse",
]