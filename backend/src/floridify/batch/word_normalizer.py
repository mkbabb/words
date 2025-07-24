"""Advanced word normalization for reducing corpus size and mapping variants to roots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from ..text import TextProcessor, basic_lemmatize, lemmatize_word
from ..utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


@dataclass
class NormalizationStats:
    """Statistics from word normalization process."""

    total_words: int = 0
    normalized_words: int = 0
    unique_roots: int = 0
    compression_ratio: float = 0.0

    # Breakdown by type
    plurals_normalized: int = 0
    verb_forms_normalized: int = 0
    adjective_forms_normalized: int = 0
    other_forms_normalized: int = 0


class WordNormalizer:
    """Advanced word normalizer using stemming and lemmatization to reduce corpus size."""

    def __init__(
        self,
        method: str = "auto",  # "auto", "advanced", or "basic"
        language: str = "en",
        cache_file: Path | None = None,
        min_word_length: int = 3,
    ):
        self.method = method
        self.language = language
        self.min_word_length = min_word_length
        self.cache_file = cache_file

        # Word mappings cache (normalized -> original_forms)
        self.word_mappings: dict[str, set[str]] = {}
        # Reverse mapping (original -> normalized)
        self.reverse_mappings: dict[str, str] = {}

        # Initialize text processor
        self.text_processor = TextProcessor()

        # Load cache if exists
        self._load_cache()

        logger.info(f"WordNormalizer initialized with method: {method}")


    def _load_cache(self) -> None:
        """Load cached word mappings from file."""
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert sets back from lists
                    self.word_mappings = {
                        normalized: set(variants)
                        for normalized, variants in data.get("mappings", {}).items()
                    }
                    self.reverse_mappings = data.get("reverse_mappings", {})
                console.print(f"[blue]Loaded {len(self.word_mappings)} cached word mappings[/blue]")
            except Exception as e:
                console.print(f"[yellow]Could not load cache: {e}[/yellow]")

    def _save_cache(self) -> None:
        """Save word mappings to cache file."""
        if not self.cache_file:
            return

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                # Convert sets to lists for JSON serialization
                data = {
                    "mappings": {
                        normalized: list(variants)
                        for normalized, variants in self.word_mappings.items()
                    },
                    "reverse_mappings": self.reverse_mappings,
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.print(f"[blue]Saved {len(self.word_mappings)} word mappings to cache[/blue]")
        except Exception as e:
            console.print(f"[yellow]Could not save cache: {e}[/yellow]")


    def _normalize_word_internal(self, word: str) -> tuple[str, str]:
        """
        Internal word normalization using best available method.
        
        Returns:
            Tuple of (normalized_word, normalization_type)
        """
        word = word.lower().strip()
        
        # Skip if too short
        if len(word) < self.min_word_length:
            return word, "unchanged"
        
        if self.method == "basic":
            # Use basic rule-based lemmatization
            normalized = basic_lemmatize(word)
            return normalized, "basic" if normalized != word else "unchanged"
        
        # Use advanced text processing for lemmatization
        normalized = lemmatize_word(word)
        
        if normalized != word:
            # Simple heuristic to determine normalization type
            if word.endswith(('s', 'es', 'ies')):
                return normalized, "plural"
            elif word.endswith(('ing', 'ed')):
                return normalized, "verb_form"
            elif word.endswith(('er', 'est', 'ly')):
                return normalized, "adjective_form"
            else:
                return normalized, "other_form"
        
        return word, "unchanged"

    def normalize_word(self, word: str) -> tuple[str, str]:
        """
        Normalize a single word to its root form.

        Returns:
            Tuple of (normalized_word, normalization_type)
        """
        # Check cache first
        if word in self.reverse_mappings:
            return self.reverse_mappings[word], "cached"

        # Clean the word
        cleaned_word = re.sub(r"[^a-zA-Z]", "", word.lower())
        if len(cleaned_word) < self.min_word_length:
            return word, "unchanged"

        # Apply normalization using abstracted method
        normalized, norm_type = self._normalize_word_internal(cleaned_word)

        # Update mappings
        if normalized != word:
            if normalized not in self.word_mappings:
                self.word_mappings[normalized] = set()
            self.word_mappings[normalized].add(word)
            self.reverse_mappings[word] = normalized

        return normalized, norm_type

    def normalize_word_list(
        self, words: list[str]
    ) -> tuple[list[str], dict[str, set[str]], NormalizationStats]:
        """
        Normalize a list of words and return unique roots with mappings.

        Returns:
            Tuple of (normalized_words, word_mappings, statistics)
        """
        console.print(f"[blue]Normalizing {len(words)} words using {self.method} method...[/blue]")

        stats = NormalizationStats()
        stats.total_words = len(words)

        normalized_words = []
        normalization_counts = {
            "plural": 0,
            "verb_form": 0,
            "adjective_form": 0,
            "other_form": 0,
            "stem": 0,
            "basic": 0,
        }

        for word in words:
            normalized, norm_type = self.normalize_word(word)
            normalized_words.append(normalized)

            if norm_type in normalization_counts:
                normalization_counts[norm_type] += 1

            if normalized != word:
                stats.normalized_words += 1

        # Calculate statistics
        stats.plurals_normalized = normalization_counts["plural"]
        stats.verb_forms_normalized = normalization_counts["verb_form"]
        stats.adjective_forms_normalized = normalization_counts["adjective_form"]
        stats.other_forms_normalized = (
            normalization_counts["other_form"]
            + normalization_counts["stem"]
            + normalization_counts["basic"]
        )

        # Get unique normalized words
        unique_normalized = list(set(normalized_words))
        stats.unique_roots = len(unique_normalized)
        stats.compression_ratio = (stats.total_words - stats.unique_roots) / stats.total_words * 100

        # Save cache
        self._save_cache()

        return unique_normalized, self.word_mappings, stats

    def get_variants(self, normalized_word: str) -> set[str]:
        """Get all original word variants for a normalized word."""
        return self.word_mappings.get(normalized_word, {normalized_word})

    def get_normalization_summary(self, stats: NormalizationStats) -> str:
        """Generate a summary of normalization results."""
        return f"""Word Normalization Summary ({self.method} method):
