"""Language-specific search engine implementation.

Provides a wrapper around the core Search class with language-specific corpus management.
"""

from __future__ import annotations

from typing import Any

from ..caching.models import VersionConfig
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

    def get_stats(self) -> dict[str, Any]:
        """Get search engine statistics."""
        return self.search_engine.get_stats()

    @property
    def _initialized(self) -> bool:
        """Check if search engine is initialized."""
        return self.search_engine._initialized

    def is_semantic_ready(self) -> bool:
        """Check if semantic search is ready."""
        return self.search_engine._semantic_ready

    def is_semantic_building(self) -> bool:
        """Check if semantic search is currently building."""
        return (
            self.search_engine._semantic_init_task is not None
            and not self.search_engine._semantic_init_task.done()
        )

    async def await_semantic_ready(self) -> None:
        """Wait for semantic search to be ready."""
        await self.search_engine.await_semantic_ready()


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

    # Ensure storage is initialized before accessing database
    from floridify.storage.mongodb import get_storage

    await get_storage()

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
    language = languages[0] if languages else Language.ENGLISH

    try:
        # Create version config with force_rebuild flag
        config = VersionConfig(force_rebuild=force_rebuild)

        # First, try to get existing corpus
        from ..corpus.language.core import LanguageCorpus
        corpus = await Corpus.get(corpus_name=corpus_name, config=config)

        # If not found or forcing rebuild, create a new LanguageCorpus with sources
        if not corpus or force_rebuild:
            logger.info(f"Creating new language corpus '{corpus_name}' with sources for {language.value}")
            corpus = await LanguageCorpus.create_from_language(
                corpus_name=corpus_name,
                language=language,
                semantic=semantic,
                model_name="all-MiniLM-L6-v2",  # Default semantic model
            )

        if not corpus:
            raise ValueError(f"Failed to get or create corpus '{corpus_name}'")

        # Create search engine from corpus
        # When force_rebuild=True, we can't use from_corpus because it will skip loading
        # Instead, manually create the index and search engine with the corpus object we have
        from floridify.search.models import SearchIndex

        index_config = VersionConfig(force_rebuild=force_rebuild)
        index = await SearchIndex.get_or_create(
            corpus=corpus,
            semantic=semantic,
            config=index_config,
        )
        search_engine = Search(index=index, corpus=corpus)

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
