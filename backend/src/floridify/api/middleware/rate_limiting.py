"""Rate limiting middleware for API endpoints."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute


class RateLimiter:
    """Token bucket rate limiter implementation."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int | None = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size or requests_per_minute

        # Storage for rate limit tracking per key
        self._minute_buckets: dict[str, list[float]] = defaultdict(list)
        self._hour_buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def _clean_bucket(self, bucket: list[float], window_seconds: float) -> None:
        """Remove expired timestamps from bucket."""
        cutoff = time.time() - window_seconds
        # Remove timestamps older than the window
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)

    async def check_rate_limit(self, key: str) -> tuple[bool, dict[str, Any]]:
        """Check if request is allowed under rate limits.

        Returns:
            Tuple of (allowed, headers) where headers contains rate limit info

        """
        async with self._lock:
            current_time = time.time()

            # Clean up old entries
            self._clean_bucket(self._minute_buckets[key], 60)
            self._clean_bucket(self._hour_buckets[key], 3600)

            minute_count = len(self._minute_buckets[key])
            hour_count = len(self._hour_buckets[key])

            # Check limits
            if minute_count >= self.requests_per_minute:
                reset_time = int(self._minute_buckets[key][0] + 60)
                return False, {
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(current_time)),
                }

            if hour_count >= self.requests_per_hour:
                reset_time = int(self._hour_buckets[key][0] + 3600)
                return False, {
                    "X-RateLimit-Limit": str(self.requests_per_hour),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(current_time)),
                }

            # Add current request
            self._minute_buckets[key].append(current_time)
            self._hour_buckets[key].append(current_time)

            # Calculate remaining
            minute_remaining = self.requests_per_minute - minute_count - 1
            hour_remaining = self.requests_per_hour - hour_count - 1

            return True, {
                "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
                "X-RateLimit-Remaining-Minute": str(minute_remaining),
                "X-RateLimit-Limit-Hour": str(self.requests_per_hour),
                "X-RateLimit-Remaining-Hour": str(hour_remaining),
            }


class OpenAIRateLimiter:
    """Specialized rate limiter for OpenAI API calls with token tracking."""

    def __init__(
        self,
        requests_per_minute: int = 50,
        tokens_per_minute: int = 150_000,
        requests_per_day: int = 10_000,
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.requests_per_day = requests_per_day

        self._request_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_day // 24,
        )

        # Token tracking
        self._token_buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._daily_tokens: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def check_request_allowed(
        self,
        key: str,
        estimated_tokens: int = 1000,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if OpenAI request is allowed."""
        # First check request rate limits
        allowed, headers = await self._request_limiter.check_rate_limit(key)
        if not allowed:
            return False, headers

        # Then check token limits
        async with self._lock:
            current_time = time.time()

            # Clean token bucket (1 minute window)
            cutoff = current_time - 60
            self._token_buckets[key] = [
                (ts, tokens) for ts, tokens in self._token_buckets[key] if ts > cutoff
            ]

            # Calculate current token usage
            current_tokens = sum(tokens for _, tokens in self._token_buckets[key])

            if current_tokens + estimated_tokens > self.tokens_per_minute:
                return False, {
                    **headers,
                    "X-RateLimit-Tokens-Limit": str(self.tokens_per_minute),
                    "X-RateLimit-Tokens-Remaining": str(
                        max(0, self.tokens_per_minute - current_tokens),
                    ),
                    "X-RateLimit-Tokens-Reset": str(int(cutoff + 60)),
                }

            # Track token usage
            self._token_buckets[key].append((current_time, estimated_tokens))
            self._daily_tokens[key] += estimated_tokens

            headers.update(
                {
                    "X-RateLimit-Tokens-Used": str(current_tokens + estimated_tokens),
                    "X-RateLimit-Tokens-Daily": str(self._daily_tokens[key]),
                },
            )

            return True, headers

    async def record_actual_tokens(self, key: str, actual_tokens: int) -> None:
        """Update token count with actual usage."""
        async with self._lock:
            if self._token_buckets[key]:
                # Update the last entry with actual tokens
                ts, estimated = self._token_buckets[key][-1]
                self._token_buckets[key][-1] = (ts, actual_tokens)
                # Adjust daily total
                self._daily_tokens[key] += actual_tokens - estimated


# Global rate limiters
general_limiter = RateLimiter(
    requests_per_minute=60,
    requests_per_hour=1000,
)

ai_limiter = OpenAIRateLimiter(
    requests_per_minute=50,
    tokens_per_minute=150_000,
    requests_per_day=10_000,
)


def get_client_key(request: Request) -> str:
    """Extract client identifier from request."""
    # Try to get authenticated user ID through safe access
    try:
        return f"user:{request.state.user_id}"
    except AttributeError:
        pass  # Fall through to IP-based identification

    # Fall back to IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    return f"ip:{ip}"


class RateLimitedRoute(APIRoute):
    """Custom route class that adds rate limiting."""

    def __init__(self, *args: Any, rate_limiter: RateLimiter | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rate_limiter = rate_limiter or general_limiter

    def get_route_handler(self) -> Callable[[Request], Any]:
        original_route_handler = super().get_route_handler()

        async def rate_limited_handler(request: Request) -> Response:
            # Get client key
            client_key = get_client_key(request)

            # Check rate limit
            allowed, headers = await self.rate_limiter.check_rate_limit(client_key)

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers=headers,
                )

            # Call original handler
            response = await original_route_handler(request)

            # Add rate limit headers to response
            for key, value in headers.items():
                response.headers[key] = value

            return response

        return rate_limited_handler


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
) -> Callable[[Any], Any]:
    """Decorator to add rate limiting to specific endpoints."""
    limiter = RateLimiter(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
    )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
            client_key = get_client_key(request)
            allowed, headers = await limiter.check_rate_limit(client_key)

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers=headers,
                )

            # Store headers in request state for later
            request.state.rate_limit_headers = headers

            return await func(request, *args, **kwargs)

        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__

        return wrapper

    return decorator
