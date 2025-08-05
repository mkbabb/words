"""
Unified corpus management system for all corpus types.

Provides a single interface for language search, wordlist, and custom corpora
with optional semantic embeddings and automatic optimization.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Protocol

from ..models.definition import CorpusType, Language
from ..search.core import SearchEngine
from ..search.corpus import CorpusCache, CorpusLanguageLoader, get_corpus_cache
from ..search.corpus.semantic_cache import SemanticIndexCache
from ..search.models import CorpusData
from ..search.semantic_manager import get_semantic_search_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Constants for automatic semantic detection
SMALL_CORPUS_THRESHOLD = 10000  # Auto-enable semantic for corpora < 10k words
SEMANTIC_TTL_HOURS = 168.0  # 1 week for semantic cache
DEFAULT_TTL_HOURS = 24.0  # 1 day for regular cache


class CorpusConfig(Protocol):
    """Configuration protocol for corpus creation."""
    
    corpus_type: CorpusType
    corpus_id: str
    words: list[str]
    phrases: list[str] | None
    semantic: bool | None
    ttl_hours: float | None
    force_rebuild: bool


class CorpusManager:
    """
    Unified corpus management system.
    
    Provides single interface for all corpus operations with automatic
    semantic embeddings, caching, and invalidation.
    """
    
    def __init__(self) -> None:
        """Initialize corpus manager."""
        self._in_memory_cache: CorpusCache | None = None
        self._semantic_manager = get_semantic_search_manager()
    
    async def _get_in_memory_cache(self) -> CorpusCache:
        """Get or create in-memory corpus cache."""
        if self._in_memory_cache is None:
            self._in_memory_cache = await get_corpus_cache()
        return self._in_memory_cache
    
    def _generate_corpus_key(self, corpus_type: CorpusType, corpus_id: str) -> str:
        """Generate consistent corpus cache key."""
        return f"{corpus_type.value}:{corpus_id}"
    
    def _generate_corpus_name(self, corpus_type: CorpusType, corpus_id: str) -> str:
        """Generate human-readable corpus name."""
        if corpus_type == CorpusType.LANGUAGE_SEARCH:
            return f"Language Search ({corpus_id})"
        elif corpus_type == CorpusType.WORDLIST:
            return f"Words in wordlist {corpus_id}"
        elif corpus_type == CorpusType.WORDLIST_NAMES:
            return "Wordlist Names"
        else:  # CUSTOM
            return f"Custom Corpus ({corpus_id})"
    
    def _should_enable_semantic(
        self, 
        words: list[str], 
        explicit_semantic: bool | None
    ) -> bool:
        """Determine if semantic search should be enabled."""
        # Always enable semantic indices by default
        # The decision to use them is made at query time
        if explicit_semantic is not None:
            return explicit_semantic
        
        # Always return True - build semantic indices for all corpora
        return True
    
    def _generate_vocabulary_hash(self, words: list[str], phrases: list[str] | None = None) -> str:
        """Generate hash for vocabulary caching."""
        vocabulary = sorted(words) + sorted(phrases or [])
        content = "\n".join(vocabulary)
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def create_corpus(
        self,
        corpus_type: CorpusType,
        corpus_id: str,
        words: list[str],
        phrases: list[str] | None = None,
        semantic: bool | None = None,
        ttl_hours: float | None = None,
        force_rebuild: bool = False,
    ) -> str:
        """
        Create a unified corpus with optional semantic embeddings.
        
        Args:
            corpus_type: Type of corpus to create
            corpus_id: Unique identifier for this corpus
            words: List of words to include
            phrases: Optional list of phrases to include
            semantic: Enable semantic search (auto-detected if None)
            ttl_hours: Time to live in hours (None = no expiration)
            force_rebuild: Force rebuild even if cached
            
        Returns:
            Internal corpus cache ID
        """
        start_time = time.perf_counter()
        
        # Generate corpus identifiers
        corpus_key = self._generate_corpus_key(corpus_type, corpus_id)
        corpus_name = self._generate_corpus_name(corpus_type, corpus_id)
        
        # Determine semantic settings
        should_semantic = self._should_enable_semantic(words, semantic)
        effective_ttl = ttl_hours if ttl_hours is not None else (
            SEMANTIC_TTL_HOURS if should_semantic else DEFAULT_TTL_HOURS
        )
        
        logger.info(
            f"Creating {corpus_type.value} corpus '{corpus_id}': "
            f"{len(words)} words, {len(phrases or [])} phrases, "
            f"semantic={'enabled' if should_semantic else 'disabled'}, "
            f"TTL={effective_ttl}h"
        )
        
        # For language search, load from sources if empty
        if corpus_type == CorpusType.LANGUAGE_SEARCH and not words:
            words, phrases = await self._load_language_corpus(corpus_id)
        
        # Create in-memory corpus
        cache = await self._get_in_memory_cache()
        internal_corpus_id = cache.create_corpus(
            words=words,
            phrases=phrases,
            name=corpus_name,
            ttl_hours=effective_ttl,
        )
        
        # Create semantic embeddings if enabled
        if should_semantic:
            await self._ensure_semantic_embeddings(
                corpus_key=corpus_key,
                corpus_name=corpus_name,
                words=words,
                force_rebuild=force_rebuild,
            )
        
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"Created corpus {corpus_key} -> {internal_corpus_id[:8]} in {elapsed_ms}ms"
        )
        
        return internal_corpus_id
    
    async def _ensure_semantic_embeddings(
        self,
        corpus_key: str,
        corpus_name: str,
        words: list[str],
        force_rebuild: bool = False,
    ) -> None:
        """Ensure semantic embeddings exist for corpus."""
        try:
            # Use semantic manager to create or get semantic search instance
            await self._semantic_manager.get_or_create_semantic_search(
                corpus_name=corpus_name,
                vocabulary=words,
                force_rebuild=force_rebuild,
                ttl_hours=SEMANTIC_TTL_HOURS,
            )
            logger.info(f"Ensured semantic embeddings for {corpus_key} ({len(words)} words)")
        except Exception as e:
            logger.error(f"Failed to ensure semantic embeddings for {corpus_key}: {e}")
    
    async def _load_language_corpus(self, corpus_id: str) -> tuple[list[str], list[str]]:
        """Load language corpus from sources.
        
        Args:
            corpus_id: Corpus ID in format 'en' or 'en-fr-de'
            
        Returns:
            Tuple of (words, phrases)
        """
        # Parse languages from corpus ID
        language_codes = corpus_id.split('-')
        languages = [Language(code) for code in language_codes]
        
        # Load using CorpusLanguageLoader
        loader = CorpusLanguageLoader(force_rebuild=False)
        await loader.load_languages(languages)
        
        words = loader.get_all_words()
        phrases = loader.get_all_phrases()
        
        logger.info(f"Loaded language corpus for {corpus_id}: {len(words)} words, {len(phrases)} phrases")
        return words, phrases
    
    async def get_corpus_info(self, internal_corpus_id: str) -> dict[str, Any] | None:
        """Get information about a corpus."""
        cache = await self._get_in_memory_cache()
        metadata = cache.get_corpus_info(internal_corpus_id)
        
        if not metadata:
            return None
        
        return {
            "corpus_id": metadata.corpus_id,
            "name": metadata.name,
            "created_at": metadata.created_at,
            "expires_at": metadata.expires_at,
            "word_count": metadata.word_count,
            "phrase_count": metadata.phrase_count,
            "search_count": metadata.search_count,
            "last_accessed": metadata.last_accessed,
        }
    
    async def search_corpus(
        self,
        internal_corpus_id: str,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
        semantic: bool = False,
    ) -> dict[str, Any]:
        """Search within a corpus using unified interface."""
        cache = await self._get_in_memory_cache()
        entry = cache.get_corpus(internal_corpus_id)
        
        if not entry:
            raise ValueError(f"Corpus {internal_corpus_id} not found")
        
        # Create search engine for this query (semantic manager handles semantic search)
        search_engine = SearchEngine(
            words=entry.words,
            phrases=entry.phrases,
            min_score=min_score or 0.6,
            semantic=semantic,
            corpus_name=entry.metadata.name,
        )
        
        # Perform search
        start_time = time.perf_counter()
        results = await search_engine.search(
            query=query,
            max_results=max_results,
            min_score=min_score,
            semantic=semantic,
        )
        search_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        return {
            "results": [
                {
                    "word": result.word,
                    "score": result.score,
                    "method": result.method.value,
                    "is_phrase": result.is_phrase,
                }
                for result in results
            ],
            "metadata": {
                "corpus_id": internal_corpus_id,
                "query": query,
                "result_count": len(results),
                "search_time_ms": search_time_ms,
                "semantic_enabled": semantic,
                "corpus_stats": entry.metadata.model_dump(),
            },
        }
    
    async def invalidate_corpus(self, corpus_type: CorpusType, corpus_id: str) -> int:
        """
        Invalidate a specific corpus.
        
        Args:
            corpus_type: Type of corpus to invalidate
            corpus_id: Specific corpus ID to invalidate
            
        Returns:
            Number of cache entries invalidated
        """
        corpus_name = self._generate_corpus_name(corpus_type, corpus_id)
        corpus_key = self._generate_corpus_key(corpus_type, corpus_id)
        
        invalidated_count = 0
        
        # Invalidate in-memory cache
        cache = await self._get_in_memory_cache()
        if cache.remove_corpus_by_name(corpus_name):
            invalidated_count += 1
            logger.debug(f"Invalidated in-memory corpus: {corpus_name}")
        
        # Invalidate semantic cache through semantic manager
        if await self._semantic_manager.invalidate_semantic_search(corpus_name):
            invalidated_count += 1
            logger.debug(f"Invalidated semantic search: {corpus_name}")
        
        # Also invalidate MongoDB semantic cache
        semantic_invalidated = await SemanticIndexCache.invalidate_corpus(corpus_name)
        invalidated_count += semantic_invalidated
        
        if invalidated_count > 0:
            logger.info(f"Invalidated {invalidated_count} cache entries for {corpus_key}")
        
        return invalidated_count
    
    async def invalidate_all_corpora(self, corpus_type: CorpusType) -> int:
        """
        Invalidate all corpora of a specific type.
        
        Args:
            corpus_type: Type of corpora to invalidate
            
        Returns:
            Total number of cache entries invalidated
        """
        invalidated_count = 0
        
        # Get all corpora and filter by type
        cache = await self._get_in_memory_cache()
        all_corpora = cache.list_corpora()
        
        for corpus_metadata in all_corpora:
            # Check if corpus name matches the type pattern
            corpus_name = corpus_metadata.name
            if self._matches_corpus_type(corpus_name, corpus_type):
                # Extract corpus_id from name for invalidation
                corpus_id = self._extract_corpus_id_from_name(corpus_name, corpus_type)
                if corpus_id:
                    count = await self.invalidate_corpus(corpus_type, corpus_id)
                    invalidated_count += count
        
        # Also invalidate semantic caches by pattern
        if corpus_type == CorpusType.WORDLIST:
            # Invalidate all wordlist-related semantic caches
            pattern_count = await SemanticIndexCache.cleanup_by_pattern("Words in wordlist")
            invalidated_count += pattern_count
        elif corpus_type == CorpusType.WORDLIST_NAMES:
            pattern_count = await SemanticIndexCache.invalidate_corpus("Wordlist Names")
            invalidated_count += pattern_count
        
        logger.info(f"Invalidated {invalidated_count} total cache entries for {corpus_type.value}")
        return invalidated_count
    
    def _matches_corpus_type(self, corpus_name: str, corpus_type: CorpusType) -> bool:
        """Check if corpus name matches the given type."""
        if corpus_type == CorpusType.LANGUAGE_SEARCH:
            return corpus_name.startswith("Language Search")
        elif corpus_type == CorpusType.WORDLIST:
            return corpus_name.startswith("Words in wordlist")
        elif corpus_type == CorpusType.WORDLIST_NAMES:
            return corpus_name == "Wordlist Names"
        else:  # CUSTOM
            return corpus_name.startswith("Custom Corpus")
    
    def _extract_corpus_id_from_name(self, corpus_name: str, corpus_type: CorpusType) -> str | None:
        """Extract corpus ID from corpus name."""
        if corpus_type == CorpusType.LANGUAGE_SEARCH:
            # "Language Search (en)" -> "en"
            start = corpus_name.find("(")
            end = corpus_name.find(")")
            if start != -1 and end != -1:
                return corpus_name[start+1:end]
        elif corpus_type == CorpusType.WORDLIST:
            # "Words in wordlist 507f1f77bcf86cd799439011" -> "507f1f77bcf86cd799439011"
            prefix = "Words in wordlist "
            if corpus_name.startswith(prefix):
                return corpus_name[len(prefix):]
        elif corpus_type == CorpusType.WORDLIST_NAMES:
            return "global"  # Single global wordlist names corpus
        else:  # CUSTOM
            # "Custom Corpus (user_123)" -> "user_123"
            start = corpus_name.find("(")
            end = corpus_name.find(")")
            if start != -1 and end != -1:
                return corpus_name[start+1:end]
        
        return None
    
    async def rebuild_corpus(
        self,
        corpus_type: CorpusType,
        corpus_id: str,
        words: list[str],
        phrases: list[str] | None = None,
        semantic: bool | None = None,
        force_rebuild: bool = True,
    ) -> str:
        """
        Rebuild a corpus with fresh data.
        
        Args:
            corpus_type: Type of corpus to rebuild
            corpus_id: Corpus ID to rebuild
            words: New word list
            phrases: New phrase list
            semantic: Enable semantic search
            force_rebuild: Force rebuild of semantic embeddings
            
        Returns:
            New internal corpus ID
        """
        # First invalidate existing corpus
        await self.invalidate_corpus(corpus_type, corpus_id)
        
        # Create new corpus with same ID
        return await self.create_corpus(
            corpus_type=corpus_type,
            corpus_id=corpus_id,
            words=words,
            phrases=phrases,
            semantic=semantic,
            force_rebuild=force_rebuild,
        )
    
    async def get_stats(self) -> dict[str, Any]:
        """Get comprehensive corpus management statistics."""
        # In-memory cache stats
        cache = await self._get_in_memory_cache()
        cache_stats = cache.get_stats()
        
        # Semantic cache stats
        semantic_count = await SemanticIndexCache.count()
        
        # Semantic manager stats
        semantic_stats = self._semantic_manager.get_stats()
        
        # Manager stats
        manager_stats = {
            "semantic_cache_entries": semantic_count,
            "semantic_manager": semantic_stats,
        }
        
        return {
            "in_memory_cache": cache_stats,
            "semantic_cache": manager_stats,
        }


# Global corpus manager instance
_corpus_manager: CorpusManager | None = None


async def get_corpus_manager() -> CorpusManager:
    """Get or create the global corpus manager."""
    global _corpus_manager
    if _corpus_manager is None:
        _corpus_manager = CorpusManager()
        logger.info("Initialized unified corpus manager")
    return _corpus_manager


async def shutdown_corpus_manager() -> None:
    """Shutdown the global corpus manager."""
    global _corpus_manager
    if _corpus_manager:
        _corpus_manager = None
        logger.info("Shutdown unified corpus manager")


async def get_corpus_entry(corpus_name: str) -> dict[str, Any] | None:
    """Get corpus data by name.
    
    Args:
        corpus_name: Full corpus name (e.g., 'language_search_en-fr')
        
    Returns:
        Dict with words, phrases, and metadata or None if not found
    """
    # Try to get from MongoDB
    corpus_data = await CorpusData.find_one({"corpus_name": corpus_name})
    if corpus_data:
        return {
            "words": corpus_data.words,
            "phrases": corpus_data.phrases,
            "metadata": corpus_data.metadata,
        }
    
    # Try to get from in-memory cache
    manager = await get_corpus_manager()
    cache = await manager._get_in_memory_cache()
    
    # Search through cache entries
    for entry_id, entry in cache._cache.items():
        if entry.metadata.name == corpus_name:
            return {
                "words": entry.words,
                "phrases": entry.phrases,
                "metadata": {
                    "corpus_id": entry.metadata.corpus_id,
                    "created_at": entry.metadata.created_at,
                    "word_count": entry.metadata.word_count,
                    "phrase_count": entry.metadata.phrase_count,
                }
            }
    
    return None

__all__ = ["CorpusManager", "CorpusType", "get_corpus_manager", "get_corpus_entry"]
