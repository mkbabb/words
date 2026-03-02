"""SearchResult Pydantic model for unified search results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models.base import Language
from .constants import SearchMethod


class SearchResult(BaseModel):
    """Unified search result across all search methods."""

    word: str = Field(..., description="Matched word or phrase")
    lemmatized_word: str | None = Field(
        None,
        description="Lemmatized form of the word if applicable",
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    method: SearchMethod = Field(
        ...,
        description="Search method used (exact, fuzzy, semantic)",
    )
    language: Language | None = Field(None, description="Language code if applicable")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    def __lt__(self, other: SearchResult) -> bool:
        """Compare by score for sorting (higher score is better)."""
        return self.score > other.score

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "word": "example",
                "score": 0.95,
                "method": "exact",
                "language": "en",
                "metadata": {"frequency": 1000},
            },
        }
    )


__all__ = [
    "SearchResult",
]
