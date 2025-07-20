"""Enhanced word list models with spaced repetition and learning features."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field


class MasteryLevel(str, Enum):
    """Learning mastery level."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class Temperature(str, Enum):
    """Learning temperature state."""

    HOT = "hot"  # Recently studied, fresh in memory
    COLD = "cold"  # Not studied recently, needs review


class ReviewData(BaseModel):
    """Spaced repetition data following SM-2 algorithm."""

    repetitions: int = Field(default=0, ge=0, description="Successful review count")
    ease_factor: float = Field(default=2.5, ge=1.3, description="Difficulty multiplier")
    interval: int = Field(default=1, ge=1, description="Days until next review")
    next_review_date: datetime = Field(
        default_factory=datetime.now, description="Next scheduled review"
    )
    last_review_date: datetime | None = Field(default=None, description="Last review timestamp")
    lapse_count: int = Field(default=0, ge=0, description="Total failure count")
    review_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Review session history"
    )

    def update_sm2(self, quality: int) -> None:
        """Update using SM-2 algorithm (quality: 0-5)."""
        if quality < 3:
            self.repetitions = 0
            self.interval = 1
            self.lapse_count += 1
        else:
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval = 1
            elif self.repetitions == 2:
                self.interval = 6
            else:
                self.interval = round(self.interval * self.ease_factor)

        # Update ease factor
        if quality >= 3:
            new_ef = self.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
            self.ease_factor = max(1.3, new_ef)

        # Calculate next review date
        self.last_review_date = datetime.now()
        self.next_review_date = self.last_review_date + timedelta(days=self.interval)

        # Add to history
        self.review_history.append(
            {
                "date": self.last_review_date.isoformat(),
                "quality": quality,
                "interval": self.interval,
                "ease_factor": self.ease_factor,
            }
        )


class WordListItem(BaseModel):
    """Word with learning metadata and spaced repetition data."""

    text: str = Field(..., description="The word text")
    frequency: int = Field(default=1, ge=1, description="Number of occurrences in list")
    selected_definitions: list[int] = Field(
        default_factory=list, description="Indices of selected definitions"
    )
    mastery_level: MasteryLevel = Field(
        default=MasteryLevel.BRONZE, description="Current mastery level"
    )
    temperature: Temperature = Field(
        default=Temperature.COLD, description="Learning temperature state"
    )
    review_data: ReviewData = Field(
        default_factory=ReviewData, description="Spaced repetition data"
    )
    last_visited: datetime | None = Field(
        default=None, description="Last time word was viewed/studied"
    )
    added_date: datetime = Field(default_factory=datetime.now, description="When added to list")
    created_at: datetime = Field(
        default_factory=datetime.now, description="First occurrence timestamp"
    )
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
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
        if self.review_data.repetitions >= 10 and self.review_data.ease_factor >= 2.5:
            self.mastery_level = MasteryLevel.GOLD
        elif self.review_data.repetitions >= 5:
            self.mastery_level = MasteryLevel.SILVER


class LearningStats(BaseModel):
    """Learning statistics for a word list."""

    total_reviews: int = Field(default=0, ge=0, description="Total review sessions")
    words_mastered: int = Field(default=0, ge=0, description="Words at gold level")
    average_ease_factor: float = Field(default=2.5, ge=1.3, description="Average difficulty")
    retention_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate")
    streak_days: int = Field(default=0, ge=0, description="Consecutive study days")
    last_study_date: datetime | None = Field(default=None, description="Last study session")
    study_time_minutes: int = Field(default=0, ge=0, description="Total study time")


class WordList(Document):
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
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
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

    @classmethod
    def generate_hash(cls, words: list[str]) -> str:
        """Generate content-based hash from word list."""
        # Sort words to ensure consistent hash regardless of order
        sorted_words = sorted(set(w.lower().strip() for w in words if w.strip()))
        content = "|".join(sorted_words)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add_words(self, new_words: list[str]) -> None:
        """Add words to the list, updating frequencies for duplicates."""
        word_map = {w.text.lower(): w for w in self.words}

        for word in new_words:
            word_clean = word.strip()
            if not word_clean:
                continue

            word_lower = word_clean.lower()
            if word_lower in word_map:
                word_map[word_lower].increment()
            else:
                new_word_item = WordListItem(text=word_clean)
                self.words.append(new_word_item)
                word_map[word_lower] = new_word_item

        self.update_stats()

    def update_stats(self) -> None:
        """Update all statistics and timestamp."""
        self.unique_words = len(self.words)
        self.total_words = sum(w.frequency for w in self.words)
        self.updated_at = datetime.now()

        # Update learning statistics
        if self.words:
            mastered = sum(1 for w in self.words if w.mastery_level == MasteryLevel.GOLD)
            self.learning_stats.words_mastered = mastered

            ease_factors = [w.review_data.ease_factor for w in self.words]
            self.learning_stats.average_ease_factor = sum(ease_factors) / len(ease_factors)

            total_reviews = sum(w.review_data.repetitions for w in self.words)
            total_lapses = sum(w.review_data.lapse_count for w in self.words)
            if total_reviews > 0:
                self.learning_stats.retention_rate = 1 - (total_lapses / total_reviews)

        # Update hash based on current words
        word_texts = [w.text for w in self.words]
        self.hash_id = self.generate_hash(word_texts)

    def get_most_frequent(self, limit: int = 10) -> list[WordListItem]:
        """Get most frequent words (highest interest)."""
        return sorted(self.words, key=lambda w: w.frequency, reverse=True)[:limit]

    def get_due_for_review(self, limit: int | None = None) -> list[WordListItem]:
        """Get words due for review, ordered by urgency."""
        now = datetime.now()
        due_words = [w for w in self.words if w.review_data.next_review_date <= now]
        # Sort by how overdue they are
        due_words.sort(key=lambda w: w.review_data.next_review_date)
        return due_words[:limit] if limit else due_words

    def get_by_mastery(self, level: MasteryLevel) -> list[WordListItem]:
        """Get words at a specific mastery level."""
        return [w for w in self.words if w.mastery_level == level]

    def get_hot_words(self, limit: int = 10) -> list[WordListItem]:
        """Get recently studied 'hot' words."""
        hot = [w for w in self.words if w.temperature == Temperature.HOT]
        hot.sort(key=lambda w: w.last_visited or w.added_date, reverse=True)
        return hot[:limit]

    def get_word_frequency(self, word: str) -> int:
        """Get frequency of a specific word."""
        word_lower = word.lower()
        for w in self.words:
            if w.text.lower() == word_lower:
                return w.frequency
        return 0

    def get_word_item(self, word: str) -> WordListItem | None:
        """Get WordListItem for a specific word."""
        word_lower = word.lower()
        for w in self.words:
            if w.text.lower() == word_lower:
                return w
        return None

    def mark_accessed(self) -> None:
        """Mark list as accessed."""
        self.last_accessed = datetime.now()
        self.updated_at = datetime.now()

    def record_study_session(self, duration_minutes: int) -> None:
        """Record a study session."""
        self.learning_stats.study_time_minutes += duration_minutes
        self.learning_stats.total_reviews += 1

        # Update streak
        now = datetime.now()
        if self.learning_stats.last_study_date:
            days_since = (now.date() - self.learning_stats.last_study_date.date()).days
            if days_since == 1:
                self.learning_stats.streak_days += 1
            elif days_since > 1:
                self.learning_stats.streak_days = 1
        else:
            self.learning_stats.streak_days = 1

        self.learning_stats.last_study_date = now
        self.mark_accessed()
