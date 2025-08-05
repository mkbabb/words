"""
Language-specific search using LexiconLanguageLoader.

Provides high-level interface for searching language lexicons.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.corpus_manager import CorpusManager
from ..models.definition import Language
from ..search.utils import generate_corpus_id, get_corpus_name
from ..utils.logging import get_logger
from .core import SearchEngine, SearchResult

logger = get_logger(__name__)


class LanguageSearch:
    """
    High-level search interface for language lexicons.

    Handles lexicon loading and provides search functionality.
    """

    def __init__(
        self,
        languages: list[Language] | None = None,
        min_score: float = 0.6,
        force_rebuild: bool = False,
        semantic: bool = False,
    ) -> None:
        """Initialize language search with configuration.

        Args:
            languages: Languages to support
            min_score: Minimum score threshold
            force_rebuild: Force rebuild of indices
            semantic: Enable semantic search capabilities
        """
        self.languages = sorted(languages or [Language.ENGLISH])  # Sort for deterministic ID
        self.min_score = min_score
        self.force_rebuild = force_rebuild
        self.semantic = semantic

        self.search_engine: SearchEngine | None = None
        self._corpus_manager: CorpusManager | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize lexicon loading and search engine with unified corpus management."""
        if self._initialized:
            return

        logger.info(
            f"Initializing language search (semantic={'enabled' if self.semantic else 'disabled'})"
        )

        # Import at runtime to avoid circular imports
        from ..core.corpus_manager import CorpusType, get_corpus_manager, get_corpus_entry
        
        # Initialize corpus manager
        self._corpus_manager = await get_corpus_manager()

        # Generate deterministic corpus ID and name
        corpus_id = generate_corpus_id(CorpusType.LANGUAGE_SEARCH, self.languages)
        corpus_name = get_corpus_name(CorpusType.LANGUAGE_SEARCH, corpus_id)
        
        # Create corpus through manager - it will handle loading from sources
        await self._corpus_manager.create_corpus(
            corpus_type=CorpusType.LANGUAGE_SEARCH,
            corpus_id=corpus_id,
            words=[],  # Empty - corpus manager will load from sources
            phrases=[],  # Empty - corpus manager will load from sources
            semantic=self.semantic,
            force_rebuild=self.force_rebuild,
        )
        
        # Get the loaded corpus data - use the display name format
        # Corpus manager uses display names like "Language Search (en)"
        display_corpus_name = f"Language Search ({corpus_id})"
        corpus_entry = await get_corpus_entry(display_corpus_name)
        
        if not corpus_entry:
            raise RuntimeError(f"Failed to load corpus {display_corpus_name}")
        
        # Initialize search engine with corpus data
        self.search_engine = SearchEngine(
            words=corpus_entry["words"],
            phrases=corpus_entry["phrases"],
            min_score=self.min_score,
            semantic=self.semantic,
            corpus_name=corpus_name,
        )

        # Initialize semantic indices if enabled
        if self.semantic and self.search_engine.semantic_search:
            await self.search_engine.initialize_semantic()

        self._initialized = True
        logger.info(f"Language search initialized for {self.languages} with unified corpus management")

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        semantic: bool | None = None,
    ) -> list[SearchResult]:
        """Search the loaded language lexicons.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            semantic: Override semantic search setting
        """
        if not self._initialized:
            await self.initialize()

        assert self.search_engine is not None
        return await self.search_engine.search(query, max_results, min_score, semantic)

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
                "corpus_name": self.search_engine.corpus_name if self.search_engine else None,
            }
        )
        return stats


# Global singleton for backward compatibility
_language_search: LanguageSearch | None = None


async def get_language_search(
    languages: list[Language] | None = None,
    force_rebuild: bool = False,
    semantic: bool = False,
) -> LanguageSearch:
    """Get or create global language search instance.

    Args:
        languages: Languages to support (defaults to English)
        force_rebuild: Force rebuild of search indices and re-download lexicons
        semantic: Enable semantic search capabilities

    Returns:
        Initialized LanguageSearch instance
    """
    global _language_search

    # Create or recreate if languages changed or force rebuild requested
    target_languages = languages or [Language.ENGLISH]
    needs_recreate = (
        _language_search is None
        or _language_search.languages != target_languages
        or force_rebuild
    )

    if needs_recreate:
        # Always create with semantic support enabled
        _language_search = LanguageSearch(
            languages=target_languages, force_rebuild=force_rebuild, semantic=True
        )
        await _language_search.initialize()

    assert _language_search is not None  # Logic ensures this is never None
    return _language_search
