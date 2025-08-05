"""
Semantic Search Manager - Centralized management of semantic search instances.

Provides singleton pattern for managing semantic search instances across the application
with proper caching, initialization, and lifecycle management.
"""

from __future__ import annotations

import time
from typing import Any

from ..utils.logging import get_logger
from .semantic import SemanticSearch

logger = get_logger(__name__)


class SemanticSearchManager:
    """
    Centralized manager for semantic search instances.
    
    Handles creation, caching, and lifecycle of semantic search instances
    to avoid duplication and ensure efficient resource usage.
    """
    
    def __init__(self) -> None:
        """Initialize semantic search manager."""
        self._instances: dict[str, SemanticSearch] = {}
    
    async def get_or_create_semantic_search(
        self,
        corpus_name: str,
        vocabulary: list[str],
        force_rebuild: bool = False,
        ttl_hours: float = 168.0,
    ) -> SemanticSearch:
        """
        Get existing semantic search instance or create new one.
        
        Args:
            corpus_name: Unique name for the corpus
            vocabulary: Words to create embeddings for
            force_rebuild: Force rebuild even if cached
            ttl_hours: Cache TTL in hours
            
        Returns:
            Initialized SemanticSearch instance
        """
        # Check if we already have an initialized instance
        if corpus_name in self._instances and not force_rebuild:
            existing = self._instances[corpus_name]
            if hasattr(existing, 'vocabulary') and existing.vocabulary:
                logger.debug(f"Reusing existing semantic search for '{corpus_name}'")
                return existing
        
        # Create new semantic search instance
        logger.info(f"Creating semantic search for corpus '{corpus_name}' with {len(vocabulary)} words")
        start_time = time.perf_counter()
        
        semantic_search = SemanticSearch(
            corpus_name=corpus_name,
            force_rebuild=force_rebuild,
            ttl_hours=ttl_hours,
        )
        
        # Initialize with vocabulary
        await semantic_search.initialize(vocabulary)
        
        # Cache the instance
        self._instances[corpus_name] = semantic_search
        
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"Semantic search created for '{corpus_name}' in {elapsed_ms}ms")
        
        return semantic_search
    
    def get_semantic_search(self, corpus_name: str) -> SemanticSearch | None:
        """
        Get existing semantic search instance without creating new one.
        
        Args:
            corpus_name: Corpus name to look up
            
        Returns:
            Existing SemanticSearch instance or None if not found
        """
        return self._instances.get(corpus_name)
    
    async def invalidate_semantic_search(self, corpus_name: str) -> bool:
        """
        Invalidate and remove semantic search instance.
        
        Args:
            corpus_name: Corpus name to invalidate
            
        Returns:
            True if instance was removed, False if not found
        """
        if corpus_name in self._instances:
            semantic_search = self._instances[corpus_name]
            
            # Invalidate cache in the semantic search instance
            await semantic_search.invalidate_cache(corpus_name)
            
            # Remove from manager
            del self._instances[corpus_name]
            logger.info(f"Invalidated semantic search for '{corpus_name}'")
            return True
        
        return False
    
    async def invalidate_all(self) -> int:
        """
        Invalidate all semantic search instances.
        
        Returns:
            Number of instances invalidated
        """
        count = 0
        corpus_names = list(self._instances.keys())
        
        for corpus_name in corpus_names:
            if await self.invalidate_semantic_search(corpus_name):
                count += 1
        
        return count
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics about managed semantic search instances."""
        return {
            "total_instances": len(self._instances),
            "corpus_names": list(self._instances.keys()),
            "memory_usage": {
                name: {
                    "vocabulary_size": len(instance.vocabulary) if hasattr(instance, 'vocabulary') and instance.vocabulary else 0,
                    "model_name": getattr(instance, 'model_name', 'unknown'),
                }
                for name, instance in self._instances.items()
            }
        }


# Global singleton instance
_semantic_search_manager: SemanticSearchManager | None = None


def get_semantic_search_manager() -> SemanticSearchManager:
    """Get or create global semantic search manager singleton."""
    global _semantic_search_manager
    if _semantic_search_manager is None:
        _semantic_search_manager = SemanticSearchManager()
        logger.info("Initialized semantic search manager")
    return _semantic_search_manager


async def shutdown_semantic_search_manager() -> None:
    """Shutdown global semantic search manager."""
    global _semantic_search_manager
    if _semantic_search_manager:
        await _semantic_search_manager.invalidate_all()
        _semantic_search_manager = None
        logger.info("Shutdown semantic search manager")