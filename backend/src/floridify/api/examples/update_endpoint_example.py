"""Example of updating existing endpoints to use request deduplication.

This shows how to refactor existing cached endpoints to add deduplication support.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...caching import cached_api_call
from ...utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


# BEFORE: Original endpoint with just caching
@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda word, params: (
        "api_lookup_old",
        word,
        params.get("force_refresh", False),
    ),
)
async def lookup_word_old(word: str, params: dict[str, Any]) -> dict[str, Any]:
    """Original implementation with only caching."""
    logger.info(f"Looking up word: {word}")
    # ... expensive lookup operation ...
    return {"word": word, "definition": "..."}


# AFTER: Updated endpoint with caching AND deduplication
@cached_api_call(
    ttl_hours=1.0,
    key_func=lambda word, params: (
        "api_lookup_new",
        word,
        params.get("force_refresh", False),
    ),
)
async def lookup_word_new(word: str, params: dict[str, Any]) -> dict[str, Any]:
    """Updated implementation with caching and deduplication.
    
    Benefits over the original:
    1. Still has all the caching benefits
    2. Concurrent requests for the same word share the result
    3. Reduces load on backend services during traffic spikes
    """
    logger.info(f"Looking up word: {word}")
    # ... expensive lookup operation ...
    return {"word": word, "definition": "..."}


# For existing code that needs minimal changes, you can also apply
# deduplication as a separate decorator:
from ...caching import deduplicated


@deduplicated(key_func=lambda word: f"synonym_lookup:{word}")
@cached_api_call(
    ttl_hours=24.0,  # Synonyms change rarely
    key_func=lambda word: ("api_synonyms", word),
)
async def get_synonyms(word: str) -> list[str]:
    """Get synonyms with both caching and deduplication.
    
    This approach keeps the existing decorator and adds deduplication on top.
    """
    logger.info(f"Finding synonyms for: {word}")
    # ... expensive synonym lookup ...
    return ["synonym1", "synonym2", "synonym3"]


# Migration strategy example
class MigrationExample:
    """Example showing how to gradually migrate existing code."""
    
    def __init__(self, use_deduplication: bool = False):
        self.use_deduplication = use_deduplication
    
    async def lookup_definition(self, word: str) -> dict[str, Any]:
        """Conditionally use deduplication based on feature flag."""
        if self.use_deduplication:
            return await self._lookup_with_dedup(word)
        else:
            return await self._lookup_cached_only(word)
    
    @cached_api_call(ttl_hours=1.0)
    async def _lookup_cached_only(self, word: str) -> dict[str, Any]:
        """Original implementation."""
        logger.info(f"Lookup (cache only): {word}")
        # ... implementation ...
        return {"word": word, "cached_only": True}
    
    @cached_api_call(ttl_hours=1.0)
    async def _lookup_with_dedup(self, word: str) -> dict[str, Any]:
        """New implementation with deduplication."""
        logger.info(f"Lookup (cache + dedup): {word}")
        # ... same implementation ...
        return {"word": word, "with_dedup": True}


# Real-world example: Updating the existing lookup endpoint
def update_lookup_endpoint_example():
    """Shows the minimal changes needed to add deduplication."""
    
    # Original code:
    # @cached_api_call(
    #     ttl_hours=1.0,
    #     key_func=lambda word, params: (
    #         "api_lookup",
    #         word,
    #         params.force_refresh,
    #         tuple(params.providers),
    #         params.no_ai,
    #     ),
    # )
    
    # Updated code (just change the decorator name and add max_wait_time):
    # @cached_api_call(
    #     ttl_hours=1.0,
    #     key_func=lambda word, params: (
    #         "api_lookup",
    #         word,
    #         params.force_refresh,
    #         tuple(params.providers),
    #         params.no_ai,
    #     ),
    #     max_wait_time=45.0,  # Lookup can take time with AI synthesis
    # )
    
    pass


# Performance monitoring example


class DeduplicationMetrics:
    """Track deduplication effectiveness."""
    
    def __init__(self):
        self.total_requests = 0
        self.deduplicated_requests = 0
        self.cache_hits = 0
        self.actual_executions = 0
    
    def record_request(self, was_deduplicated: bool, was_cached: bool) -> None:
        """Record metrics for a request."""
        self.total_requests += 1
        
        if was_cached:
            self.cache_hits += 1
        elif was_deduplicated:
            self.deduplicated_requests += 1
        else:
            self.actual_executions += 1
    
    def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics."""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "deduplicated_requests": self.deduplicated_requests,
            "actual_executions": self.actual_executions,
            "deduplication_rate": (
                self.deduplicated_requests / self.total_requests 
                if self.total_requests > 0 else 0
            ),
            "cache_hit_rate": (
                self.cache_hits / self.total_requests 
                if self.total_requests > 0 else 0
            ),
        }


# Example of custom key generation for complex scenarios
def custom_dedup_key_example():
    """Shows different key generation strategies."""
    
    # 1. Simple key based on single parameter
    simple_key = lambda user_id: f"user:{user_id}"
    
    # 2. Composite key from multiple parameters
    composite_key = lambda user_id, resource_id: f"user:{user_id}:resource:{resource_id}"
    
    # 3. Key that ignores certain parameters
    def selective_key(word: str, include_etymology: bool = False, debug: bool = False):
        # Ignore debug flag in deduplication key
        return f"word:{word}:etymology:{include_etymology}"
    
    # 4. Key with normalized values
    def normalized_key(query: str, limit: int = 10):
        # Normalize query to lowercase and cap limit
        return f"search:{query.lower()}:limit:{min(limit, 100)}"
    
    # 5. Key for time-bucketed deduplication
    def time_bucketed_key(user_id: str, bucket_minutes: int = 5):
        # Deduplicate within time buckets
        import time
        bucket = int(time.time() / (bucket_minutes * 60))
        return f"user:{user_id}:bucket:{bucket}"
    
    return {
        "simple": simple_key,
        "composite": composite_key,
        "selective": selective_key,
        "normalized": normalized_key,
        "time_bucketed": time_bucketed_key,
    }