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

__all__ = [
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
]