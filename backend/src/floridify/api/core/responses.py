"""Extended response models for specialized API endpoints.

This module provides response models that extend the base ResourceResponse and ListResponse
for endpoints that need additional structure or metadata.
"""

from typing import Any

from pydantic import BaseModel, Field


class StreamResponse(BaseModel):
    """Base class for Server-Sent Event (SSE) responses."""

    event: str = Field(..., description="Event type")
    data: Any = Field(..., description="Event data")
    id: str | None = Field(None, description="Event ID")
    retry: int | None = Field(None, description="Retry timeout in milliseconds")


class ProgressResponse(StreamResponse):
    """Progress event for long-running operations."""

    event: str = Field(default="progress")
    stage: str = Field(..., description="Current stage of operation")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str = Field(..., description="Progress message")
    details: dict[str, Any] | None = Field(None, description="Additional details")


class CompleteResponse(StreamResponse):
    """Completion event for streaming operations."""

    event: str = Field(default="complete")
    result: Any = Field(..., description="Final result")
    duration_ms: int | None = Field(None, description="Total operation duration")


class ValidationErrorResponse(BaseModel):
    """Enhanced validation error response with field-level details."""

    error: str = Field(default="Validation Error")
    validation_errors: list[dict[str, Any]] = Field(..., description="Field validation errors")
    request_id: str | None = Field(None, description="Request tracking ID")

    @classmethod
    def from_pydantic_errors(
        cls, errors: list[dict[str, Any]], request_id: str | None = None
    ) -> "ValidationErrorResponse":
        """Create from Pydantic validation errors."""
        validation_errors = []
        for error in errors:
            validation_errors.append(
                {
                    "field": ".".join(str(loc) for loc in error.get("loc", [])),
                    "message": error.get("msg", "Invalid value"),
                    "type": error.get("type", "value_error"),
                    "input": error.get("input"),
                }
            )
        return cls(validation_errors=validation_errors, request_id=request_id)
