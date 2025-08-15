"""Common dependencies for API endpoints.

This module provides reusable dependency injection functions for FastAPI endpoints,
eliminating code duplication across routers.
"""

from fastapi import Query

from .base import FieldSelection, PaginationParams, SortParams


def get_pagination(
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
) -> PaginationParams:
    """Get pagination parameters from query.

    This is a common dependency used across all list endpoints.

    Args:
        offset: Number of items to skip (default: 0)
        limit: Number of items to return (default: 20, max: 100)

    Returns:
        PaginationParams object with offset and limit

    """
    return PaginationParams(offset=offset, limit=limit)


def get_sort(
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
) -> SortParams:
    """Get sort parameters from query.

    This is a common dependency used across all list endpoints that support sorting.

    Args:
        sort_by: Field name to sort by (optional)
        sort_order: Sort direction - 'asc' or 'desc' (default: 'asc')

    Returns:
        SortParams object with sort field and direction

    """
    return SortParams(sort_by=sort_by, sort_order=sort_order)


def get_fields(
    include: str | None = Query(None, description="Comma-separated fields to include"),
    exclude: str | None = Query(None, description="Comma-separated fields to exclude"),
    expand: str | None = Query(None, description="Comma-separated relations to expand"),
) -> FieldSelection:
    """Get field selection parameters from query.

    This dependency enables field filtering and relationship expansion on API responses.

    Args:
        include: Comma-separated list of fields to include in response
        exclude: Comma-separated list of fields to exclude from response
        expand: Comma-separated list of relationships to expand

    Returns:
        FieldSelection object with parsed field sets

    Note:
        - include and exclude are mutually exclusive - if both are provided, include takes precedence
        - expand allows loading related resources in a single request

    """
    return FieldSelection(
        include=set(include.split(",")) if include else None,
        exclude=set(exclude.split(",")) if exclude else None,
        expand=set(expand.split(",")) if expand else None,
    )


# Additional common dependencies can be added here as needed
