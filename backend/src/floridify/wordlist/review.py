"""Anki-grade spaced repetition review logic.

Implements SM-2 with card states, learning/relearning steps,
leech detection, interval caps, and fuzz.
"""

import random
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from .constants import (
    EASY_BONUS,
    EASY_INTERVAL_DAYS,
    GRADUATING_INTERVAL_DAYS,
    HARD_INTERVAL_MULTIPLIER,
    INTERVAL_FUZZ_RANGE,
    LEARNING_STEPS_MINUTES,
    LEECH_THRESHOLD,
    MATURE_INTERVAL_DAYS,
    MAX_INTERVAL_DAYS,
    MAX_REVIEW_HISTORY,
    RELEARNING_STEPS_MINUTES,
    SM2_DEFAULT_EASE_FACTOR,
    SM2_MAX_EASE_FACTOR,
    SM2_MIN_EASE_FACTOR,
    SM2_QUALITY_THRESHOLD,
    CardState,
)


class ReviewHistoryItem(BaseModel):
    """Single review session record."""

    date: datetime
    quality: int = Field(ge=0, le=5, description="Review quality (0-5)")
    interval: float = Field(ge=0, description="Interval (days or fraction of day)")
    ease_factor: float = Field(ge=SM2_MIN_EASE_FACTOR, description="Difficulty multiplier")
    card_state: CardState = Field(default=CardState.NEW, description="Card state after review")


