"""Modern generalized caching system for Floridify."""

from .cache_manager import CacheManager
from .decorators import cached_api_call, cached_api_call_with_dedup, cached_computation
from .http_client import get_cached_http_client
# from .request_deduplicator import deduplicated  # TODO: Implement

__all__ = [
    "CacheManager",
    "cached_api_call",
    "cached_api_call_with_dedup",
    "cached_computation",
    # "deduplicated",  # TODO: Implement
    "get_cached_http_client",
]
