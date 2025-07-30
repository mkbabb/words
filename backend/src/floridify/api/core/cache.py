"""Caching utilities for API responses."""

import hashlib
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

import orjson
from beanie import PydanticObjectId
from bson import ObjectId
from fastapi import Request, Response
from pydantic import BaseModel

from ...caching.cache_manager import CacheManager, get_cache_manager


def _ensure_json_serializable(obj: Any) -> Any:
    """Recursively convert ObjectIds to strings for JSON serialization."""
    if isinstance(obj, (ObjectId, PydanticObjectId)):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_ensure_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_ensure_json_serializable(item) for item in obj)
    elif hasattr(obj, 'model_dump'):
        return obj.model_dump(mode="json")
    return obj


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
        body_bytes = request._body if hasattr(request, "_body") else b""
        if body_bytes:
            body_hash = hashlib.md5(body_bytes).hexdigest()[:8]
            parts.append(body_hash)

    if config.vary_by_user:
        # Add user identifier if authentication is implemented
        user_id = getattr(request.state, "user_id", "anonymous")
        parts.append(str(user_id))

    # Create hash of all parts
    key_string = ":".join(parts)
    return hashlib.sha256(key_string.encode()).hexdigest()


def cached_endpoint(
    ttl: int = 3600, prefix: str = "api", config: APICacheConfig | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for caching API endpoints."""
    if config is None:
        config = APICacheConfig(ttl=ttl)
    else:
        config.ttl = ttl

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(request: Request, response: Response, *args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            cache_key = generate_cache_key(request, config, prefix)

            # Try to get from cache
            cache_manager = get_cache_manager()
            cached_data = cache_manager.get((cache_key,))

            if cached_data:
                # Parse cached response
                cached_response = orjson.loads(cached_data)

                # Set cache headers
                response.headers["X-Cache"] = "HIT"
                response.headers["Cache-Control"] = f"max-age={config.ttl}"

                # Check if client has valid cache
                if "etag" in cached_response:
                    response.headers["ETag"] = cached_response["etag"]
                    client_etag = request.headers.get("If-None-Match")
                    if client_etag == cached_response["etag"]:
                        response.status_code = 304
                        return None

                return cached_response["data"]

            # Call the actual endpoint
            result = await func(request, response, *args, **kwargs)

            # Don't cache error responses
            if response.status_code >= 400:
                return result

            # Generate ETag if not already set
            if "ETag" not in response.headers:
                if isinstance(result, BaseModel):
                    content = result.model_dump_json()
                else:
                    # Ensure result is JSON-serializable
                    json_data = _ensure_json_serializable(result)
                    content = orjson.dumps(json_data).decode()
                etag = hashlib.md5(content.encode()).hexdigest()
                response.headers["ETag"] = f'"{etag}"'

            # Cache the response  
            cache_data = {
                "data": result.model_dump(mode="json") if isinstance(result, BaseModel) else _ensure_json_serializable(result),
                "etag": response.headers.get("ETag", "").strip('"'),
                "timestamp": datetime.utcnow().isoformat(),
                "status_code": response.status_code,
            }

            cache_manager.set(
                (cache_key,), orjson.dumps(cache_data).decode(), ttl_hours=config.ttl / 3600
            )

            # Set cache headers
            response.headers["X-Cache"] = "MISS"
            response.headers["Cache-Control"] = f"max-age={config.ttl}"

            return result

        return wrapper

    return decorator


class CacheInvalidator:
    """Utility for invalidating related caches."""

    def __init__(self, cache_manager: CacheManager | None = None):
        self.cache_manager = cache_manager or get_cache_manager()

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        # This would require Redis SCAN command
        # For now, we track invalidation patterns
        invalidated = 0

        # Store invalidation timestamp
        invalidation_key = f"invalidation:{pattern}"
        self.cache_manager.set(
            (invalidation_key,),
            datetime.utcnow().isoformat(),
            ttl_hours=24.0,  # Keep for 24 hours
        )

        return invalidated

    async def invalidate_word(self, word_id: str) -> None:
        """Invalidate all caches related to a word."""
        patterns = [
            f"*word*{word_id}*",
            f"*definition*{word_id}*",
            f"*synthesis*{word_id}*",
            f"*facts*{word_id}*",
            f"*examples*{word_id}*",
        ]

        for pattern in patterns:
            await self.invalidate_pattern(pattern)

    async def invalidate_definition(self, definition_id: str) -> None:
        """Invalidate all caches related to a definition."""
        patterns = [
            f"*definition*{definition_id}*",
            f"*examples*{definition_id}*",
        ]

        for pattern in patterns:
            await self.invalidate_pattern(pattern)


def get_cache_headers(
    max_age: int = 3600, private: bool = False, must_revalidate: bool = True
) -> dict[str, str]:
    """Generate standard cache headers."""
    directives = []

    if private:
        directives.append("private")
    else:
        directives.append("public")

    directives.append(f"max-age={max_age}")

    if must_revalidate:
        directives.append("must-revalidate")

    return {
        "Cache-Control": ", ".join(directives),
        "Vary": "Accept-Encoding, Accept-Language",
    }


class ResponseCache:
    """Context manager for response caching."""

    def __init__(
        self, request: Request, response: Response, ttl: int = 3600, key_prefix: str = "response"
    ):
        self.request = request
        self.response = response
        self.ttl = ttl
        self.key_prefix = key_prefix
        self.cache_manager = get_cache_manager()
        self.cache_key: str | None = None
        self.start_time: datetime | None = None

    async def __aenter__(self) -> Any:
        self.start_time = datetime.utcnow()
        config = APICacheConfig(ttl=self.ttl)
        self.cache_key = generate_cache_key(self.request, config, self.key_prefix)

        # Check cache
        cached = self.cache_manager.get((self.cache_key,))
        if cached:
            self.response.headers["X-Cache"] = "HIT"
            return orjson.loads(cached)

        self.response.headers["X-Cache"] = "MISS"
        return None

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is None and self.cache_key and self.start_time:
            # Cache successful response
            elapsed = (datetime.utcnow() - self.start_time).total_seconds()
            self.response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
