"""Modern generalized caching system for Floridify."""

from .cache_manager import CacheManager, get_cache_manager
from .decorators import (
    cached_api_call,
    cached_api_call_with_dedup,
    cached_computation,
    deduplicated,
)
from .http_client import get_cached_http_client
from .unified_cache import UnifiedSearchCache, get_unified_cache

__all__ = [
    "CacheManager",
    "get_cache_manager",
    "cached_api_call",
    "cached_computation",
    "deduplicated",
    "cached_api_call_with_dedup",
    "get_cached_http_client",
    "UnifiedSearchCache",
    "get_unified_cache",
]
