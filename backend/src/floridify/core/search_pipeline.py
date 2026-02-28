"""Generalized search pipeline with hot-reload search engine for word resolution and discovery."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from ..models.base import Language
from ..search.constants import SearchMode
from ..search.core import SearchResult
from ..search.language import LanguageSearch, _semantic_search_enabled, get_language_search
from ..utils.logging import (
    get_logger,
    log_metrics,
    log_search_method,
    log_stage,
    log_timing,
)

logger = get_logger(__name__)


# ============================================================================
# HOT-RELOAD SEARCH ENGINE MANAGER
# ============================================================================


@dataclass
class _CorpusFingerprint:
    """Lightweight fingerprint for detecting corpus changes."""

    corpus_name: str
    vocabulary_hash: str | None
    version: str | None


class SearchEngineManager:
    """Manages the search engine singleton with periodic corpus change detection.

    Hot path cost: one time.monotonic() call (~10ns).
    The actual MongoDB metadata check happens at most once per check_interval seconds.
    """

    def __init__(self, check_interval: float = 30.0) -> None:
        self._engine: LanguageSearch | None = None
        self._fingerprint: _CorpusFingerprint | None = None
        self._last_check: float = 0.0
        self._check_interval: float = check_interval
        self._reload_lock: asyncio.Lock = asyncio.Lock()
        self._languages: list[Language] | None = None
        self._semantic: bool = _semantic_search_enabled()
        self._init_task: asyncio.Task[None] | None = None
        self._init_error: str | None = None
        self._initializing: bool = False

    async def get_engine(
        self,
        languages: list[Language] | None = None,
        force_rebuild: bool = False,
        semantic: bool | None = None,
    ) -> LanguageSearch:
        """Get the search engine, rebuilding if the corpus has changed.

        Fast path: engine exists, within check interval -> return immediately.
        Periodic check: query corpus metadata for vocabulary_hash (~1-2ms).
        If hash changed: hot-reload (clear caches, rebuild indices).
        """
        target_languages = languages or [Language.ENGLISH]
        effective_semantic = semantic if semantic is not None else self._semantic

        # Wait for background init if running
        if self._init_task and not self._init_task.done():
            await self._init_task

        # Force rebuild always triggers a full reload
        if force_rebuild:
            return await self._full_reload(target_languages, effective_semantic)

        # If background init failed, retry inline
        if self._engine is None and self._init_error:
            logger.info(f"Background init failed ({self._init_error}), retrying inline")
            return await self._full_reload(target_languages, effective_semantic)

        # Fast path: engine exists and we're within check interval
        if self._engine is not None and self._languages == target_languages:
            now = time.monotonic()
            if now - self._last_check < self._check_interval:
                return self._engine

            # Periodic check: has the corpus changed?
            self._last_check = now
            if not await self._corpus_changed():
                return self._engine

            # Corpus changed — hot reload
            logger.info("Corpus change detected — initiating hot reload")
            return await self._hot_reload(target_languages, effective_semantic)

        # No engine yet — initial load
        return await self._full_reload(target_languages, effective_semantic)

    async def start_background_init(
        self,
        languages: list[Language] | None = None,
        semantic: bool | None = None,
    ) -> None:
        """Start search engine initialization in background. Called from lifespan."""
        if self._init_task is not None:
            return
        self._initializing = True
        self._init_task = asyncio.create_task(
            self._background_init(
                languages or [Language.ENGLISH],
                semantic if semantic is not None else self._semantic,
            )
        )

    async def _background_init(self, languages: list[Language], semantic: bool) -> None:
        """Background task: build corpus + search engine."""
        try:
            logger.info(
                f"Background search init starting (languages={[l.value for l in languages]}, semantic={semantic})"
            )
            self._engine = await get_language_search(languages, semantic=semantic)
            self._languages = languages
            self._last_check = time.monotonic()
            self._fingerprint = await self._capture_fingerprint(languages)
            self._init_error = None
            logger.info("Background search init completed successfully")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"Background search init failed: {e}", exc_info=True)
        finally:
            self._initializing = False

    async def _corpus_changed(self) -> bool:
        """Lightweight check if the corpus metadata has changed.

        Queries Corpus.Metadata for vocabulary_hash of the current corpus.
        Cost: ~1-2ms (indexed query on resource_id + is_latest).
        """
        if self._fingerprint is None:
            return True

        try:
            from ..caching.models import BaseVersionedData

            collection = BaseVersionedData.get_pymongo_collection()

            # Query for the latest version of the corpus with matching name
            doc = await collection.find_one(
                {
                    "corpus_name": self._fingerprint.corpus_name,
                    "version_info.is_latest": True,
                },
                projection={
                    "vocabulary_hash": 1,
                    "version_info.version": 1,
                },
            )

            if doc is None:
                return True

            new_hash = doc.get("vocabulary_hash")
            new_version = doc.get("version_info", {}).get("version")

            if new_hash != self._fingerprint.vocabulary_hash:
                logger.info(
                    f"Vocabulary hash changed: {self._fingerprint.vocabulary_hash} -> {new_hash}"
                )
                return True

            if new_version != self._fingerprint.version:
                logger.info(f"Corpus version changed: {self._fingerprint.version} -> {new_version}")
                return True

            return False

        except Exception as e:
            logger.warning(f"Corpus change detection failed (assuming unchanged): {e}")
            return False

    async def _full_reload(self, languages: list[Language], semantic: bool) -> LanguageSearch:
        """Full engine load (initial or force rebuild)."""
        async with self._reload_lock:
            self._engine = await get_language_search(
                languages,
                force_rebuild=True,
                semantic=semantic,
            )
            self._languages = languages
            self._semantic = semantic
            self._last_check = time.monotonic()
            self._fingerprint = await self._capture_fingerprint(languages)
            return self._engine

    async def _hot_reload(self, languages: list[Language], semantic: bool) -> LanguageSearch:
        """Hot-reload the search engine after corpus change.

        Under lock: clear language_search_cache + search_instance_cache,
        build new engine, atomic swap. Old engine serves requests until swap.
        """
        async with self._reload_lock:
            # Double-check after acquiring lock (another coroutine may have reloaded)
            if not await self._corpus_changed():
                return self._engine  # type: ignore[return-value]

            logger.info("Hot-reloading search engine...")
            start = time.perf_counter()

            # Clear caches
            from ..search.language import reset_language_search

            await reset_language_search()

            # Build new engine
            new_engine = await get_language_search(
                languages,
                force_rebuild=True,
                semantic=semantic,
            )

            # Atomic swap
            self._engine = new_engine
            self._languages = languages
            self._semantic = semantic
            self._last_check = time.monotonic()
            self._fingerprint = await self._capture_fingerprint(languages)

            duration = time.perf_counter() - start
            logger.info(f"Hot-reload complete in {duration:.2f}s")
            return new_engine

    async def _capture_fingerprint(self, languages: list[Language]) -> _CorpusFingerprint | None:
        """Capture current corpus fingerprint for change detection."""
        try:
            # Determine corpus name from languages
            language = languages[0] if languages else Language.ENGLISH
            if language == Language.ENGLISH:
                corpus_name = "language_english"
            elif language == Language.SPANISH:
                corpus_name = "language_spanish"
            elif language == Language.FRENCH:
                corpus_name = "language_french"
            else:
                corpus_name = "language_english"

            from ..caching.models import BaseVersionedData

            collection = BaseVersionedData.get_pymongo_collection()
            doc = await collection.find_one(
                {
                    "corpus_name": corpus_name,
                    "version_info.is_latest": True,
                },
                projection={
                    "vocabulary_hash": 1,
                    "version_info.version": 1,
                },
            )

            if doc:
                return _CorpusFingerprint(
                    corpus_name=corpus_name,
                    vocabulary_hash=doc.get("vocabulary_hash"),
                    version=doc.get("version_info", {}).get("version"),
                )
            return _CorpusFingerprint(
                corpus_name=corpus_name,
                vocabulary_hash=None,
                version=None,
            )
        except Exception as e:
            logger.warning(f"Failed to capture corpus fingerprint: {e}")
            return None

    async def reset(self) -> None:
        """Reset the search engine (for testing/cleanup)."""
        async with self._reload_lock:
            self._engine = None
            self._fingerprint = None
            self._last_check = 0.0
            self._languages = None
            self._init_task = None
            self._init_error = None
            self._initializing = False
            logger.info("SearchEngineManager reset")

    def get_status(self) -> dict[str, Any]:
        """Get hot-reload status for the status endpoint."""
        now = time.monotonic()
        return {
            "engine_loaded": self._engine is not None,
            "initializing": self._initializing,
            "init_error": self._init_error,
            "semantic_enabled": self._semantic,
            "last_check_seconds_ago": round(now - self._last_check, 1)
            if self._last_check
            else None,
            "check_interval": self._check_interval,
            "corpus_fingerprint": {
                "corpus_name": self._fingerprint.corpus_name,
                "vocabulary_hash": self._fingerprint.vocabulary_hash,
                "version": self._fingerprint.version,
            }
            if self._fingerprint
            else None,
            "languages": [lang.value for lang in self._languages] if self._languages else None,
        }


# Global singleton manager
_search_engine_manager: SearchEngineManager | None = None


def get_search_engine_manager() -> SearchEngineManager:
    """Get the global SearchEngineManager singleton."""
    global _search_engine_manager
    if _search_engine_manager is None:
        _search_engine_manager = SearchEngineManager()
    return _search_engine_manager


# ============================================================================
# BACKWARD-COMPATIBLE WRAPPERS
# ============================================================================


async def get_search_engine(
    languages: list[Language] | None = None,
    force_rebuild: bool = False,
    semantic: bool | None = None,
) -> LanguageSearch:
    """Get or create the global LanguageSearch singleton.

    Backward-compatible wrapper around SearchEngineManager.

    Args:
        languages: Languages to support (defaults to English)
        force_rebuild: Force rebuild of search indices
        semantic: Enable semantic search (None = use SEMANTIC_SEARCH_ENABLED env var)

    Returns:
        Initialized LanguageSearch instance
    """
    return await get_search_engine_manager().get_engine(
        languages=languages,
        force_rebuild=force_rebuild,
        semantic=semantic,
    )


async def reset_search_engine() -> None:
    """Reset the search engine singleton (for testing/cleanup).

    Backward-compatible wrapper around SearchEngineManager.
    """
    await get_search_engine_manager().reset()


# ============================================================================
# SEARCH PIPELINE FUNCTIONS
# ============================================================================


@log_timing
@log_stage("Search Pipeline", "🔍")
async def search_word_pipeline(
    word: str,
    languages: list[Language] | None = None,
    mode: SearchMode = SearchMode.SMART,
    max_results: int = 20,
    min_score: float | None = None,
    force_rebuild: bool = False,
    corpus_id: any = None,
    corpus_name: str | None = None,
) -> list[SearchResult]:
    """Generalized word search pipeline - isomorphic with backend API.

    This pipeline can be used by any component that needs to search for words,
    including lookup, synonyms, suggestions, and other features.

    Args:
        word: Word to search for
        languages: Languages to search in (defaults to English)
        mode: Search mode (SMART, EXACT, FUZZY, SEMANTIC)
        max_results: Maximum number of results
        min_score: Minimum score threshold
        force_rebuild: Force rebuild of search indices
        corpus_id: Optional specific corpus ID to search
        corpus_name: Optional specific corpus name to search

    Returns:
        List of search results ranked by relevance

    """
    # Set defaults
    if languages is None:
        languages = [Language.ENGLISH]

    # Track timing for performance metrics
    pipeline_start = time.perf_counter()

    try:
        # Query processing

        # If corpus_id or corpus_name provided, use direct corpus search
        if corpus_id or corpus_name:
            # Get corpus by ID or name
            from ..corpus.manager import get_tree_corpus_manager
            from ..search.core import Search

            manager = get_tree_corpus_manager()
            corpus = await manager.get_corpus(corpus_id=corpus_id, corpus_name=corpus_name)
            if corpus is None:
                logger.error(f"Corpus not found: {corpus_id or corpus_name}")
                return []

            # Create search engine for this corpus
            search_engine = await Search.from_corpus(
                corpus_name=corpus.corpus_name,
                semantic=True,
            )

            # Perform search
            results = await search_engine.search_with_mode(
                query=word,
                mode=mode,
                max_results=max_results,
                min_score=min_score,
            )
        else:
            # Use language-based search (existing behavior)
            language_search = await get_language_search(
                languages=languages,
                force_rebuild=force_rebuild,
            )

            # Perform search with specified mode
            results = await language_search.search_with_mode(
                query=word,
                mode=mode,
                max_results=max_results,
                min_score=min_score,
            )

        # Search completed

        # Log search metrics
        pipeline_time = time.perf_counter() - pipeline_start
        logger.info(
            f"✅ Search completed: {len(results)} results for '{word}' in {pipeline_time:.2f}s",
        )

        # Log detailed metrics
        if results:
            scores = [r.score for r in results]
            log_search_method(
                method="pipeline_total",
                query=word,
                result_count=len(results),
                duration=pipeline_time,
                scores=scores,
            )

        return results

    except Exception as e:
        pipeline_time = time.perf_counter() - pipeline_start
        logger.error(f"❌ Search pipeline failed for '{word}' after {pipeline_time:.2f}s: {e}")

        log_metrics(
            word=word,
            error=str(e),
            pipeline_time=pipeline_time,
            stage="search_pipeline_error",
        )
        # Search failed
        return []


@log_timing
async def find_best_match(
    word: str,
    languages: list[Language] | None = None,
    semantic: bool = True,
) -> SearchResult | None:
    """Find the single best match for a word.

    Convenience function that wraps search_word_pipeline and returns
    only the top result, or None if no results found.

    Args:
        word: Word to search for
        languages: Languages to search in
        semantic: Enable semantic search

    Returns:
        Best matching search result or None

    """
    # Map semantic parameter to SearchMode
    mode = SearchMode.SMART if semantic else SearchMode.EXACT

    results = await search_word_pipeline(
        word=word,
        languages=languages,
        mode=mode,
        max_results=1,
    )

    if results:
        best = results[0]
        logger.debug(
            f"✅ Best match for '{word}': '{best.word}' (score: {best.score:.3f}, method: {best.method})",
        )
        return best
    logger.debug(f"❌ No match found for '{word}'")
    return None


async def search_similar_words(
    word: str,
    languages: list[Language] | None = None,
    max_results: int = 10,
    exclude_original: bool = True,
) -> list[SearchResult]:
    """Search for words similar to the given word.

    Uses semantic search to find contextually similar words,
    useful for synonym generation and word discovery.

    Args:
        word: Word to find similar words for
        languages: Languages to search in
        max_results: Maximum number of results
        exclude_original: Whether to exclude the original word from results

    Returns:
        List of similar words ranked by semantic similarity

    """
    # Always use semantic search for similarity
    results = await search_word_pipeline(
        word=word,
        languages=languages,
        semantic=True,
        max_results=max_results + (1 if exclude_original else 0),
    )

    # Filter out the original word if requested
    if exclude_original:
        results = [result for result in results if result.word.lower() != word.lower()]
        # Limit to requested number after filtering
        results = results[:max_results]

    return results
