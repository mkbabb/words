"""
Simple TTL cache for in-memory corpus storage.

Provides ephemeral corpus storage with automatic cleanup.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logging import get_logger
from .generalized import GeneralizedSearch, SearchResult
from .lexicon.core import SimpleLexicon

logger = get_logger(__name__)


class CorpusMetadata(BaseModel):
    """Metadata for a cached corpus."""
    
    corpus_id: str = Field(..., description="Unique corpus identifier")
    name: str = Field(default="", description="Optional corpus name")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(..., description="Expiration timestamp")
    word_count: int = Field(default=0, description="Number of words")
    phrase_count: int = Field(default=0, description="Number of phrases")
    search_count: int = Field(default=0, description="Number of searches performed")
    last_accessed: datetime = Field(default_factory=datetime.now)


class CorpusEntry:
    """Internal corpus cache entry."""
    
    def __init__(
        self,
        corpus_id: str,
        words: list[str],
        phrases: list[str] | None = None,
        name: str = "",
        ttl_hours: float = 1.0,
    ) -> None:
        self.metadata = CorpusMetadata(
            corpus_id=corpus_id,
            name=name,
            expires_at=datetime.now() + timedelta(hours=ttl_hours),
            word_count=len(words),
            phrase_count=len(phrases or []),
        )
        self.vocabulary = SimpleLexicon(words, phrases)
        self.search_engine: GeneralizedSearch | None = None
    
    def is_expired(self) -> bool:
        """Check if corpus has expired."""
        return datetime.now() > self.metadata.expires_at
    
    def touch(self) -> None:
        """Update last accessed time and increment search count."""
        self.metadata.last_accessed = datetime.now()
        self.metadata.search_count += 1
    
    async def get_search_engine(self) -> GeneralizedSearch:
        """Get or create search engine for this corpus."""
        if self.search_engine is None:
            self.search_engine = GeneralizedSearch(
                lexicon=self.vocabulary,
                min_score=0.6,
            )
        return self.search_engine


class CorpusCache:
    """TTL-based in-memory corpus cache with automatic cleanup."""
    
    def __init__(self, max_size: int = 100, cleanup_interval: float = 300.0) -> None:
        """
        Initialize corpus cache.
        
        Args:
            max_size: Maximum number of corpora to cache
            cleanup_interval: Cleanup interval in seconds
        """
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self._cache: dict[str, CorpusEntry] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._started = False
    
    async def start(self) -> None:
        """Start the cache cleanup task."""
        if self._started:
            return
        
        self._started = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"Started corpus cache with max_size={self.max_size}")
    
    async def stop(self) -> None:
        """Stop the cache cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self._started = False
        logger.info("Stopped corpus cache")
    
    def create_corpus(
        self,
        words: list[str],
        phrases: list[str] | None = None,
        name: str = "",
        ttl_hours: float = 1.0,
    ) -> str:
        """
        Create a new corpus and return its ID.
        
        Args:
            words: List of words to include
            phrases: Optional list of phrases
            name: Optional corpus name
            ttl_hours: Time to live in hours
            
        Returns:
            Unique corpus ID
        """
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        corpus_id = str(uuid.uuid4())
        entry = CorpusEntry(
            corpus_id=corpus_id,
            words=words,
            phrases=phrases,
            name=name,
            ttl_hours=ttl_hours,
        )
        
        self._cache[corpus_id] = entry
        logger.info(
            f"Created corpus {corpus_id[:8]} with {len(words)} words, "
            f"{len(phrases or [])} phrases, TTL={ttl_hours}h"
        )
        
        return corpus_id
    
    async def search_corpus(
        self,
        corpus_id: str,
        query: str,
        max_results: int = 20,
        min_score: float | None = None,
    ) -> dict[str, Any]:
        """
        Search within a corpus.
        
        Args:
            corpus_id: Corpus identifier
            query: Search query
            max_results: Maximum results to return
            min_score: Minimum score threshold
            
        Returns:
            Search results with metadata
            
        Raises:
            ValueError: If corpus not found or expired
        """
        entry = self._cache.get(corpus_id)
        if not entry:
            raise ValueError(f"Corpus {corpus_id} not found")
        
        if entry.is_expired():
            del self._cache[corpus_id]
            raise ValueError(f"Corpus {corpus_id} has expired")
        
        entry.touch()
        search_engine = await entry.get_search_engine()
        
        start_time = time.perf_counter()
        results = await search_engine.search(
            query=query,
            max_results=max_results,
            min_score=min_score,
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
                "corpus_id": corpus_id,
                "query": query,
                "result_count": len(results),
                "search_time_ms": search_time_ms,
                "corpus_stats": entry.metadata.model_dump(),
            }
        }
    
    def get_corpus_info(self, corpus_id: str) -> CorpusMetadata | None:
        """Get corpus metadata."""
        entry = self._cache.get(corpus_id)
        if not entry or entry.is_expired():
            return None
        return entry.metadata
    
    def list_corpora(self) -> list[CorpusMetadata]:
        """List all active corpora."""
        self._cleanup_expired()
        return [entry.metadata for entry in self._cache.values()]
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        return {
            "cache_size": len(self._cache),
            "max_size": self.max_size,
            "total_words": sum(entry.metadata.word_count for entry in self._cache.values()),
            "total_phrases": sum(entry.metadata.phrase_count for entry in self._cache.values()),
            "total_searches": sum(entry.metadata.search_count for entry in self._cache.values()),
        }
    
    def _evict_oldest(self) -> None:
        """Evict oldest corpus to make room."""
        if not self._cache:
            return
        
        oldest_id = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].metadata.created_at
        )
        del self._cache[oldest_id]
        logger.debug(f"Evicted corpus {oldest_id[:8]} (cache full)")
    
    def _cleanup_expired(self) -> None:
        """Remove expired corpora."""
        expired_ids = [
            corpus_id for corpus_id, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for corpus_id in expired_ids:
            del self._cache[corpus_id]
            logger.debug(f"Removed expired corpus {corpus_id[:8]}")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in corpus cache cleanup: {e}")


# Global cache instance
_corpus_cache: CorpusCache | None = None


async def get_corpus_cache() -> CorpusCache:
    """Get or create the global corpus cache."""
    global _corpus_cache
    if _corpus_cache is None:
        _corpus_cache = CorpusCache()
        await _corpus_cache.start()
    return _corpus_cache


async def shutdown_corpus_cache() -> None:
    """Shutdown the global corpus cache."""
    global _corpus_cache
    if _corpus_cache:
        await _corpus_cache.stop()
        _corpus_cache = None