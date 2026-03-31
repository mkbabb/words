"""Caching utilities for API responses."""

import hashlib

from fastapi import Request
from pydantic import BaseModel

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

    if config.vary_by_user:
        from ..middleware.auth_state import AuthState

        auth: AuthState = request.state.auth
        user_id = auth.user_id or "anonymous"
        parts.append(str(user_id))

    # Create hash of all parts
    key_string = ":".join(parts)
    return hashlib.sha256(key_string.encode()).hexdigest()
