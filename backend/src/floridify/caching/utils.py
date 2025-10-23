"""Shared utilities for caching module.

Provides common functionality used across multiple caching modules,
including JSON encoding, namespace normalization, and async utilities.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

from beanie import PydanticObjectId
from pydantic import BaseModel

from .models import CacheNamespace

T = TypeVar("T")

__all__ = [
    "json_encoder",
    "normalize_namespace",
    "run_in_executor",
]


def json_encoder(obj: Any) -> Any:
    """Universal JSON encoder for cache metadata.

    Handles common types that are not JSON serializable by default:
    - PydanticObjectId → str
    - Enum → value
    - datetime → ISO format
    - UUID → str
    - Pydantic models → model_dump()

    Args:
        obj: Object to encode for JSON serialization

    Returns:
        JSON-serializable representation

    Raises:
        TypeError: If object type is not JSON serializable

    Examples:
        >>> json_encoder(PydanticObjectId("507f1f77bcf86cd799439011"))
        '507f1f77bcf86cd799439011'
        >>> json_encoder(CacheNamespace.DICTIONARY)
        'dictionary'
        >>> json_encoder(datetime(2025, 1, 15))
        '2025-01-15T00:00:00'
    """
    if isinstance(obj, PydanticObjectId):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def normalize_namespace(namespace: CacheNamespace | str) -> CacheNamespace:
    """Convert string namespace to enum.

    Ensures namespace is always a CacheNamespace enum, converting from
    string if necessary. This eliminates the need for repeated isinstance
    checks throughout the codebase.

    Args:
        namespace: CacheNamespace enum or string value

    Returns:
        CacheNamespace enum

    Raises:
        TypeError: If namespace is neither enum nor string
        ValueError: If string is not a valid namespace value

    Examples:
        >>> normalize_namespace("dictionary")
        <CacheNamespace.DICTIONARY: 'dictionary'>
        >>> normalize_namespace(CacheNamespace.API)
        <CacheNamespace.API: 'api'>
    """
    if isinstance(namespace, CacheNamespace):
        return namespace
    if isinstance(namespace, str):
        return CacheNamespace(namespace)
    raise TypeError(f"Invalid namespace type: {type(namespace).__name__}")


async def run_in_executor[T](func: Callable[[], T]) -> T:
    """Execute synchronous function in thread pool executor.

    Allows CPU-bound synchronous operations to run without blocking
    the async event loop. Useful for operations like compression,
    serialization, or other compute-intensive tasks.

    Args:
        func: Callable with no arguments returning T

    Returns:
        Result of func()

    Example:
        >>> import pickle
        >>> data = {"large": "object"}
        >>> serialized = await run_in_executor(lambda: pickle.dumps(data))
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func)
