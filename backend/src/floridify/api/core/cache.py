"""Caching utilities for API responses."""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any

import orjson
from fastapi import Request, Response
from pydantic import BaseModel

from ...caching import get_global_cache
from ...caching.core import GlobalCacheManager
from ...caching.filesystem import FilesystemBackend
from ...caching.models import CacheNamespace
from ...utils.logging import get_logger

logger = get_logger(__name__)


class APICacheConfig(BaseModel):
    """Configuration for API response caching."""

    ttl: int = 3600  # Default TTL in seconds
    include_headers: bool = False
    include_query_params: bool = True
    include_body: bool = True
    cache_private: bool = False
    vary_by_user: bool = False


def generate_cache_key(request: Request, config: APICacheConfig, prefix: str = "api") -> str:
    """Generate cache key from request."""
    parts = [prefix, request.method, request.url.path]

    if config.include_query_params and request.query_params:
        # Sort query params for consistent keys
        sorted_params = sorted(request.query_params.items())
        parts.append(str(sorted_params))

    if config.include_body and request.method in ["POST", "PUT", "PATCH"]:
        # Include body hash for write operations
        # Note: Cannot access async body() in sync function
        # Body hashing should be handled at the async decorator level
        # For now, skip body hashing in sync key generation
        pass

    if config.vary_by_user:
        # Add user identifier if authentication is implemented
        # Access state through try/except for safety
        user_id = "anonymous"
        try:
            user_id = request.state.user_id
        except AttributeError:
            pass  # Use default anonymous
        parts.append(str(user_id))

    # Create hash of all parts
    key_string = ":".join(parts)
    return hashlib.sha256(key_string.encode()).hexdigest()

