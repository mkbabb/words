"""Word list data models with integrated business logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field

from ..models.base import BaseMetadata
from .constants import MasteryLevel, Temperature
from .review import ReviewData
from .stats import LearningStats


class WordListItem(BaseModel):
    """Word reference with learning metadata and spaced repetition data."""

    # Foreign key to Word model
    word_id: str = Field(..., description="FK to Word document")
    
    # Cached word text for quick access (denormalized for performance)
    text: str = Field(..., description="Cached word text")
    
    # WordList-specific fields
    frequency: int = Field(default=1, ge=1, description="Number of occurrences in list")
    selected_definition_ids: list[str] = Field(
        default_factory=list, description="FK to selected Definition documents"
    )
    
    # Learning metadata
    mastery_level: MasteryLevel = Field(
        default=MasteryLevel.DEFAULT, description="Current mastery level"
    )
    temperature: Temperature = Field(
        default=Temperature.COLD, description="Learning temperature state"
    )
    review_data: ReviewData = Field(
        default_factory=ReviewData, description="Spaced repetition data"
    )
    
    # Timestamps
    last_visited: datetime | None = Field(
        default=None, description="Last time word was viewed/studied"
    )
    added_date: datetime = Field(default_factory=datetime.now, description="When added to list")
    created_at: datetime = Field(
        default_factory=datetime.now, description="First occurrence timestamp"
    )
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    # User metadata
    notes: str = Field(default="", description="User notes about the word")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")

    def increment(self) -> None:
        """Increment frequency and update timestamp."""
        self.frequency += 1
        self.updated_at = datetime.now()

    def mark_visited(self) -> None:
        """Mark word as visited/viewed."""
        self.last_visited = datetime.now()
        self.temperature = Temperature.HOT
        self.updated_at = datetime.now()

    def review(self, quality: int) -> None:
        """Process a review session."""
        self.review_data.update_sm2(quality)
        self.last_visited = datetime.now()
        self.temperature = Temperature.HOT
        self.updated_at = datetime.now()

        # Update mastery based on performance
        self._update_mastery_level()

    def _update_mastery_level(self) -> None:
        """Update mastery level based on review performance."""
        if self.review_data.repetitions >= 10 and self.review_data.ease_factor >= 2.5:
            self.mastery_level = MasteryLevel.GOLD
        elif self.review_data.repetitions >= 5:
            self.mastery_level = MasteryLevel.SILVER
        elif self.review_data.repetitions > 0:
            self.mastery_level = MasteryLevel.BRONZE

    def is_due_for_review(self) -> bool:
        """Check if word is due for review."""
        return self.review_data.is_due_for_review()

    def get_overdue_days(self) -> int:
        """Get number of days overdue for review."""
        return self.review_data.get_overdue_days()


class WordList(Document, BaseMetadata):
    """Word list with learning metadata and statistics."""

    name: str = Field(..., description="Human-readable list name")
    description: str = Field(default="", description="List description/purpose")
    hash_id: str = Field(..., description="Content-based hash identifier")
    words: list[WordListItem] = Field(default_factory=list, description="Words with learning data")
    total_words: int = Field(default=0, ge=0, description="Total word count")
    unique_words: int = Field(default=0, ge=0, description="Unique word count")
    learning_stats: LearningStats = Field(
        default_factory=LearningStats, description="Aggregated learning statistics"
    )
    last_accessed: datetime | None = Field(default=None, description="Last time list was accessed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: list[str] = Field(default_factory=list, description="List categorization tags")
    is_public: bool = Field(default=False, description="Public visibility flag")
    owner_id: str | None = Field(default=None, description="Owner user ID")

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

    def add_words(self, new_words: list[tuple[str, str]]) -> None:
        """Add words to the list, updating frequencies for duplicates.
        
        Args:
            new_words: List of (word_id, text) tuples
        """
        word_map = {w.text.lower(): w for w in self.words}

        for word_id, word_text in new_words:
            word_clean = word_text.strip()
            if not word_clean:
                continue

            word_lower = word_clean.lower()
            if word_lower in word_map:
                word_map[word_lower].increment()
            else:
                new_word_item = WordListItem(
                    word_id=word_id,
                    text=word_clean
                )
                self.words.append(new_word_item)
                word_map[word_lower] = new_word_item

        self.update_stats()

    def update_stats(self) -> None:
        """Update all statistics and timestamp."""
        self.unique_words = len(self.words)
        self.total_words = sum(w.frequency for w in self.words)
        self.updated_at = datetime.now()

        # Update learning statistics from words
        self.learning_stats.update_from_words(self.words)

    def get_most_frequent(self, limit: int = 10) -> list[WordListItem]:
        """Get most frequent words (highest interest)."""
        return sorted(self.words, key=lambda w: w.frequency, reverse=True)[:limit]

    def get_due_for_review(self, limit: int | None = None) -> list[WordListItem]:
        """Get words due for review, ordered by urgency."""
        due_words = [w for w in self.words if w.is_due_for_review()]
        # Sort by how overdue they are (most overdue first)
        due_words.sort(key=lambda w: w.get_overdue_days(), reverse=True)
        return due_words[:limit] if limit else due_words

    def get_by_mastery(self, level: MasteryLevel) -> list[WordListItem]:
        """Get words at a specific mastery level."""
        return [w for w in self.words if w.mastery_level == level]

    def get_hot_words(self, limit: int = 10) -> list[WordListItem]:
        """Get recently studied 'hot' words."""
        hot = [w for w in self.words if w.temperature == Temperature.HOT]
        hot.sort(key=lambda w: w.last_visited or w.added_date, reverse=True)
        return hot[:limit]

    def get_word_frequency(self, word_text: str) -> int:
        """Get frequency of a specific word by text."""
        word_lower = word_text.lower()
        for w in self.words:
            if w.text.lower() == word_lower:
                return w.frequency
        return 0

    def get_word_item(self, word_text: str) -> WordListItem | None:
        """Get WordListItem for a specific word by text."""
        word_lower = word_text.lower()
        for w in self.words:
            if w.text.lower() == word_lower:
                return w
        return None
    
    def get_word_item_by_id(self, word_id: str) -> WordListItem | None:
        """Get WordListItem by word ID."""
        for w in self.words:
            if w.word_id == word_id:
                return w
        return None

    def mark_accessed(self) -> None:
        """Mark list as accessed."""
        self.last_accessed = datetime.now()
        self.updated_at = datetime.now()

    def record_study_session(self, duration_minutes: int) -> None:
        """Record a study session."""
        self.learning_stats.record_study_session(duration_minutes)
        self.mark_accessed()

    def get_mastery_distribution(self) -> dict[MasteryLevel, int]:
        """Get distribution of words by mastery level."""
        return self.learning_stats.get_mastery_distribution(self.words)
