"""Language-specific search using LexiconLanguageLoader.

Provides high-level interface for searching language lexicons.
"""

from __future__ import annotations

from typing import Any

from ..corpus.core import Corpus
from ..corpus.loaders.language import CorpusLanguageLoader
from ..corpus.manager import CorpusManager, get_corpus_manager
from ..models.dictionary import Language
from ..utils.logging import get_logger
from .constants import DEFAULT_MIN_SCORE, SearchMode
from .core import SearchEngine, SearchResult
from .semantic.constants import DEFAULT_SENTENCE_MODEL, SemanticModel

logger = get_logger(__name__)


class LanguageSearch:
    """High-level search interface for language lexicons.

    Handles lexicon loading and provides search functionality.
    """

    def __init__(
        self,
        languages: list[Language] | None = None,
        min_score: float = DEFAULT_MIN_SCORE,
        force_rebuild: bool = False,
        semantic: bool = True,
        semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
    ) -> None:
        """Initialize language search with configuration.

        Args:
            languages: Languages to support
            min_score: Minimum score threshold
            force_rebuild: Force rebuild of indices
            semantic: Enable semantic search capabilities
            semantic_model: Model for semantic search (BGE-M3 or MiniLM)

        """
        self.languages = sorted(
            languages or [Language.ENGLISH],
            key=lambda x: x.value,
        )  # Sort for deterministic ID
        self.min_score = min_score
        self.force_rebuild = force_rebuild
        self.semantic = semantic
        self.semantic_model = semantic_model

        self.search_engine: SearchEngine | None = None
        self._corpus_manager: CorpusManager = get_corpus_manager()
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize lexicon loading and search engine with unified corpus management."""
        if self.search_engine is not None:
            logger.debug("Language search already initialized, skipping")
            return

        logger.info(
            f"Initializing language search for {[lang.value for lang in self.languages]} (semantic={'enabled' if self.semantic else 'disabled'})",
        )

        # Load vocabulary and create corpus using unified language loader
        logger.debug(f"Creating language loader (force_rebuild={self.force_rebuild})")
        loader = CorpusLanguageLoader(force_rebuild=self.force_rebuild)

        # Get or create corpus (handles vocabulary loading, normalization, and corpus creation)
        corpus = await loader.get_or_create_corpus_for_languages(
            languages=self.languages,
            force_rebuild=self.force_rebuild,
        )

        logger.info(
            f"Corpus ready: '{corpus.corpus_name}' (full hash: {corpus.vocabulary_hash}, {len(corpus.vocabulary)} items)",
        )

        # Initialize search engine with corpus name
        logger.info(
            f"Creating SearchEngine for corpus '{corpus.corpus_name}' with {self.semantic_model if self.semantic else 'no semantic'}"
        )
        self.search_engine = SearchEngine(
            corpus_name=corpus.corpus_name,
            min_score=self.min_score,
            semantic=self.semantic,
            semantic_model=self.semantic_model,
            force_rebuild=self.force_rebuild,
        )

        # Initialize search engine components
        logger.info("Initializing SearchEngine components")
        await self.search_engine.initialize()

        # Semantic search is initialized during SearchEngine.initialize() if enabled

        logger.info(
            f"✅ Language search fully initialized for {[lang.value for lang in self.languages]}",
        )
        self._initialized = True

    async def update_corpus(self, corpus: Corpus) -> None:
        """Update the language search with a new corpus.

        Args:
            corpus: New corpus to use

        """
        if self.search_engine is None:
            await self.initialize()

        if self.search_engine:
            await self.search_engine.update_corpus()

    def model_dump(self) -> dict[str, Any]:
        """Export language search state.

        Returns:
            Dictionary containing state

        """
        return {
            "languages": [lang.value for lang in self.languages],
            "min_score": self.min_score,
            "semantic": self.semantic,
            "semantic_model": self.semantic_model if self.semantic else None,
            "initialized": self._initialized,
        }

    def model_load(self, data: dict[str, Any]) -> None:
        """Load language search state.

        Args:
            data: Dictionary containing state

        """
        self.languages = [Language(lang) for lang in data.get("languages", ["en"])]
        self.min_score = data.get("min_score", DEFAULT_MIN_SCORE)
        self.semantic = data.get("semantic", True)
        self.semantic_model = data.get("semantic_model", DEFAULT_SENTENCE_MODEL)
        self._initialized = data.get("initialized", False)

    async def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Search the loaded language lexicons using SMART mode.

        Args:
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        if self.search_engine is None:
            await self.initialize()

        assert self.search_engine is not None
        return await self.search_engine.search(query, max_results, min_score)

    async def search_with_mode(
        self,
        query: str,
        mode: SearchMode,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Search the loaded language lexicons with explicit mode.

        Args:
            query: Search query
            mode: Search mode (SMART, EXACT, FUZZY, SEMANTIC)
            max_results: Maximum results to return
            min_score: Minimum score threshold

        """
        if self.search_engine is None:
            await self.initialize()

        assert self.search_engine is not None
        return await self.search_engine.search_with_mode(query, mode, max_results, min_score)

    async def find_best_match(self, word: str) -> SearchResult | None:
        """Find best matching word for word resolution."""
        if self.search_engine is None:
            await self.initialize()

        assert self.search_engine is not None
        return await self.search_engine.find_best_match(word)

    def get_stats(self) -> dict[str, Any]:
        """Get search statistics."""
        if self.search_engine is None:
            return {"status": "not_initialized"}

        stats = self.search_engine.get_stats()
        stats.update(
            {
                "languages": [lang.value for lang in self.languages],
                "corpus_name": self.search_engine.corpus_name if self.search_engine else None,
            },
        )
        return stats


# Global singleton for backward compatibility
_language_search: LanguageSearch | None = None


async def get_language_search(
    languages: list[Language] | None = None,
    force_rebuild: bool = False,
    semantic: bool = True,
    semantic_model: SemanticModel = DEFAULT_SENTENCE_MODEL,
) -> LanguageSearch:
    """Get or create global language search instance.

    Args:
        languages: Languages to support (defaults to English)
        force_rebuild: Force rebuild of search indices and re-download lexicons
        semantic: Enable semantic search capabilities
        semantic_model: Model for semantic search (BGE-M3 or MiniLM)

    Returns:
        Initialized LanguageSearch instance

    """
    global _language_search

    # Create or recreate if languages changed or force rebuild requested
    target_languages = languages or [Language.ENGLISH]
    needs_recreate = (
        _language_search is None or _language_search.languages != target_languages or force_rebuild
    )

    if needs_recreate:
        # Create with semantic support as specified
        _language_search = LanguageSearch(
            languages=target_languages,
            force_rebuild=force_rebuild,
            semantic=semantic,
            semantic_model=semantic_model,
        )
        await _language_search.initialize()

    assert _language_search is not None  # Logic ensures this is never None
    return _language_search
