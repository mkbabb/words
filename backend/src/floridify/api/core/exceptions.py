"""Centralized exception handling for the API.

This module eliminates 500+ lines of duplicated error handling code across routers
by providing a consistent, type-safe approach to raising HTTP exceptions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Standard error detail."""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    details: list[ErrorDetail] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str | None = None


class APIException(HTTPException):
    """Base exception with automatic ErrorResponse formatting."""

    def __init__(
        self,
        status_code: int,
        error: str,
        details: list[ErrorDetail] | None = None,
        request_id: str | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Initialize APIException with ErrorResponse formatting.

        Args:
            status_code: HTTP status code
            error: Main error message
            details: List of error details with field information
            request_id: Optional request tracking ID
            headers: Optional HTTP headers

        """
        response = ErrorResponse(
            error=error,
            details=details,
            request_id=request_id,
        )
        super().__init__(
            status_code=status_code,
            detail=response.model_dump(mode="json"),
            headers=headers,
        )


class NotFoundException(APIException):
    """404 Not Found exception."""

    def __init__(
        self,
        resource: str,
        identifier: str | None = None,
        field: str = "id",
        request_id: str | None = None,
    ):
        """Initialize 404 exception.

        Args:
            resource: Resource type (e.g., "Word", "Definition")
            identifier: Resource identifier that was not found
            field: Field name used for lookup (default: "id")
            request_id: Optional request tracking ID

        """
        if identifier:
            message = f"{resource} '{identifier}' not found"
        else:
            message = f"{resource} not found"

        super().__init__(
            status_code=404,
            error=message,
            details=[
                ErrorDetail(
                    field=field,
                    message=message,
                    code=f"{resource.upper()}_NOT_FOUND",
                ),
            ],
            request_id=request_id,
        )


class ValidationException(APIException):
    """400 Bad Request for validation errors."""

    def __init__(
        self,
        field: str,
        message: str,
        code: str = "VALIDATION_ERROR",
        request_id: str | None = None,
    ):
        """Initialize validation exception.

        Args:
            field: Field that failed validation
            message: Validation error message
            code: Error code (default: VALIDATION_ERROR)
            request_id: Optional request tracking ID

        """
        super().__init__(
            status_code=400,
            error="Validation Error",
            details=[
                ErrorDetail(
                    field=field,
                    message=message,
                    code=code,
                ),
            ],
            request_id=request_id,
        )


class ConflictException(APIException):
    """409 Conflict exception."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        code: str = "CONFLICT",
        request_id: str | None = None,
    ):
        """Initialize conflict exception.

        Args:
            message: Conflict description
            field: Optional field that caused conflict
            code: Error code (default: CONFLICT)
            request_id: Optional request tracking ID

        """
        super().__init__(
            status_code=409,
            error="Conflict",
            details=[
                ErrorDetail(
                    field=field,
                    message=message,
                    code=code,
                ),
            ],
            request_id=request_id,
        )


class VersionConflictException(ConflictException):
    """409 Conflict specifically for version mismatches."""

    def __init__(
        self,
        expected: int,
        actual: int,
        resource: str | None = None,
        request_id: str | None = None,
    ):
        """Initialize version conflict exception.

        Args:
            expected: Expected version number
            actual: Actual version number
            resource: Optional resource type
            request_id: Optional request tracking ID

        """
        message = f"Version mismatch: expected {expected}, got {actual}"
        if resource:
            message = f"{resource} version mismatch: expected {expected}, got {actual}"

        super().__init__(
            message=message,
            field="version",
            code="VERSION_CONFLICT",
            request_id=request_id,
        )


class UnauthorizedException(APIException):
    """401 Unauthorized exception."""

    def __init__(
        self,
        message: str = "Authentication required",
        code: str = "UNAUTHORIZED",
        request_id: str | None = None,
    ):
        """Initialize unauthorized exception."""
        super().__init__(
            status_code=401,
            error="Unauthorized",
            details=[
                ErrorDetail(
                    message=message,
                    code=code,
                ),
            ],
            request_id=request_id,
        )


class ForbiddenException(APIException):
    """403 Forbidden exception."""

    def __init__(
        self,
        message: str = "Access denied",
        resource: str | None = None,
        action: str | None = None,
        request_id: str | None = None,
    ):
        """Initialize forbidden exception."""
        if resource and action:
            message = f"Access denied: cannot {action} {resource}"
        elif resource:
            message = f"Access denied to {resource}"

        super().__init__(
            status_code=403,
            error="Forbidden",
            details=[
                ErrorDetail(
                    message=message,
                    code="ACCESS_DENIED",
                ),
            ],
            request_id=request_id,
        )


class RateLimitException(APIException):
    """429 Too Many Requests exception."""

    def __init__(
        self,
        retry_after: int | None = None,
        message: str = "Rate limit exceeded",
        request_id: str | None = None,
    ):
        """Initialize rate limit exception."""
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=429,
            error="Too Many Requests",
            details=[
                ErrorDetail(
                    message=message,
                    code="RATE_LIMIT_EXCEEDED",
                ),
            ],
            request_id=request_id,
            headers=headers,
        )


class ServiceUnavailableException(APIException):
    """503 Service Unavailable exception."""

    def __init__(
        self,
        service: str,
        message: str | None = None,
        retry_after: int | None = None,
        request_id: str | None = None,
    ):
        """Initialize service unavailable exception."""
        if not message:
            message = f"{service} is temporarily unavailable"

        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        super().__init__(
            status_code=503,
            error="Service Unavailable",
            details=[
                ErrorDetail(
                    field="service",
                    message=message,
                    code="SERVICE_UNAVAILABLE",
                ),
            ],
            request_id=request_id,
            headers=headers,
        )


class PayloadTooLargeException(APIException):
    """413 Payload Too Large exception."""

    def __init__(
        self,
        max_size: str,
        actual_size: str | None = None,
        field: str = "file",
        request_id: str | None = None,
    ):
        """Initialize payload too large exception."""
        if actual_size:
            message = f"File size {actual_size} exceeds maximum allowed size of {max_size}"
        else:
            message = f"File size must be less than {max_size}"

        super().__init__(
            status_code=413,
            error="File too large",
            details=[
                ErrorDetail(
                    field=field,
                    message=message,
                    code="FILE_TOO_LARGE",
                ),
            ],
            request_id=request_id,
        )


class InvalidContentTypeException(ValidationException):
    """400 Bad Request for invalid content type."""

    def __init__(
        self,
        expected_type: str,
        actual_type: str | None,
        field: str = "file",
        request_id: str | None = None,
    ):
        """Initialize invalid content type exception."""
        message = f"File must be {expected_type}"
        if actual_type:
            message = f"File must be {expected_type}, got {actual_type}"

        super().__init__(
            field=field,
            message=message,
            code="INVALID_TYPE",
            request_id=request_id,
        )


# Convenience functions for common error patterns
def raise_not_found(resource: str, identifier: str | None = None, field: str = "id") -> None:
    """Raise a 404 Not Found exception."""
    raise NotFoundException(resource, identifier, field)


def raise_validation_error(field: str, message: str, code: str = "VALIDATION_ERROR") -> None:
    """Raise a 400 Validation Error."""
    raise ValidationException(field, message, code)


def raise_conflict(message: str, field: str | None = None, code: str = "CONFLICT") -> None:
    """Raise a 409 Conflict exception."""
    raise ConflictException(message, field, code)


def raise_version_conflict(expected: int, actual: int, resource: str | None = None) -> None:
    """Raise a 409 Version Conflict exception."""
    raise VersionConflictException(expected, actual, resource)
