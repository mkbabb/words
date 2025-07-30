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
    ResponseBuilder,
    SortParams,
    check_etag,
    get_etag,
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
from .dependencies import (
    get_fields,
    get_pagination,
    get_sort,
)
from .responses import (
    StreamResponse,
    ProgressResponse,
    CompleteResponse,
    ValidationErrorResponse,
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
    "ResponseBuilder",
    "BatchRequest",
    "BatchResponse",
    "BaseRepository",
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
    # Dependencies
    "get_fields",
    "get_pagination", 
    "get_sort",
    # Extended Responses
    "StreamResponse",
    "ProgressResponse",
    "CompleteResponse",
    "ValidationErrorResponse",
]
