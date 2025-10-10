"""Modern generalized caching system for Floridify."""

from .core import (
    GlobalCacheManager,
    get_global_cache,
    shutdown_global_cache,
)
from .decorators import (
    cached_api_call,
    cached_api_call_with_dedup,
    cached_computation,
    cached_computation_async,
    cached_computation_sync,
    deduplicated,
)
from .models import (
    CacheNamespace,
    CompressionType,
)

__all__ = [
    "CacheNamespace",
    "CompressionType",
    "GlobalCacheManager",
    "cached_api_call",
    "cached_api_call_with_dedup",
    "cached_computation",
    "cached_computation_async",
    "cached_computation_sync",
    "deduplicated",
    "get_global_cache",
    "shutdown_global_cache",
]
