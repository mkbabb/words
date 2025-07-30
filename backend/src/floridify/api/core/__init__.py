"""Core API utilities and base classes."""

from .base import (
    BaseRepository,
    BatchRequest,
    BatchResponse,
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
from .dependencies import (
    get_fields,
    get_pagination,
    get_sort,
)
from .exceptions import (
    APIException,
    ConflictException,
    ErrorDetail,
    ErrorResponse,
    ForbiddenException,
    InvalidContentTypeException,
    NotFoundException,
    PayloadTooLargeException,
    RateLimitException,
    ServiceUnavailableException,
    UnauthorizedException,
    ValidationException,
    VersionConflictException,
    raise_conflict,
    raise_not_found,
    raise_validation_error,
    raise_version_conflict,
)
from .query import (
    AggregationBuilder,
    BulkOperationBuilder,
    QueryOptimizer,
)
from .responses import (
    CompleteResponse,
    ProgressResponse,
    StreamResponse,
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
    # Exceptions
    "APIException",
    "NotFoundException",
    "ValidationException",
    "ConflictException",
    "VersionConflictException",
    "UnauthorizedException",
    "ForbiddenException",
    "RateLimitException",
    "ServiceUnavailableException",
    "PayloadTooLargeException",
    "InvalidContentTypeException",
    "raise_not_found",
    "raise_validation_error",
    "raise_conflict",
    "raise_version_conflict",
]
