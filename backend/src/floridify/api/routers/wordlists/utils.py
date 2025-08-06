"""Utility functions for wordlist searching - DISABLED for KISS approach."""

from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    word: str = Field(..., description="Matched word")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    method: str = Field(..., description="Search method used")
    is_phrase: bool = Field(False, description="Whether this is a phrase")


def get_adaptive_min_score(query: str, base_score: float = 0.4) -> float:
    """Get adaptive minimum score - stubbed."""
    return base_score


async def search_wordlist_names(
    query: str,
    owner_id: str | None = None,
    max_results: int = 20,
    min_score: float = 0.6,
) -> list[dict[str, Any]]:
    """Search wordlist names - stubbed."""
    return []


async def search_words_in_wordlist(
    wordlist_id: PydanticObjectId,
    query: str,
    max_results: int = 20,
    min_score: float = 0.6,
) -> list[dict[str, Any]]:
    """Search words in wordlist - stubbed."""
    return []


async def invalidate_wordlist_corpus(wordlist_id: PydanticObjectId) -> None:
    """Invalidate wordlist corpus - stubbed."""
    pass


async def invalidate_wordlist_names_corpus() -> None:
    """Invalidate wordlist names corpus - stubbed."""
    pass


async def get_corpus_stats() -> dict[str, Any]:
    """Get corpus statistics - stubbed."""
    return {}