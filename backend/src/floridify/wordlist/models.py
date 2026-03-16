"""Word list data models with integrated business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

from ..models.base import BaseMetadataWithAccess
from .constants import COOLING_THRESHOLD_HOURS, CardState, MasteryLevel, Temperature
from .review import ReviewData
from .stats import LearningStats


class WordListItem(BaseModel):
    """Word reference with learning metadata and spaced repetition data."""

    # Foreign key to Word model - optimized with ObjectId
    word_id: PydanticObjectId = Field(..., description="FK to Word document")

    # Learning metadata
    frequency: int = Field(default=1, ge=1, description="Number of occurrences in list")
    selected_definition_ids: list[PydanticObjectId] = Field(
        default_factory=list,
        description="FK to selected Definition documents",
    )
    mastery_level: MasteryLevel = Field(
        default=MasteryLevel.DEFAULT,
        description="Current mastery level",
    )
    temperature: Temperature = Field(
        default=Temperature.COLD,
        description="Learning temperature state",
    )
    review_data: ReviewData = Field(
        default_factory=ReviewData,
        description="Spaced repetition data",
    )

    # Timestamps
    last_visited: datetime | None = Field(
        default=None,
        description="Last time word was viewed/studied",
    )
    added_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When added to list",
    )

    # User metadata
    notes: str = Field(default="", description="User notes about the word")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")

    def increment(self) -> None:
        """Increment frequency."""
        self.frequency += 1

    def mark_visited(self) -> None:
        """Mark word as visited/viewed."""
        self.last_visited = datetime.now(UTC)
        self.temperature = Temperature.HOT

    def update_temperature(self) -> None:
        """Lazy temperature cooling based on time since last visit."""
        if self.temperature == Temperature.HOT and self.last_visited:
            # MongoDB strips tzinfo, so re-attach UTC if naive
            last = self.last_visited
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            hours_since = (datetime.now(UTC) - last).total_seconds() / 3600
            if hours_since >= COOLING_THRESHOLD_HOURS:
                self.temperature = Temperature.COLD

    def review(self, quality: int) -> MasteryLevel:
        """Process a review session. Returns previous mastery level."""
        previous_mastery = self.mastery_level
        self.review_data.update_sm2(quality)
        self.last_visited = datetime.now(UTC)
        self.temperature = Temperature.HOT

        # Update mastery based on card state
        self._update_mastery_level()
        return previous_mastery

    def _update_mastery_level(self) -> None:
        """Update mastery level based on card state (Anki-grade)."""
        state = self.review_data.card_state
        if state in (CardState.NEW, CardState.LEARNING):
            self.mastery_level = MasteryLevel.DEFAULT
        elif state == CardState.RELEARNING:
            self.mastery_level = MasteryLevel.BRONZE  # Demoted on lapse
        elif state == CardState.YOUNG:
            if self.review_data.repetitions >= 5 and self.review_data.ease_factor >= 2.3:
                self.mastery_level = MasteryLevel.SILVER
            else:
                self.mastery_level = MasteryLevel.BRONZE
        elif state == CardState.MATURE:
            self.mastery_level = MasteryLevel.GOLD

    def is_due_for_review(self) -> bool:
        """Check if word is due for review."""
        return self.review_data.is_due_for_review()

    def get_overdue_days(self) -> int:
        """Get number of days overdue for review."""
        return self.review_data.get_overdue_days()


class WordListItemDoc(Document, WordListItem):
    """Persistent WordListItem stored in its own collection."""

    wordlist_id: PydanticObjectId = Field(..., description="FK to WordList document")

    class Settings:
        name = "word_list_items"
        indexes = [
            IndexModel(
                [("wordlist_id", ASCENDING), ("word_id", ASCENDING)],
                unique=True,
            ),
            [("wordlist_id", 1), ("review_data.next_review_date", 1)],
            [("wordlist_id", 1), ("mastery_level", 1)],
            [("wordlist_id", 1), ("added_date", -1)],
            [("wordlist_id", 1), ("temperature", 1)],
        ]


class WordList(Document, BaseMetadataWithAccess):
    """Word list with learning metadata and statistics."""

    name: str = Field(..., description="Human-readable list name")
    description: str = Field(default="", description="List description/purpose")
    hash_id: str = Field(..., description="Content-based hash identifier")

    # Statistics
    total_words: int = Field(default=0, ge=0, description="Total word count")
    unique_words: int = Field(default=0, ge=0, description="Unique word count")
    learning_stats: LearningStats = Field(
        default_factory=LearningStats,
        description="Aggregated learning statistics",
    )

    # Metadata
    tags: list[str] = Field(
        default_factory=list,
        description="List categorization tags",
    )
    is_public: bool = Field(default=False, description="Public visibility flag")
    owner_id: str | None = Field(default=None, description="Owner user ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    class Settings:
        name = "word_lists"
        indexes = [
            "name",
            "hash_id",
            [("name", "text")],
            "created_at",
            "updated_at",
            "last_accessed",
            "owner_id",
        ]

    def set_stats(
        self,
        unique_words: int,
        total_words: int,
        learning_stats: LearningStats,
    ) -> None:
        """Set statistics from externally computed values.

        Args:
            unique_words: Number of unique words in the list
            total_words: Total word count (sum of frequencies)
            learning_stats: Pre-computed learning statistics

        """
        self.unique_words = unique_words
        self.total_words = total_words
        self.learning_stats = learning_stats
        self.mark_updated()

    def record_study_session(self, duration_minutes: int) -> None:
        """Record a study session."""
        self.learning_stats.record_study_session(duration_minutes)
        self.mark_accessed()
