"""Learning statistics and analytics for wordlists."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .constants import MasteryLevel

if TYPE_CHECKING:
    from .models import WordListItem


class LearningStats(BaseModel):
    """Learning statistics for a word list."""

    total_reviews: int = Field(default=0, ge=0, description="Total review sessions")
    words_mastered: int = Field(default=0, ge=0, description="Words at gold level")
    average_ease_factor: float = Field(
        default=2.5, ge=1.3, description="Average difficulty"
    )
    retention_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Success rate"
    )
    streak_days: int = Field(default=0, ge=0, description="Consecutive study days")
    last_study_date: datetime | None = Field(
        default=None, description="Last study session"
    )
    study_time_minutes: int = Field(default=0, ge=0, description="Total study time")

    def update_from_words(self, words: list["WordListItem"]) -> None:
        """Update statistics based on word list data."""
        if not words:
            return

        # Count mastered words
        self.words_mastered = sum(
            1 for w in words if w.mastery_level == MasteryLevel.GOLD
        )

        # Calculate average ease factor
        ease_factors = [w.review_data.ease_factor for w in words]
        if ease_factors:
            self.average_ease_factor = sum(ease_factors) / len(ease_factors)

        # Calculate retention rate
        total_reviews = sum(w.review_data.repetitions for w in words)
        total_lapses = sum(w.review_data.lapse_count for w in words)
        if total_reviews > 0:
            self.retention_rate = 1 - (total_lapses / (total_reviews + total_lapses))

    def record_study_session(self, duration_minutes: int) -> None:
        """Record a study session and update statistics."""
        self.study_time_minutes += duration_minutes
        self.total_reviews += 1

        # Update streak
        now = datetime.now()
        if self.last_study_date:
            days_since = (now.date() - self.last_study_date.date()).days
            if days_since == 1:
                self.streak_days += 1
            elif days_since > 1:
                self.streak_days = 1
        else:
            self.streak_days = 1

        self.last_study_date = now

    def is_streak_active(self) -> bool:
        """Check if study streak is still active."""
        if not self.last_study_date:
            return False

        days_since = (datetime.now().date() - self.last_study_date.date()).days
        return days_since <= 1

    def get_mastery_distribution(
        self, words: list["WordListItem"]
    ) -> dict[MasteryLevel, int]:
        """Get distribution of words by mastery level."""
        distribution = {level: 0 for level in MasteryLevel}
        for word in words:
            distribution[word.mastery_level] += 1
        return distribution

    def get_study_time_hours(self) -> float:
        """Get total study time in hours."""
        return self.study_time_minutes / 60.0

    def get_average_session_minutes(self) -> float:
        """Get average study session duration."""
        if self.total_reviews == 0:
            return 0.0
        return self.study_time_minutes / self.total_reviews