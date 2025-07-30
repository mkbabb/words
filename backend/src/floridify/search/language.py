"""
Language-specific search using LexiconLanguageLoader.

Provides high-level interface for searching language lexicons.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..constants import Language
from ..utils.logging import get_logger
from .core import SearchEngine, SearchResult
from .lexicon.core import SimpleLexicon
from .lexicon.language_loader import LexiconLanguageLoader

logger = get_logger(__name__)


class LanguageSearch:
    """
    High-level search interface for language lexicons.

    Handles lexicon loading and provides search functionality.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        languages: list[Language] | None = None,
        min_score: float = 0.6,
        force_rebuild: bool = False,
    ) -> None:
        """Initialize language search with configuration."""
        self.cache_dir = cache_dir or Path("data/search")
        self.languages = languages or [Language.ENGLISH]
        self.min_score = min_score
        self.force_rebuild = force_rebuild

        self.lexicon_loader: LexiconLanguageLoader | None = None
        self.search_engine: SearchEngine | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize lexicon loading and search engine."""
        if self._initialized:
            return

        logger.info("Initializing language search")

        # Load lexicons
        self.lexicon_loader = LexiconLanguageLoader(
            self.cache_dir, force_rebuild=self.force_rebuild
        )
        await self.lexicon_loader.load_languages(self.languages)

        # Create lexicon adapter
        words = self.lexicon_loader.get_all_words()
        phrases = self.lexicon_loader.get_all_phrases()
        lexicon = SimpleLexicon(words=words, phrases=phrases, languages=self.languages)

        # Initialize search engine
        self.search_engine = SearchEngine(lexicon, self.min_score)

        self._initialized = True
        logger.info(f"Language search initialized for {self.languages}")

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Search the loaded language lexicons."""
        if not self._initialized:
            await self.initialize()

        assert self.search_engine is not None
        return await self.search_engine.search(query, max_results, min_score)

    async def find_best_match(self, word: str) -> SearchResult | None:
        """Find best matching word for word resolution."""
        if not self._initialized:
            await self.initialize()

        assert self.search_engine is not None
        return await self.search_engine.find_best_match(word)

    def get_stats(self) -> dict[str, Any]:
        """Get search statistics."""
        if not self._initialized or not self.search_engine:
            return {"status": "not_initialized"}

        stats = self.search_engine.get_stats()
        stats.update(
            {
                "languages": [lang.value for lang in self.languages],
                "cache_dir": str(self.cache_dir),
            }
        )
        return stats


# Global singleton for backward compatibility
_language_search: LanguageSearch | None = None


async def get_language_search(
    languages: list[Language] | None = None,
    force_rebuild: bool = False,
) -> LanguageSearch:
    """Get or create global language search instance.

    Args:
        languages: Languages to support (defaults to English)
        force_rebuild: Force rebuild of search indices and re-download lexicons

    Returns:
        Initialized LanguageSearch instance
    """
    global _language_search

    # Create or recreate if languages changed or force rebuild requested
    target_languages = languages or [Language.ENGLISH]
    if _language_search is None or _language_search.languages != target_languages or force_rebuild:
        _language_search = LanguageSearch(languages=target_languages, force_rebuild=force_rebuild)
        await _language_search.initialize()

    return _language_search
