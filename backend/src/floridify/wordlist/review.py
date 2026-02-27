"""Spaced repetition review logic using SM-2 algorithm."""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from .constants import (
    SM2_DEFAULT_EASE_FACTOR,
    SM2_INITIAL_INTERVALS,
    SM2_MAX_EASE_FACTOR,
    SM2_MIN_EASE_FACTOR,
    SM2_QUALITY_THRESHOLD,
)


class ReviewHistoryItem(BaseModel):
    """Single review session record."""

    date: datetime
    quality: int = Field(ge=0, le=5, description="Review quality (0-5)")
    interval: int = Field(ge=1, description="Days until next review")
    ease_factor: float = Field(ge=SM2_MIN_EASE_FACTOR, description="Difficulty multiplier")


class ReviewData(BaseModel):
    """Spaced repetition data following SM-2 algorithm."""

    repetitions: int = Field(default=0, ge=0, description="Successful review count")
    ease_factor: float = Field(
        default=SM2_DEFAULT_EASE_FACTOR,
        ge=SM2_MIN_EASE_FACTOR,
        description="Difficulty multiplier",
    )
    interval: int = Field(default=1, ge=1, description="Days until next review")
    next_review_date: datetime = Field(
        default_factory=datetime.now,
        description="Next scheduled review",
    )
    last_review_date: datetime | None = Field(default=None, description="Last review timestamp")
    lapse_count: int = Field(default=0, ge=0, description="Total failure count")
    review_history: list[ReviewHistoryItem] = Field(
        default_factory=list,
        description="Review session history",
    )

    def calculate_next_interval(self, quality: int) -> int:
        """Calculate next review interval based on SM-2 algorithm."""
        if quality < SM2_QUALITY_THRESHOLD:
            return 1

        if self.repetitions == 0:
            return SM2_INITIAL_INTERVALS.get(1, 1)
        if self.repetitions == 1:
            return SM2_INITIAL_INTERVALS.get(2, 6)
        return round(self.interval * self.ease_factor)

    def calculate_ease_factor(self, quality: int) -> float:
        """Calculate new ease factor based on review quality.

        Clamped to [SM2_MIN_EASE_FACTOR, SM2_MAX_EASE_FACTOR] to prevent
        unbounded growth from repeated perfect recalls.
        """
        if quality < SM2_QUALITY_THRESHOLD:
            return self.ease_factor

        new_ef = self.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        return max(SM2_MIN_EASE_FACTOR, min(new_ef, SM2_MAX_EASE_FACTOR))

    def update_sm2(self, quality: int) -> None:
        """Update using SM-2 algorithm (quality: 0-5)."""
        if quality < SM2_QUALITY_THRESHOLD:
            self.repetitions = 0
            self.interval = 1
            self.lapse_count += 1
        else:
            self.repetitions += 1
            self.interval = self.calculate_next_interval(quality)

        # Update ease factor
        self.ease_factor = self.calculate_ease_factor(quality)

        # Calculate next review date
        self.last_review_date = datetime.now()
        self.next_review_date = self.last_review_date + timedelta(days=self.interval)

        # Add to history
        self.review_history.append(
            ReviewHistoryItem(
                date=self.last_review_date,
                quality=quality,
                interval=self.interval,
                ease_factor=self.ease_factor,
            ),
        )

    def is_due_for_review(self, reference_date: datetime | None = None) -> bool:
        """Check if item is due for review."""
        if reference_date is None:
            reference_date = datetime.now()
        return self.next_review_date <= reference_date

    def get_overdue_days(self, reference_date: datetime | None = None) -> int:
        """Get number of days overdue (negative if not due yet)."""
        if reference_date is None:
            reference_date = datetime.now()
        delta = reference_date - self.next_review_date
        return delta.days

    def get_retention_rate(self) -> float:
        """Calculate retention rate based on review history."""
        if self.repetitions == 0:
            return 0.0
        total_reviews = self.repetitions + self.lapse_count
        if total_reviews == 0:
            return 0.0
        return self.repetitions / total_reviews