class ReviewData(BaseModel):
    """Spaced repetition data following Anki-grade SM-2 algorithm."""

    repetitions: int = Field(default=0, ge=0, description="Successful review count")
    ease_factor: float = Field(
        default=SM2_DEFAULT_EASE_FACTOR,
        ge=SM2_MIN_EASE_FACTOR,
        description="Difficulty multiplier",
    )
    interval: float = Field(
        default=0, ge=0, description="Current interval in days (can be fractional for sub-day)"
    )
    next_review_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Next scheduled review (minute-precision for learning steps)",
    )
    last_review_date: datetime | None = Field(default=None, description="Last review timestamp")
    lapse_count: int = Field(default=0, ge=0, description="Total failure count")
    review_history: list[ReviewHistoryItem] = Field(
        default_factory=list,
        description="Review session history",
    )

    # Anki-grade card state tracking
    card_state: CardState = Field(default=CardState.NEW, description="Current card state")
    learning_step: int = Field(
        default=0, ge=0, description="Current step index in LEARNING/RELEARNING"
    )
    is_leech: bool = Field(default=False, description="Flagged as problematic card")
    graduated_interval: float = Field(
        default=GRADUATING_INTERVAL_DAYS,
        description="Interval before lapse (for relearning graduation)",
    )

    def process_review(self, quality: int) -> None:
        """Process a review with Anki-grade card state logic.

        Quality mapping:
        - 0 (Again): Complete failure
        - 1 (Hard): Incorrect; answer remembered after reveal
        - 2 (Difficult): Incorrect but close
        - 3 (Okay): Correct with significant difficulty
        - 4 (Good): Correct with minor hesitation
        - 5 (Easy): Perfect, effortless recall
        """
        now = datetime.now(UTC)

        if self.card_state == CardState.NEW:
            # First review: enter learning (Again on NEW is not a lapse)
            self.card_state = CardState.LEARNING
            self._process_learning(quality, LEARNING_STEPS_MINUTES)
        elif self.card_state == CardState.LEARNING:
            self._process_learning(quality, LEARNING_STEPS_MINUTES)
        elif self.card_state == CardState.RELEARNING:
            self._process_learning(quality, RELEARNING_STEPS_MINUTES, is_relearning=True)
        elif self.card_state in (CardState.YOUNG, CardState.MATURE):
            self._process_review(quality)

        # Cap interval
        self.interval = min(self.interval, MAX_INTERVAL_DAYS)

        # Update review date
        self.last_review_date = now
        if self.interval < 1:
            # Sub-day interval: use minutes
            minutes = self.interval * 24 * 60
            self.next_review_date = now + timedelta(minutes=max(minutes, 1))
        else:
            self.next_review_date = now + timedelta(days=self.interval)

        # Update card state based on interval
        if self.card_state in (CardState.YOUNG, CardState.MATURE):
            if self.interval >= MATURE_INTERVAL_DAYS:
                self.card_state = CardState.MATURE
            else:
                self.card_state = CardState.YOUNG

        # Record history (capped)
        self.review_history.append(
            ReviewHistoryItem(
                date=now,
                quality=quality,
                interval=self.interval,
                ease_factor=self.ease_factor,
                card_state=self.card_state,
            ),
        )
        if len(self.review_history) > MAX_REVIEW_HISTORY:
            self.review_history = self.review_history[-MAX_REVIEW_HISTORY:]

    def _process_learning(
        self,
        quality: int,
        steps: list[int],
        is_relearning: bool = False,
    ) -> None:
        """Process review for LEARNING or RELEARNING cards."""
        if quality < SM2_QUALITY_THRESHOLD:
            # Again: reset to step 0
            self.learning_step = 0
            self.card_state = CardState.RELEARNING if is_relearning else CardState.LEARNING
            self.interval = steps[0] / (24 * 60)  # Convert minutes to days
            # Note: lapse_count is only incremented in _process_review when YOUNG/MATURE fails
        elif quality == 5:
            # Easy: skip remaining steps, graduate immediately
            self._graduate(easy=True, is_relearning=is_relearning)
        else:
            # Good/Hard: advance to next step
            next_step = self.learning_step + 1
            if next_step >= len(steps):
                # No more steps, graduate
                self._graduate(easy=False, is_relearning=is_relearning)
            else:
                self.learning_step = next_step
                self.card_state = CardState.RELEARNING if is_relearning else CardState.LEARNING
                self.interval = steps[next_step] / (24 * 60)  # Convert minutes to days

    def _graduate(self, easy: bool = False, is_relearning: bool = False) -> None:
        """Graduate from learning/relearning to review state."""
        if easy:
            self.interval = EASY_INTERVAL_DAYS
        elif is_relearning:
            # Graduate back to previous interval (not reset to 1 day)
            self.interval = max(self.graduated_interval, GRADUATING_INTERVAL_DAYS)
        else:
            self.interval = GRADUATING_INTERVAL_DAYS

        self.card_state = CardState.YOUNG
        self.repetitions += 1
        self.learning_step = 0

    def _process_review(self, quality: int) -> None:
        """Process review for YOUNG/MATURE cards."""
        if quality < SM2_QUALITY_THRESHOLD:
            # Lapse: enter relearning
            self.graduated_interval = self.interval  # Save for relearning graduation
            self.card_state = CardState.RELEARNING
            self.learning_step = 0
            self.interval = RELEARNING_STEPS_MINUTES[0] / (24 * 60)
            self.lapse_count += 1
            self.repetitions = 0
            self._check_leech()
        else:
            # Successful review
            self.repetitions += 1

            if quality == 2:
                # Hard: slight increase, no EF change
                self.interval = round(self.interval * HARD_INTERVAL_MULTIPLIER)
            elif quality == 5:
                # Easy: bonus multiplier
                new_ef = self._calculate_ease_factor(quality)
                self.ease_factor = new_ef
                self.interval = self._fuzz(round(self.interval * self.ease_factor * EASY_BONUS))
            else:
                # Good (3 or 4): standard SM-2
                new_ef = self._calculate_ease_factor(quality)
                self.ease_factor = new_ef
                self.interval = self._fuzz(round(self.interval * self.ease_factor))

    def _calculate_ease_factor(self, quality: int) -> float:
        """Calculate new ease factor based on review quality."""
        new_ef = self.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        return max(SM2_MIN_EASE_FACTOR, min(new_ef, SM2_MAX_EASE_FACTOR))

    def _fuzz(self, interval: float) -> float:
        """Apply fuzz to interval to spread review load."""
        if interval <= 1:
            return interval
        fuzz = interval * INTERVAL_FUZZ_RANGE
        return max(1, interval + random.uniform(-fuzz, fuzz))

    def _check_leech(self) -> None:
        """Check if card should be flagged as leech."""
        if self.lapse_count >= LEECH_THRESHOLD:
            self.is_leech = True

    # --- Legacy compatibility methods ---

    def calculate_next_interval(self, quality: int) -> int:
        """Legacy: Calculate next review interval based on SM-2 algorithm."""
        if quality < SM2_QUALITY_THRESHOLD:
            return 1
        from .constants import SM2_INITIAL_INTERVALS

        if self.repetitions == 0:
            return SM2_INITIAL_INTERVALS.get(1, 1)
        if self.repetitions == 1:
            return SM2_INITIAL_INTERVALS.get(2, 6)
        return round(self.interval * self.ease_factor)

    def update_sm2(self, quality: int) -> None:
        """Update using Anki-grade SM-2 algorithm (quality: 0-5).

        This is the primary entry point, now delegates to process_review().
        """
        self.process_review(quality)

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """Ensure a datetime is UTC-aware.

        MongoDB strips timezone info from stored datetimes, returning naive
        datetimes on retrieval. This method re-attaches UTC to naive datetimes
        so they can be safely compared with timezone-aware datetimes.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    def is_due_for_review(self, reference_date: datetime | None = None) -> bool:
        """Check if item is due for review."""
        if reference_date is None:
            reference_date = datetime.now(UTC)
        return self._ensure_utc(self.next_review_date) <= reference_date

    def get_overdue_days(self, reference_date: datetime | None = None) -> int:
        """Get number of days overdue (negative if not due yet)."""
        if reference_date is None:
            reference_date = datetime.now(UTC)
        delta = reference_date - self._ensure_utc(self.next_review_date)
        return delta.days

    def get_retention_rate(self) -> float:
        """Calculate retention rate based on review history."""
        if self.repetitions == 0:
            return 0.0
        total_reviews = self.repetitions + self.lapse_count
        if total_reviews == 0:
            return 0.0
        return self.repetitions / total_reviews

    def get_predicted_intervals(self) -> dict[int, float]:
        """Get predicted next intervals for each quality score.

        Returns a dict mapping quality (0-5) to predicted interval in days.
        Used by frontend to show "next interval" on each button.
        """
        predictions: dict[int, float] = {}
        for q in range(6):
            # Clone state to simulate
            clone = self.model_copy(deep=True)
            clone.process_review(q)
            predictions[q] = clone.interval
        return predictions
