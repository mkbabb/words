"""Constants and enums for wordlist functionality."""

from __future__ import annotations

from enum import Enum

# Numeric ordering for MasteryLevel comparison
_MASTERY_ORDER: dict[str, int] = {"default": 0, "bronze": 1, "silver": 2, "gold": 3}


class MasteryLevel(str, Enum):
    """Learning mastery level with correct ordering."""

    DEFAULT = "default"  # Not yet studied
    BRONZE = "bronze"  # Learning phase
    SILVER = "silver"  # Familiar phase
    GOLD = "gold"  # Mastered phase

    @property
    def order(self) -> int:
        return _MASTERY_ORDER[self.value]

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, MasteryLevel):
            return NotImplemented
        return self.order > other.order

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, MasteryLevel):
            return NotImplemented
        return self.order >= other.order

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, MasteryLevel):
            return NotImplemented
        return self.order < other.order

    def __le__(self, other: object) -> bool:
        if not isinstance(other, MasteryLevel):
            return NotImplemented
        return self.order <= other.order


class CardState(str, Enum):
    """Card state for Anki-grade spaced repetition."""

    NEW = "new"  # Never reviewed
    LEARNING = "learning"  # In initial learning steps (sub-day intervals)
    YOUNG = "young"  # Graduated, interval < 21 days
    MATURE = "mature"  # Interval >= 21 days
    RELEARNING = "relearning"  # Failed after graduating, back in steps


class Temperature(str, Enum):
    """Learning temperature state."""

    HOT = "hot"  # Recently studied, fresh in memory
    COLD = "cold"  # Not studied recently, needs review


# Spaced repetition constants (basic SM-2)
SM2_MIN_EASE_FACTOR = 1.3
SM2_DEFAULT_EASE_FACTOR = 2.5
SM2_INITIAL_INTERVALS = {
    1: 1,  # First review after 1 day
    2: 6,  # Second review after 6 days
}
SM2_MAX_EASE_FACTOR = 4.0
SM2_QUALITY_THRESHOLD = 3  # Quality scores below this reset repetitions

# Anki-grade constants
LEARNING_STEPS_MINUTES: list[int] = [1, 10]  # Initial learning: 1min, 10min
RELEARNING_STEPS_MINUTES: list[int] = [10]  # After lapse: 10min
GRADUATING_INTERVAL_DAYS = 1  # First interval after graduating learning
EASY_INTERVAL_DAYS = 4  # Interval when pressing "Easy" during learning
MAX_INTERVAL_DAYS = 36500  # ~100 years cap
LEECH_THRESHOLD = 8  # Lapses before marking as leech
EASY_BONUS = 1.3  # Multiplier for "Easy" answers
HARD_INTERVAL_MULTIPLIER = 1.2  # Multiplier for "Hard" answers
INTERVAL_FUZZ_RANGE = 0.05  # ±5% fuzz to spread review load
MATURE_INTERVAL_DAYS = 21  # Interval threshold for YOUNG -> MATURE

# Temperature cooling
COOLING_THRESHOLD_HOURS = 24

# Review history cap
MAX_REVIEW_HISTORY = 50
