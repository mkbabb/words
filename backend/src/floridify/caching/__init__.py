"""Modern generalized caching system for Floridify."""

from .core import (
    CacheBackend,
    CacheMetadata,
    CacheNamespace,
    CacheTTL,
    CompressionType,
    QuantizationType,
)
from .decorators import (
    cached_api_call,
    cached_api_call_with_dedup,
    cached_computation,
    cached_computation_async,
    cached_computation_sync,
    deduplicated,
)
from .unified import (
    UnifiedCache,
    clear_all_cache,
    get_unified,
    invalidate_cache_namespace,
)

__all__ = [
    "CacheBackend",
    "CacheNamespace",
    "CacheTTL",
    "CompressionType",
    "QuantizationType", 
    "CacheMetadata",
    "UnifiedCache",
    "get_unified",
    "invalidate_cache_namespace",
    "clear_all_cache",
    "cached_api_call",
    "cached_computation",
    "cached_computation_async",
    "cached_computation_sync",
    "deduplicated",
    "cached_api_call_with_dedup",
]
