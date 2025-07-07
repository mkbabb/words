"""Caching decorators for API calls and computations."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from ..utils.logging import get_logger
from .cache_manager import get_cache_manager

F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])

logger = get_logger(__name__)


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
            
            # Check for force refresh parameter
            force_refresh = kwargs.pop(force_refresh_param, False)
            
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
            
            # Check for force refresh parameter
            force_refresh = kwargs.pop(force_refresh_param, False)
            
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
            
            # Check for force refresh parameter
            force_refresh = kwargs.pop(force_refresh_param, False)
            
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