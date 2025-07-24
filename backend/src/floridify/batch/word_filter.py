"""Word filtering with normalization support for batch synthesis processing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import nltk  # type: ignore[import-not-found]
from nltk.corpus import stopwords  # type: ignore[import-not-found]

from .word_normalizer import WordNormalizer

# Download required NLTK data
nltk.download("stopwords", quiet=True)
nltk.download("averaged_perceptron_tagger", quiet=True)
nltk.download("averaged_perceptron_tagger_eng", quiet=True)
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# Compile regex patterns once for performance
NUMERIC_PATTERN = re.compile(r"^\d+(?:st|nd|rd|th|s)?$")
REPEAT_PATTERN = re.compile(r"^(.{1,2})\1{2,}$")  # aaa, abab, etc

# Internet slang and abbreviations to filter
SLANG_WORDS = {
    "lol",
    "lmao",
    "rofl",
    "omg",
    "wtf",
    "btw",
    "fyi",
    "asap",
    "aka",
    "imo",
    "imho",
    "tbh",
    "tbd",
    "tba",
    "eta",
    "faq",
    "diy",
    "pov",
    "smh",
    "idk",
    "irl",
    "afaik",
    "afk",
    "brb",
    "dm",
    "pm",
    "np",
}


class FilterMethod(Enum):
    """Filter method presets."""

    MINIMAL = "minimal"  # Almost no filtering
    STANDARD = "standard"  # Balanced filtering
    AGGRESSIVE = "aggressive"  # Heavy filtering + normalization


@dataclass
class FilterStats:
    """Filtering and normalization statistics."""

    total: int = 0
    remaining: int = 0
    filtered: int = 0
    normalized: int = 0
    unique_roots: int = 0
    compression_ratio: float = 0.0


class WordFilter:
    """Word filter with normalization support for batch processing."""

    def __init__(
        self,
        min_length: int = 3,
        max_length: int = 32,
        filter_stopwords: bool = True,
        filter_slang: bool = True,
        normalize: bool = False,
        normalization_method: str = "nltk",
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.filter_stopwords = filter_stopwords
        self.filter_slang = filter_slang
        self.normalize = normalize

        # Initialize NLTK stopwords if needed
        self.stop_words = set(stopwords.words("english")) if filter_stopwords else set()

        # Initialize normalizer if needed
        self.normalizer = (
            WordNormalizer(method=normalization_method, min_word_length=min_length)
            if normalize
            else None
        )

    def is_valid_word(self, word: str) -> bool:
        """Validate word using filtering rules."""
        if not word or not word.isalpha():
            return False

        # Length check
        word_len = len(word)
        if word_len < self.min_length or word_len > self.max_length:
            return False

        word_lower = word.lower()

        # Stop words
        if self.filter_stopwords and word_lower in self.stop_words:
            return False

        # Numeric patterns
        if NUMERIC_PATTERN.match(word_lower):
            return False

        # Internet slang
        if self.filter_slang and word_lower in SLANG_WORDS:
            return False

        # Repetitive patterns
        if REPEAT_PATTERN.match(word_lower):
            return False

        return True

    def filter_words(self, words: list[str]) -> tuple[list[str], FilterStats]:
        """Filter and optionally normalize words."""
        stats = FilterStats(total=len(words))

        # First pass: basic filtering
        valid_words = [word for word in words if self.is_valid_word(word)]

        # Normalize if enabled
        if self.normalize and self.normalizer:
            normalized_set = set()
            word_mappings = {}

            for word in valid_words:
                normalized, norm_type = self.normalizer.normalize_word(word)

                # Track normalization
                if normalized != word and norm_type != "unchanged":
                    stats.normalized += 1

                # Keep unique normalized forms
                if normalized not in normalized_set:
                    normalized_set.add(normalized)
                    word_mappings[normalized] = word  # Keep one original form

            # Use normalized unique words
            unique_words = list(word_mappings.values())
            stats.unique_roots = len(normalized_set)
        else:
            # Just remove case-insensitive duplicates
            seen = set()
            unique_words = []
            for word in valid_words:
                word_lower = word.lower()
                if word_lower not in seen:
                    seen.add(word_lower)
                    unique_words.append(word)

        stats.remaining = len(unique_words)
        stats.filtered = stats.total - stats.remaining
        stats.compression_ratio = (stats.filtered / stats.total * 100) if stats.total > 0 else 0.0

        return unique_words, stats

    def get_summary(self, stats: FilterStats) -> str:
        """Get filtering summary."""
        retention = (stats.remaining / stats.total * 100) if stats.total > 0 else 0

        summary = f"""Filter Results:
Total: {stats.total:,} → Remaining: {stats.remaining:,} ({retention:.1f}%)
Filtered: {stats.filtered:,} words ({stats.compression_ratio:.1f}% reduction)"""

        if self.normalize and stats.normalized > 0:
            summary += (
                f"\nNormalized: {stats.normalized:,} words to {stats.unique_roots:,} unique roots"
            )

        return summary


class FilterPresets:
    """Filter preset configurations - simplified to be more distinct."""

    @staticmethod
    def minimal() -> WordFilter:
        """Minimal filtering - only remove truly invalid words."""
        return WordFilter(
            min_length=1,
            max_length=32,
            filter_stopwords=False,  # Keep stopwords
            filter_slang=False,  # Keep slang
            normalize=False,  # No normalization
        )

    @staticmethod
    def standard() -> WordFilter:
        """Standard filtering - balanced approach."""
        return WordFilter(
            min_length=3,
            max_length=32,
            filter_stopwords=True,  # Remove stopwords
            filter_slang=True,  # Remove slang
            normalize=False,  # No normalization for speed
        )

    @staticmethod
    def aggressive() -> WordFilter:
        """Aggressive filtering with normalization."""
        return WordFilter(
            min_length=4,
            max_length=24,
            filter_stopwords=True,  # Remove stopwords
            filter_slang=True,  # Remove slang
            normalize=True,  # Enable normalization
            normalization_method="nltk",
        )

    @classmethod
    def from_method(cls, method: FilterMethod) -> WordFilter:
        """Create filter from enum method."""
        method_map = {
            FilterMethod.MINIMAL: cls.minimal,
            FilterMethod.STANDARD: cls.standard,
            FilterMethod.AGGRESSIVE: cls.aggressive,
        }
        return method_map[method]()
