"""Type-safe protocols for API operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, TypeVar, runtime_checkable

from beanie import Document
from pydantic import BaseModel

T = TypeVar("T", bound=Document)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)


@runtime_checkable
class VersionedDocument(Protocol):
    """Protocol for documents with version support."""

    version: int


@runtime_checkable
class HasId(Protocol):
    """Protocol for objects with an id attribute."""

    id: Any


@runtime_checkable
class HasIsoformat(Protocol):
    """Protocol for objects with isoformat method (datetime-like)."""

    def isoformat(self) -> str:
        """Return ISO format string representation."""
        ...


@runtime_checkable
class HasModelDump(Protocol):
    """Protocol for Pydantic models with model_dump method."""

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        """Dump model to dictionary."""
        ...


class TypedFieldUpdater:
    """Type-safe field updater for documents."""

    @staticmethod
    def update_fields(doc: T, update_data: dict[str, Any]) -> None:
        """Update document fields with validation.

        Args:
            doc: Document to update
            update_data: Dictionary of fields to update

        Raises:
            ValueError: If field is not allowed or value is invalid
        """
        # Get allowed fields from the document's model (Pydantic v2 only)
        if not hasattr(doc, "model_fields"):
            raise ValueError(f"Document {type(doc).__name__} must be a Pydantic v2 model")
        allowed_fields = set(doc.model_fields.keys())

        for field, value in update_data.items():
            if field not in allowed_fields:
                raise ValueError(f"Field '{field}' not allowed for {type(doc).__name__}")

            # Set the validated value
            setattr(doc, field, value)


def serialize_for_response(data: Any) -> dict[str, Any]:
    """Type-safe serialization for API responses.

    Args:
        data: Data to serialize

    Returns:
        Serialized dictionary
    """
    if isinstance(data, HasModelDump):
        return data.model_dump(mode="json")
    if isinstance(data, dict):
        return data
    if isinstance(data, BaseModel):
        # Pydantic v2 models only
        return data.model_dump(mode="json")
    # Return as dict for other types
    return {"data": data}


def format_datetime(dt: Any) -> str:
    """Type-safe datetime formatting.

    Args:
        dt: Datetime-like object

    Returns:
        ISO format string or string representation
    """
    if isinstance(dt, HasIsoformat):
        return dt.isoformat()
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)
