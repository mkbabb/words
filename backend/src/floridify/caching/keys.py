"""Cache key generation utilities - Pure functions, zero dependencies.

Single source of truth for all cache key generation.
All variants use SHA256 hashing for collision resistance.

This module contains ONLY pure functions - no I/O, no state, no side effects.
"""

import hashlib
from enum import Enum
from typing import Any


def generate_resource_key(resource_type: Any, resource_id: str, *qualifiers: Any) -> str:
    """Generate cache key for versioned resources using colon-separated parts.

    Pure function - zero dependencies, zero side effects.
    Uses explicit colon joining for consistency with manager.py legacy behavior.

    Args:
        resource_type: ResourceType enum (will extract .value)
        resource_id: Unique identifier for the resource
        *qualifiers: Additional qualifiers (e.g., "v", "1.0.0", "content", checksum)

    Returns:
        SHA-256 hex digest (64 characters)

    Examples:
        >>> generate_resource_key(ResourceType.CORPUS, "id123")
        'abc123...'
        >>> generate_resource_key(ResourceType.CORPUS, "id123", "v", "1.0.0")
        'def456...'
        >>> generate_resource_key(ResourceType.CORPUS, "id123", "content", "a1b2c3d4")
        'xyz789...'
    """
    # Convert all parts to strings and handle enums
    parts = []
    for part in (resource_type, resource_id, *qualifiers):
        if isinstance(part, Enum):
            parts.append(part.value)
        else:
            parts.append(str(part))

    # Combine with separator and hash
    key_string = ":".join(parts)
    return hashlib.sha256(key_string.encode()).hexdigest()


def generate_http_key(method: str, path: str, params: dict[str, Any] | None = None) -> str:
    """Generate cache key for HTTP API endpoints.

    Pure function for HTTP cache keys with optional query parameters.

    Args:
        method: HTTP method (e.g., "GET", "POST")
        path: URL path (e.g., "/api/dictionary/hello")
        params: Optional query parameters dict

    Returns:
        SHA-256 hex digest (64 characters)

    Examples:
        >>> generate_http_key("GET", "/api/dictionary/hello")
        'abc123...'
        >>> generate_http_key("GET", "/api/search", {"q": "test", "limit": 10})
        'def456...'
    """
    parts = ["api", method, path]
    if params:
        # Sort params for deterministic key generation
        parts.append(str(sorted(params.items())))
    return hashlib.sha256(":".join(parts).encode()).hexdigest()


def generate_cache_key(key_parts: tuple[Any, ...]) -> str:
    """Generate SHA-256 cache key from tuple of parts.

    Core implementation used by decorator-based caching.
    Uses str(tuple) for stable serialization.

    Args:
        key_parts: Tuple of any values (already prepared)

    Returns:
        SHA-256 hex digest (64 characters)

    Examples:
        >>> parts = ("dictionary", "hello")
        >>> generate_cache_key(parts)
        'a1b2c3d4...'
        >>> parts = ("CORPUS", "my-corpus", "v", "1.0.0")
        >>> generate_cache_key(parts)
        'e5f6g7h8...'
    """
    return hashlib.sha256(str(key_parts).encode()).hexdigest()


def serialize_cache_value(value: Any) -> Any:
    """Serialize value for cache key. Handles all types uniformly.

    Used by both decorators and version manager to ensure consistent
    serialization across the caching system.

    Args:
        value: Any Python value to serialize

    Returns:
        Serialized value (primitives, enum values, tuples, or hash strings)

    Examples:
        >>> serialize_cache_value(None)
        None
        >>> serialize_cache_value("hello")
        'hello'
        >>> serialize_cache_value(CacheNamespace.DICTIONARY)
        'dictionary'
        >>> serialize_cache_value([1, 2, 3])
        (1, 2, 3)
    """
    # Primitives pass through unchanged
    if value is None or isinstance(value, str | int | float | bool):
        return value

    # Enums → extract value
    if isinstance(value, Enum):
        return value.value

    # Small collections (< 10 items) → preserve as tuple
    if isinstance(value, list | tuple) and len(value) < 10:
        return tuple(value) if isinstance(value, list) else value

    # Complex objects → hash
    try:
        return str(hash(value))
    except TypeError:
        return str(id(value))


def generate_versioned_cache_key(
    resource_type: "Any",  # ResourceType enum (avoiding circular import)
    resource_id: str,
    version: str | None = None,
) -> str:
    """Generate cache key for versioned resources.

    Uses core generate_cache_key with standardized parts.

    Args:
        resource_type: ResourceType enum (e.g., ResourceType.DICTIONARY)
        resource_id: Unique identifier for the resource
        version: Optional version string (e.g., "1.0.0")

    Returns:
        SHA-256 hex digest cache key

    Examples:
        >>> generate_versioned_cache_key(ResourceType.DICTIONARY, "hello")
        'abc123...'
        >>> generate_versioned_cache_key(ResourceType.CORPUS, "my-corpus", "1.0.0")
        'def456...'
    """
    if version:
        parts = (resource_type.value, resource_id, "v", version)
    else:
        parts = (resource_type.value, resource_id)
    return generate_cache_key(parts)


def generate_content_cache_key(
    resource_type: "Any",  # ResourceType enum (avoiding circular import)
    resource_id: str,
    checksum_prefix: str,
) -> str:
    """Generate cache key for external content storage.

    Uses core generate_cache_key with standardized parts.

    Args:
        resource_type: ResourceType enum
        resource_id: Unique identifier for the resource
        checksum_prefix: First 8 characters of content checksum

    Returns:
        SHA-256 hex digest cache key

    Examples:
        >>> generate_content_cache_key(ResourceType.DICTIONARY, "hello", "a1b2c3d4")
        'xyz789...'
    """
    parts = (resource_type.value, resource_id, "content", checksum_prefix)
    return generate_cache_key(parts)
