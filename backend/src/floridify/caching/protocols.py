"""Type-safe protocols for cache serialization and type checking."""

from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .models import ContentLocation


@runtime_checkable
class CacheSerializable(Protocol):
    """Protocol for objects that can be serialized to cache keys."""

    def to_cache_key(self) -> str:
        """Convert object to a string representation for cache key."""
        ...


@runtime_checkable
class HasHeaders(Protocol):
    """Protocol for request-like objects with headers."""

    headers: dict[str, str]


@runtime_checkable
class EnumLike(Protocol):
    """Protocol for enum-like objects with a value attribute."""

    value: Any


@runtime_checkable
class VersionedContent(Protocol):
    """Protocol for objects with versioned content storage."""

    content_inline: dict[str, Any] | None
    content_location: ContentLocation | None


def serialize_cache_value(value: Any) -> str | int | float | tuple[Any, ...] | None:
    """Type-safe value serialization for cache keys.

    Args:
        value: Value to serialize

    Returns:
        Serialized representation of the value
    """
    # Handle basic types
    if value is None or isinstance(value, str | int | float | bool):
        return value

    # Handle standard enums explicitly
    if isinstance(value, Enum):
        return value.value

    # Handle protocol-based serialization
    if isinstance(value, CacheSerializable):
        return value.to_cache_key()

    # Handle lists and tuples (small collections only)
    if isinstance(value, list | tuple) and len(value) < 10:
        return tuple(value) if isinstance(value, list) else value

    # Fallback to string representation for complex objects
    try:
        return str(hash(value))
    except TypeError:
        return str(id(value))


def is_request_with_headers(obj: Any) -> bool:
    """Type-safe check for objects with headers attribute.

    Args:
        obj: Object to check

    Returns:
        True if object has headers attribute, False otherwise
    """
    return isinstance(obj, HasHeaders)
