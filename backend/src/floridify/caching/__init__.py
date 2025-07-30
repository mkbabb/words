"""Modern generalized caching system for Floridify."""

from .cache_manager import CacheManager
from .decorators import (
    cached_api_call,
    cached_api_call_with_dedup,
    cached_computation,
    deduplicated,
)
from .http_client import get_cached_http_client

__all__ = [
    "CacheManager",
    "cached_api_call",
    "cached_computation",
    "deduplicated",
    "cached_api_call_with_dedup",
    "get_cached_http_client",
]
