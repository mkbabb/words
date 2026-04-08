"""Wordlist API response models.

These types are exposed via FastAPI's `response_model` parameter so they
appear in the OpenAPI schema. The frontend imports them via
`openapi-typescript` and reuses them as the canonical type definitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ....wordlist.constants import CardState, MasteryLevel, Temperature
from ....wordlist.review import ReviewData, ReviewHistoryItem
from ....wordlist.stats import LearningStats

# Re-export the canonical sub-models so they appear in the OpenAPI schema
# via reference from the response models below.
__all__ = [
    "CardState",
    "LearningStats",
    "MasteryDistribution",
    "MasteryLevel",
    "ReviewData",
    "ReviewHistoryItem",
    "Temperature",
    "WordListItemResponse",
    "WordListResponse",
    "WordListStatistics",
]


class WordListItemResponse(BaseModel):
    """API response shape for a single wordlist item.

    Differs from the persisted `WordListItem` model in one key way:
    the `word_id` ObjectId FK is resolved to the canonical `word` text
    string for client convenience.
    """

    word: str = Field(..., description="Resolved word text (FK resolved from word_id)")
    frequency: int = Field(..., ge=1, description="Number of occurrences in list")
    selected_definition_ids: list[str] = Field(
        default_factory=list,
        description="Selected Definition document IDs",
    )
    mastery_level: MasteryLevel = Field(..., description="Current mastery level")
    temperature: Temperature = Field(..., description="Learning temperature state")
    review_data: ReviewData = Field(..., description="Spaced repetition data")
    last_visited: datetime | None = Field(None, description="Last viewed timestamp")
    added_date: datetime = Field(..., description="When added to list")
    suspended: bool = Field(default=False, description="Suspended from reviews (leech management)")
    notes: str = Field(default="", description="User notes about the word")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")


class WordListResponse(BaseModel):
    """API response shape for a wordlist (metadata, no embedded items).

    Items are loaded separately via `GET /wordlists/{id}/words`.
    """

    id: str = Field(..., description="MongoDB document ID")
    name: str = Field(..., description="Human-readable list name")
    description: str = Field(default="", description="List description / purpose")
    hash_id: str = Field(..., description="Content-based hash identifier")

    total_words: int = Field(..., ge=0, description="Total word count")
    unique_words: int = Field(..., ge=0, description="Unique word count")
    learning_stats: LearningStats = Field(..., description="Aggregated learning statistics")

    tags: list[str] = Field(default_factory=list, description="List categorization tags")
    is_public: bool = Field(default=False, description="Public visibility flag")
    owner_id: str | None = Field(None, description="Owner user ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    last_accessed: datetime | None = Field(None, description="Last access timestamp")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class MasteryDistribution(BaseModel):
    """Counts of items at each mastery level."""

    default: int = Field(default=0, ge=0)
    bronze: int = Field(default=0, ge=0)
    silver: int = Field(default=0, ge=0)
    gold: int = Field(default=0, ge=0)


class WordListStatistics(BaseModel):
    """Detailed statistics for a single wordlist."""

    total_words: int = Field(..., ge=0)
    unique_words: int = Field(..., ge=0)
    mastery_distribution: MasteryDistribution = Field(..., description="Mastery level breakdown")
    study_sessions: int = Field(..., ge=0, description="Total study session count")
    total_study_time: int = Field(..., ge=0, description="Total study time in minutes")