Total words: {stats.total_words:,}
Normalized words: {stats.normalized_words:,} ({stats.normalized_words / stats.total_words * 100:.1f}%)
Unique roots: {stats.unique_roots:,}
Compression ratio: {stats.compression_ratio:.1f}%

Normalization breakdown:
  Plurals: {stats.plurals_normalized:,}
  Verb forms: {stats.verb_forms_normalized:,}
  Adjective forms: {stats.adjective_forms_normalized:,}
  Other forms: {stats.other_forms_normalized:,}

Space reduction: {stats.total_words - stats.unique_roots:,} words removed
"""


# Predefined normalizer configurations
class NormalizerPresets:
    """Predefined normalizer configurations for different use cases."""

    @staticmethod
    def conservative() -> WordNormalizer:
        """Conservative normalization - prefer accuracy over compression."""
        return WordNormalizer(
            method="advanced",
            cache_file=Path("./cache/word_normalizer_conservative.json"),
            min_word_length=2,
        )

    @staticmethod
    def aggressive() -> WordNormalizer:
        """Aggressive normalization - maximize compression."""
        return WordNormalizer(
            method="auto",
            cache_file=Path("./cache/word_normalizer_aggressive.json"),
            min_word_length=3,
        )

    @staticmethod
    def fast() -> WordNormalizer:
        """Fast normalization - basic rules for speed."""
        return WordNormalizer(
            method="basic", 
            cache_file=Path("./cache/word_normalizer_fast.json"), 
            min_word_length=3
        )

    @staticmethod
    def balanced() -> WordNormalizer:
        """Balanced normalization - good accuracy and compression."""
        return WordNormalizer(
            method="auto",
            cache_file=Path("./cache/word_normalizer_balanced.json"),
            min_word_length=3,
        )
