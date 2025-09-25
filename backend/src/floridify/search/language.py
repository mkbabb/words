"""Language-specific search engine implementation.

Provides a wrapper around the core Search class with language-specific corpus management.
"""

from __future__ import annotations

from ..corpus.core import Corpus
from ..models.base import Language
from ..utils.logging import get_logger
from .constants import SearchMode
from .core import Search
from .models import SearchResult

logger = get_logger(__name__)

# Global singleton cache for language search engines
_language_search_cache: dict[tuple[Language, ...], LanguageSearch] = {}


class LanguageSearch:
    """Language-specific search engine wrapper around core Search."""

    def __init__(
        self,
        languages: list[Language],
        search_engine: Search,
    ) -> None:
        """Initialize language search wrapper.

        Args:
            languages: List of supported languages
            search_engine: Core search engine instance

        """
        self.languages = languages
        self.search_engine = search_engine

    async def search_with_mode(
        self,
        query: str,
        mode: SearchMode,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Search with explicit mode selection."""
        return await self.search_engine.search_with_mode(
            query=query,
            mode=mode,
            max_results=max_results,
            min_score=min_score,
        )

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Smart cascading search."""
        return await self.search_engine.search(
            query=query,
            max_results=max_results,
            min_score=min_score,
        )

    async def find_best_match(self, word: str) -> SearchResult | None:
        """Find single best matching word."""
        return await self.search_engine.find_best_match(word)


async def get_language_search(
    languages: list[Language],
    force_rebuild: bool = False,
    semantic: bool = True,
) -> LanguageSearch:
    """Get or create a language-specific search engine.

    Args:
        languages: List of languages to support
        force_rebuild: Force rebuild of search indices
        semantic: Enable semantic search

    Returns:
        LanguageSearch instance

    """
    global _language_search_cache

    # Create cache key
    cache_key = tuple(sorted(languages, key=lambda x: x.value))

    # Check cache unless force rebuild
    if not force_rebuild and cache_key in _language_search_cache:
        logger.debug(f"Using cached language search for {[lang.value for lang in languages]}")
        return _language_search_cache[cache_key]

    logger.info(f"Creating language search for {[lang.value for lang in languages]}")

    # Get or create corpus for these languages
    corpus_names = []
    for language in languages:
        if language == Language.ENGLISH:
            corpus_names.append("language_english")
        elif language == Language.SPANISH:
            corpus_names.append("language_spanish")
        elif language == Language.FRENCH:
            corpus_names.append("language_french")
        # Add more languages as needed
        else:
            # Default to english for unsupported languages
            corpus_names.append("language_english")

    # For now, use the first corpus (typically English)
    corpus_name = corpus_names[0]

    try:
        # Get or create the corpus
        corpus = await Corpus.get_or_create(
            corpus_name=corpus_name,
            language=languages[0] if languages else Language.ENGLISH,
        )
        if not corpus:
            raise ValueError(f"Failed to get or create corpus '{corpus_name}'")

        # Create search engine from corpus
        search_engine = await Search.from_corpus(
            corpus_name=corpus_name,
            semantic=semantic,
        )

        # Create language search wrapper
        language_search = LanguageSearch(
            languages=languages,
            search_engine=search_engine,
        )

        # Cache the result
        _language_search_cache[cache_key] = language_search

        logger.info(f"✅ Language search initialized for {[lang.value for lang in languages]}")
        return language_search

    except Exception as e:
        logger.error(f"Failed to create language search: {e}")
        raise


async def reset_language_search() -> None:
    """Reset the language search cache."""
    global _language_search_cache
    _language_search_cache.clear()
    logger.info("Language search cache reset")


__all__ = ["LanguageSearch", "get_language_search", "reset_language_search"]
