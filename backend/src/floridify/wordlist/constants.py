"""Constants and enums for wordlist functionality."""

from enum import Enum


class MasteryLevel(str, Enum):
    """Learning mastery level."""

    DEFAULT = "default"  # Not yet studied
    BRONZE = "bronze"   # Learning phase
    SILVER = "silver"   # Familiar phase
    GOLD = "gold"       # Mastered phase


class Temperature(str, Enum):
    """Learning temperature state."""

    HOT = "hot"    # Recently studied, fresh in memory
    COLD = "cold"  # Not studied recently, needs review


# Spaced repetition constants
SM2_MIN_EASE_FACTOR = 1.3
SM2_DEFAULT_EASE_FACTOR = 2.5
SM2_INITIAL_INTERVALS = {
    1: 1,   # First review after 1 day
    2: 6,   # Second review after 6 days
}
SM2_QUALITY_THRESHOLD = 3  # Quality scores below this reset repetitions