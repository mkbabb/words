"""Caching decorators for API calls and computations."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, ParamSpec, TypeVar, cast

from ..utils.logging import get_logger
from .core import get_global_cache
from .models import CacheNamespace
from .protocols import is_request_with_headers, serialize_cache_value

# Modern type parameters using ParamSpec
P = ParamSpec("P")
R = TypeVar("R")

logger = get_logger(__name__)

# Cache namespace mapping - DRY principle
CACHE_NAMESPACE_MAP: dict[str, CacheNamespace] = {
    "api": CacheNamespace.API,
    "search": CacheNamespace.SEARCH,
    "dictionary": CacheNamespace.DICTIONARY,
    "corpus": CacheNamespace.CORPUS,
    "semantic": CacheNamespace.SEMANTIC,
    "scraping": CacheNamespace.SCRAPING,
    "compute": CacheNamespace.SEARCH,  # Map compute to SEARCH for backward compatibility
}


def _efficient_cache_key_parts(
    func: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[Any, ...]:
    """Generate efficient cache key parts avoiding expensive operations."""
    key_parts: list[Any] = [func.__module__, func.__name__, args]

    # Process kwargs efficiently without sorting
    if len(kwargs) <= 3:  # Fast path for simple kwargs (most API calls)
        for key, value in kwargs.items():
            serialized = serialize_cache_value(value)
            key_parts.append((key, serialized))
    else:  # Fallback with sorting only for complex cases
        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            serialized = serialize_cache_value(value)
            key_parts.append((key, serialized))

    return tuple(key_parts)


def _generate_cache_key(key_parts: tuple[Any, ...]) -> str:
    """Generate a stable cache key from parts."""
    return hashlib.sha256(str(key_parts).encode()).hexdigest()


# Global deduplication state (thread-safe via GIL)
_active_calls: dict[str, asyncio.Future[Any]] = {}


def cached_api_call(
    ttl_hours: float = 24.0,
    key_prefix: str = "api",
    ignore_params: list[str] | None = None,
    include_headers: bool = False,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Cache decorator for API calls with proper async handling.

    Args:
        ttl_hours: Cache TTL in hours (default: 24 hours)
        key_prefix: Namespace prefix for cache keys
        ignore_params: List of parameter names to exclude from cache key
        include_headers: Whether to include request headers in cache key

    Returns:
        Decorated async function with preserved parameter types

    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()

            # Handle request headers if FastAPI/HTTP context
            headers = None
            if include_headers:
                request = kwargs.get("request")
                if request and is_request_with_headers(request):
                    # Include select headers that might affect response
                    relevant_headers = {"accept-language", "accept-encoding"}
                    headers = {
                        k: v for k, v in request.headers.items() if k.lower() in relevant_headers
                    }

            # Filter out ignored parameters
            if ignore_params:
                filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ignore_params}
            else:
                filtered_kwargs = kwargs

            # Generate cache key efficiently
            key_parts = _efficient_cache_key_parts(func, args, filtered_kwargs)
            if headers:
                key_parts = (*key_parts, headers)

            cache_key = _generate_cache_key(key_parts)

            # Get unified cache
            cache = await get_global_cache()

            # Map key_prefix to namespace
            namespace = CACHE_NAMESPACE_MAP.get(key_prefix, CacheNamespace.API)

            # Try to get from cache
            cached_result = await cache.get(namespace, cache_key)
            if cached_result is not None:
                logger.debug(
                    f"💨 Cache hit for {func.__name__} (took {(time.time() - start_time) * 1000:.2f}ms)",
                )
                return cast("R", cached_result)

            # Call the actual function
            try:
                result = await func(*args, **kwargs)

                # Cache the result
                await cache.set(
                    namespace,
                    cache_key,
                    result,
                    ttl_override=timedelta(hours=ttl_hours),
                )

                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"✅ Cached result for {func.__name__} (took {elapsed:.2f}ms)")

                return result

            except Exception as e:
                # Don't cache errors, but log them
                elapsed = (time.time() - start_time) * 1000
                logger.warning(f"❌ Error in {func.__name__} after {elapsed:.2f}ms: {e}")
                raise

        return wrapper

    return decorator


def cached_computation_async(
    ttl_hours: float = 168.0,  # 7 days default
    key_prefix: str = "compute",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Cache decorator for async computational functions.

    Optimized for async-only functions with proper type preservation.

    Args:
        ttl_hours: Cache TTL in hours (default: 7 days)
        key_prefix: Namespace prefix for cache keys

    Returns:
        Decorated async function with preserved parameter types

    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Generate cache key
            key_parts = _efficient_cache_key_parts(func, args, kwargs)
            cache_key = _generate_cache_key(key_parts)

            # Get unified cache
            cache = await get_global_cache()

            # Map key_prefix to namespace
            namespace = CACHE_NAMESPACE_MAP.get(key_prefix, CacheNamespace.API)

            # Try to get from cache
            cached_result = await cache.get(namespace, cache_key)
            if cached_result is not None:
                logger.debug(f"💨 Cache hit for async computation {func.__name__}")
                return cast("R", cached_result)

            # Execute the computation
            result = await func(*args, **kwargs)

            # Cache the result
            await cache.set(namespace, cache_key, result, ttl_override=timedelta(hours=ttl_hours))

            logger.debug(f"✅ Cached async computation result for {func.__name__}")
            return result

        return wrapper

    return decorator


def cached_computation_sync(
    ttl_hours: float = 168.0,  # 7 days default
    key_prefix: str = "compute",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Cache decorator for sync computational functions.

    Optimized for sync-only functions with proper type preservation.

    Args:
        ttl_hours: Cache TTL in hours (default: 7 days)
        key_prefix: Namespace prefix for cache keys

    Returns:
        Decorated sync function with preserved parameter types

    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            async def async_runner() -> R:
                # Generate cache key
                key_parts = _efficient_cache_key_parts(func, args, kwargs)
                cache_key = _generate_cache_key(key_parts)

                # Get unified cache
                cache = await get_global_cache()

                # Map key_prefix to namespace
                namespace = CACHE_NAMESPACE_MAP.get(key_prefix, CacheNamespace.API)

                # Try to get from cache
                cached_result = await cache.get(namespace, cache_key)
                if cached_result is not None:
                    logger.debug(f"💨 Cache hit for sync computation {func.__name__}")
                    return cast("R", cached_result)

                # Execute the computation
                result = func(*args, **kwargs)

                # Cache the result
                await cache.set(
                    namespace,
                    cache_key,
                    result,
                    ttl_override=timedelta(hours=ttl_hours),
                )

                logger.debug(f"✅ Cached sync computation result for {func.__name__}")
                return result

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_runner())
            finally:
                loop.close()

        return wrapper

    return decorator


def cached_computation(
    ttl_hours: float = 168.0,  # 7 days default
    key_prefix: str = "compute",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Universal cache decorator for computational functions.

    Auto-detects sync vs async and applies appropriate decorator.
    For better type safety, prefer cached_computation_async or cached_computation_sync.

    Args:
        ttl_hours: Cache TTL in hours (default: 7 days)
        key_prefix: Namespace prefix for cache keys

    Returns:
        Decorated function

    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            return cached_computation_async(ttl_hours, key_prefix)(func)
        return cached_computation_sync(ttl_hours, key_prefix)(func)

    return decorator


def deduplicated(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Decorator to prevent duplicate concurrent calls to the same function.

    If multiple calls are made with the same arguments while one is in progress,
    they will wait for the first call to complete and share the result.

    Args:
        func: Async function to deduplicate

    Returns:
        Decorated async function with preserved types

    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Generate cache key for deduplication
        key_parts = _efficient_cache_key_parts(func, args, kwargs)
        cache_key = _generate_cache_key(key_parts)

        # Check if this call is already in progress
        if cache_key in _active_calls:
            logger.debug(f"🔄 Deduplicating call to {func.__name__} - waiting for existing call")
            # Wait for the existing call to complete
            return await _active_calls[cache_key]

        # Create a future for this call
        future: asyncio.Future[Any] = asyncio.Future()
        _active_calls[cache_key] = future

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Set the result for any waiting calls
            future.set_result(result)
            return result

        except Exception as e:
            # Set the exception for any waiting calls
            future.set_exception(e)
            raise
        finally:
            # Clean up
            await asyncio.sleep(0.01)  # Small delay to ensure waiters get the result
            del _active_calls[cache_key]

    return wrapper


def cached_api_call_with_dedup(
    ttl_hours: float = 24.0,
    key_prefix: str = "api",
    ignore_params: list[str] | None = None,
    include_headers: bool = False,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Combine caching and deduplication for API calls.

    This decorator first checks the cache, then prevents duplicate concurrent
    calls if the cache misses.

    Args:
        ttl_hours: Cache TTL in hours (default: 24 hours)
        key_prefix: Namespace prefix for cache keys
        ignore_params: List of parameter names to exclude from cache key
        include_headers: Whether to include request headers in cache key

    Returns:
        Decorated async function with preserved types

    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.time()

            # Handle request headers if FastAPI/HTTP context
            headers = None
            if include_headers:
                request = kwargs.get("request")
                if request and is_request_with_headers(request):
                    # Include select headers that might affect response
                    relevant_headers = {"accept-language", "accept-encoding"}
                    headers = {
                        k: v for k, v in request.headers.items() if k.lower() in relevant_headers
                    }

            # Filter out ignored parameters
            if ignore_params:
                filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ignore_params}
            else:
                filtered_kwargs = kwargs

            # Generate cache key efficiently
            key_parts = _efficient_cache_key_parts(func, args, filtered_kwargs)
            if headers:
                key_parts = (*key_parts, headers)
            cache_key = _generate_cache_key(key_parts)

            # Check for existing calls first (deduplication)
            if cache_key in _active_calls:
                logger.debug(
                    f"🔄 Deduplicating API call to {func.__name__} - waiting for existing call",
                )
                return cast("R", await _active_calls[cache_key])

            # Create future for deduplication
            future: asyncio.Future[R] = asyncio.Future()
            _active_calls[cache_key] = future

            try:
                # Get unified cache
                cache = await get_global_cache()

                # Map key_prefix to namespace
                namespace = CACHE_NAMESPACE_MAP.get(key_prefix, CacheNamespace.API)

                # Try to get from cache
                cached_result = await cache.get(namespace, cache_key)
                if cached_result is not None:
                    logger.debug(
                        f"💨 Cache hit for {func.__name__} (took {(time.time() - start_time) * 1000:.2f}ms)",
                    )
                    future.set_result(cached_result)
                    return cast("R", cached_result)

                # Call the actual function
                result = await func(*args, **kwargs)

                # Cache the result
                await cache.set(
                    namespace,
                    cache_key,
                    result,
                    ttl_override=timedelta(hours=ttl_hours),
                )

                elapsed = (time.time() - start_time) * 1000
                logger.debug(f"✅ Cached API result for {func.__name__} (took {elapsed:.2f}ms)")

                # Set the result for any waiting calls
                future.set_result(result)
                return result

            except Exception as e:
                # Set the exception for any waiting calls
                future.set_exception(e)

                # Don't cache errors, but log them
                elapsed = (time.time() - start_time) * 1000
                logger.warning(f"❌ Error in {func.__name__} after {elapsed:.2f}ms: {e}")
                raise

            finally:
                # Clean up deduplication state
                await asyncio.sleep(0.01)  # Small delay to ensure waiters get the result
                del _active_calls[cache_key]

        return wrapper

    return decorator
