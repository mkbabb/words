"""
Simple Lexicon object replacing Vocabulary with minimal overhead.

Performance-optimized for 100k-1M word searches.
"""

from __future__ import annotations

from typing import Protocol

from ...constants import Language


class Lexicon(Protocol):
    """Simple vocabulary interface optimized for search performance."""

    def get_all_words(self) -> list[str]:
        """Return all words as strings."""
        ...

    def get_all_phrases(self) -> list[str]:
        """Return all phrases as strings."""
        ...


class SimpleLexicon:
    """High-performance in-memory lexicon implementation."""

    def __init__(
        self,
        words: list[str],
        phrases: list[str] | None = None,
        languages: list[Language] = [Language.ENGLISH],
    ) -> None:
        """Initialize with pre-normalized word and phrase lists."""
        self._words = words  # Assume already normalized
        self._phrases = phrases or []
        self.languages = languages

    def get_all_words(self) -> list[str]:
        """Return all words (zero-copy)."""
        return self._words

    def get_all_phrases(self) -> list[str]:
        """Return all phrases (zero-copy)."""
        return self._phrases

    def get_vocabulary_size(self) -> dict[str, int]:
        """Get vocabulary statistics."""
        return {
            "words": len(self._words),
            "phrases": len(self._phrases),
            "total": len(self._words) + len(self._phrases),
        }
