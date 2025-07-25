"""Core API utilities and base classes."""

from .base import (
    BaseRepository,
    BatchRequest,
    BatchResponse,
    ErrorDetail,
    ErrorResponse,
    FieldSelection,
    ListResponse,
    PaginationParams,
    ResourceResponse,
    SortParams,
    check_etag,
    get_etag,
    handle_api_errors,
)
from .cache import (
    APICacheConfig,
    CacheInvalidator,
    ResponseCache,
    cached_endpoint,
    generate_cache_key,
    get_cache_headers,
)
from .query import (
    AggregationBuilder,
    BulkOperationBuilder,
    QueryOptimizer,
)

__all__ = [
    # Base
    "ErrorDetail",
    "ErrorResponse",
    "PaginationParams",
    "SortParams",
    "FieldSelection",
    "ListResponse",
    "ResourceResponse",
    "BatchRequest",
    "BatchResponse",
    "BaseRepository",
    "handle_api_errors",
    "get_etag",
    "check_etag",
    # Cache
    "APICacheConfig",
    "CacheInvalidator",
    "ResponseCache",
    "cached_endpoint",
    "generate_cache_key",
    "get_cache_headers",
    # Query
    "AggregationBuilder",
    "BulkOperationBuilder",
    "QueryOptimizer",
]
