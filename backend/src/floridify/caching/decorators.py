"""Caching decorators for API calls and computations."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import HTTPException

from ..utils.logging import get_logger
from .cache_manager import get_cache_manager

F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])

logger = get_logger(__name__)


class RequestDeduplicator:
    """Manages in-flight requests to prevent duplicate executions."""

    def __init__(
        self, max_wait_time: float = 120.0, cleanup_interval: float = 60.0
    ):  # Default 2 minutes
        self._in_flight: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()
        self._max_wait_time = max_wait_time
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    async def deduplicate(
        self,
        key: str,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with deduplication."""
        async with self._lock:
            # Check if request is already in flight
            if key in self._in_flight:
                future = self._in_flight[key]
                logger.info(f"🔄 Deduplicating request: {key}")
            else:
                # Create new future for this request
                future = asyncio.Future()
                self._in_flight[key] = future
                logger.info(f"🚀 Starting new request: {key}")

                # Schedule the actual execution
                asyncio.create_task(self._execute(key, future, func, *args, **kwargs))

            # Cleanup old entries periodically
            await self._cleanup_stale_entries()

        # Wait for result with timeout
        try:
            return await asyncio.wait_for(future, timeout=self._max_wait_time)
        except TimeoutError:
            logger.warning(f"⏱️ Timeout waiting for request: {key}")
            raise HTTPException(status_code=504, detail="Request timeout")

    async def _execute(
        self,
        key: str,
        future: asyncio.Future[Any],
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Execute the actual function and set the future result."""
        try:
            result = await func(*args, **kwargs)
            future.set_result(result)
            logger.info(f"✅ Request completed: {key}")
        except Exception as e:
            future.set_exception(e)
            logger.error(f"❌ Request failed: {key} - {e}")
        finally:
            # Remove from in-flight after a short delay
            await asyncio.sleep(0.1)
            async with self._lock:
                self._in_flight.pop(key, None)

    async def _cleanup_stale_entries(self) -> None:
        """Remove completed futures that weren't cleaned up."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = current_time
        stale_keys = [key for key, future in self._in_flight.items() if future.done()]

        for key in stale_keys:
            self._in_flight.pop(key, None)
            logger.debug(f"🧹 Cleaned up stale request: {key}")


# Global deduplicator instance with increased timeout
_deduplicator = RequestDeduplicator(max_wait_time=120.0)  # 2 minutes default


def cached_api_call(
    ttl_hours: float | None = None,
    use_file_cache: bool = False,
    key_func: Callable[..., tuple[Any, ...]] | None = None,
    force_refresh_param: str = "force_refresh",
) -> Callable[[AF], AF]:
    """Decorator for caching API calls with TTL.

    Args:
        ttl_hours: Cache TTL in hours (uses default if None)
        use_file_cache: Whether to persist cache to disk
        key_func: Custom function to generate cache key from args/kwargs
        force_refresh_param: Parameter name to check for cache invalidation

    Returns:
        Decorated async function
    """

    def decorator(func: AF) -> AF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = get_cache_manager()

            # Check for force refresh parameter (don't pop yet)
            force_refresh = kwargs.get(force_refresh_param, False)

            # Generate cache key (needs access to force_refresh)
            if key_func:
                key_parts = key_func(*args, **kwargs)
            else:
                # Default key generation: function name + args + sorted kwargs
                key_parts = (
                    func.__module__,
                    func.__name__,
                    args,
                    tuple(sorted(kwargs.items())),
                )

            # Check cache first (unless forcing refresh)
            if not force_refresh:
                cached_result = cache_manager.get(
                    key_parts,
                    use_file_cache=use_file_cache,
                )
                if cached_result is not None:
                    logger.debug(f"🎯 Cache hit: {func.__name__}")
                    return cached_result

            # Execute function and cache result
            logger.debug(f"🔄 Executing: {func.__name__}")
            result = await func(*args, **kwargs)

            # Cache the result
            cache_manager.set(
                key_parts,
                result,
                ttl_hours=ttl_hours,
                use_file_cache=use_file_cache,
            )

            return result

        return wrapper  # type: ignore[return-value]

    return decorator


def cached_computation(
    ttl_hours: float | None = None,
    use_file_cache: bool = True,  # Computations typically benefit from disk cache
    key_func: Callable[..., tuple[Any, ...]] | None = None,
    force_refresh_param: str = "force_rebuild",
) -> Callable[[F], F]:
    """Decorator for caching expensive computations.

    Args:
        ttl_hours: Cache TTL in hours (uses default if None)
        use_file_cache: Whether to persist cache to disk
        key_func: Custom function to generate cache key from args/kwargs
        force_refresh_param: Parameter name to check for cache invalidation

    Returns:
        Decorated function (sync or async)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = get_cache_manager()

            # Check for force refresh parameter (don't pop yet)
            force_refresh = kwargs.get(force_refresh_param, False)

            # Generate cache key
            if key_func:
                key_parts = key_func(*args, **kwargs)
            else:
                # Default key generation: function name + args + sorted kwargs
                key_parts = (
                    func.__module__,
                    func.__name__,
                    args,
                    tuple(sorted(kwargs.items())),
                )

            # Check cache first (unless forcing refresh)
            if not force_refresh:
                cached_result = cache_manager.get(
                    key_parts,
                    use_file_cache=use_file_cache,
                )
                if cached_result is not None:
                    logger.debug(f"🎯 Cache hit: {func.__name__}")
                    return cached_result

            # Execute function and cache result
            logger.debug(f"🔄 Computing: {func.__name__}")
            result = func(*args, **kwargs)

            # Cache the result
            cache_manager.set(
                key_parts,
                result,
                ttl_hours=ttl_hours,
                use_file_cache=use_file_cache,
            )

            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = get_cache_manager()

            # Check for force refresh parameter (don't pop yet)
            force_refresh = kwargs.get(force_refresh_param, False)

            # Generate cache key
            if key_func:
                key_parts = key_func(*args, **kwargs)
            else:
                # Default key generation: function name + args + sorted kwargs
                key_parts = (
                    func.__module__,
                    func.__name__,
                    args,
                    tuple(sorted(kwargs.items())),
                )

            # Check cache first (unless forcing refresh)
            if not force_refresh:
                cached_result = cache_manager.get(
                    key_parts,
                    use_file_cache=use_file_cache,
                )
                if cached_result is not None:
                    logger.debug(f"🎯 Cache hit: {func.__name__}")
                    return cached_result

            # Execute function and cache result
            logger.debug(f"🔄 Computing: {func.__name__}")
            result = await func(*args, **kwargs)

            # Cache the result
            cache_manager.set(
                key_parts,
                result,
                ttl_hours=ttl_hours,
                use_file_cache=use_file_cache,
            )

            return result

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        else:
            return sync_wrapper  # type: ignore[return-value]

    return decorator


def openai_cache_key(*args: Any, **kwargs: Any) -> tuple[Any, ...]:
    """Generate cache key for OpenAI API calls."""
    # Extract common OpenAI parameters for cache key
    word = kwargs.get("word", args[1] if len(args) > 1 else "unknown")

    # Include prompt hash and model info
    prompt = kwargs.get("prompt", args[0] if args else "")
    prompt_hash = hash(prompt) if prompt else 0

    model = kwargs.get("model", "default")

    return ("openai_api", word, prompt_hash, model)


def http_cache_key(*args: Any, **kwargs: Any) -> tuple[Any, ...]:
    """Generate cache key for HTTP requests."""
    # URL is typically the first argument
    url = args[0] if args else kwargs.get("url", "unknown")

    # Include method and important headers
    method = kwargs.get("method", "GET")
    headers = kwargs.get("headers", {})

    # Create deterministic key from URL and important parameters
    return ("http_request", method, url, tuple(sorted(headers.items())))


def lexicon_cache_key(*args: Any, **kwargs: Any) -> tuple[Any, ...]:
    """Generate cache key for lexicon operations."""
    # Include language and source information
    language = kwargs.get("language", args[0] if args else "unknown")
    source = kwargs.get("source", "default")

    return ("lexicon", language, source)


def deduplicated(
    key_func: Callable[..., str],
    max_wait_time: float | None = None,
) -> Callable[[AF], AF]:
    """Decorator for request deduplication.

    Args:
        key_func: Function to generate deduplication key from arguments
        max_wait_time: Maximum time to wait for in-flight request

    Returns:
        Decorated async function
    """

    def decorator(func: AF) -> AF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate deduplication key
            key = key_func(*args, **kwargs)

            # Use custom wait time if provided
            deduplicator = _deduplicator
            if max_wait_time is not None:
                # Create temporary deduplicator with custom timeout
                deduplicator = RequestDeduplicator(max_wait_time=max_wait_time)

            # Execute with deduplication
            return await deduplicator.deduplicate(key, func, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def cached_api_call_with_dedup(
    ttl_hours: float | None = None,
    use_file_cache: bool = False,
    key_func: Callable[..., tuple[Any, ...]] | None = None,
    force_refresh_param: str = "force_refresh",
    max_wait_time: float = 120.0,  # Default 2 minutes
) -> Callable[[AF], AF]:
    """Decorator combining caching and request deduplication.

    Args:
        ttl_hours: Cache TTL in hours
        use_file_cache: Whether to persist cache to disk
        key_func: Function to generate cache key from args/kwargs
        force_refresh_param: Parameter name for cache invalidation
        max_wait_time: Maximum time to wait for in-flight request

    Returns:
        Decorated async function with both caching and deduplication
    """

    def decorator(func: AF) -> AF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = get_cache_manager()

            # Check for force refresh
            force_refresh = kwargs.get(force_refresh_param, False)

            # Generate cache key
            if key_func:
                key_parts = key_func(*args, **kwargs)
            else:
                key_parts = (
                    func.__module__,
                    func.__name__,
                    args,
                    tuple(sorted(kwargs.items())),
                )

            # Check cache first (unless forcing refresh)
            if not force_refresh:
                cached_result = cache_manager.get(
                    key_parts,
                    use_file_cache=use_file_cache,
                )
                if cached_result is not None:
                    logger.debug(f"🎯 Cache hit: {func.__name__}")
                    return cached_result

            # Create deduplication key
            # Convert key_parts to string for hashing (handles unhashable types)
            key_str = "|".join(str(part) for part in key_parts)
            key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
            dedup_key = f"{func.__module__}:{func.__name__}:{key_hash}"

            # Execute with deduplication
            result = await _deduplicator.deduplicate(
                dedup_key,
                func,
                *args,
                **kwargs,
            )

            # Cache the result
            cache_manager.set(
                key_parts,
                result,
                ttl_hours=ttl_hours,
                use_file_cache=use_file_cache,
            )

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
