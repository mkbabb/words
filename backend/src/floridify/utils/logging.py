"""Logging utilities and decorators for pipeline debugging.

Loguru-based implementation with VSCode click-to-definition support,
performance optimization, and structured logging capabilities.
"""

import asyncio
import functools
import os
import sys
import time
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar, cast

from loguru import logger as loguru_logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Context variable for request correlation
request_context: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})

T = TypeVar("T")

# Configure loguru for VSCode compatibility and performance
_configured = False


def _configure_loguru() -> None:
    """Configure loguru with VSCode-compatible format and performance optimizations."""
    global _configured
    if _configured:
        return

    # Remove default handler
    loguru_logger.remove()

    # Determine if we're in development
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    log_level = os.getenv("LOG_LEVEL", "DEBUG" if is_dev else "INFO")

    # VSCode-compatible console format with clickable file paths
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        '"<cyan>{file.path}</cyan>", line <cyan>{line}</cyan> in <cyan>{function}</cyan>(): '
        "<level>{message}</level>"
    )

    # Add console handler with colors and VSCode support
    loguru_logger.add(
        sys.stderr,
        level=log_level,
        format=console_format,
        colorize=True,
        backtrace=is_dev,
        diagnose=is_dev,
        enqueue=True,  # Non-blocking for performance
    )

    # Add file handler for persistent logs
    loguru_logger.add(
        "logs/floridify.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="50 MB",
        retention="7 days",
        compression="gz",
        enqueue=True,
    )

    # Add error-only file for monitoring
    loguru_logger.add(
        "logs/floridify_errors.log",
        level="ERROR",
        format='{time:YYYY-MM-DD HH:mm:ss} | {level} | "{file.path}", line {line} in {function}(): {message}',
        rotation="10 MB",
        retention="30 days",
        backtrace=True,
        diagnose=is_dev,
        enqueue=True,
    )

    # Add custom SUCCESS level for compatibility
    try:
        loguru_logger.level("SUCCESS", no=25, color="<green><bold>")
    except ValueError:
        # Level already exists
        pass

    _configured = True


# Initialize loguru configuration
_configure_loguru()


class LoggerWrapper:
    """Wrapper around loguru logger to provide compatible API with enhanced features."""

    def __init__(self, name: str):
        self._name = name
        self._logger = loguru_logger.bind(name=name)

    def _with_context(self, **kwargs: Any) -> Any:
        """Add request context to log message."""
        context = request_context.get({})
        return self._logger.bind(**context, **kwargs)

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with context."""
        self._with_context().opt(depth=1).debug(message, *args, **kwargs)

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with context."""
        self._with_context().opt(depth=1).info(message, *args, **kwargs)

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with context."""
        self._with_context().opt(depth=1).warning(message, *args, **kwargs)

    def warn(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Alias for warning (stdlib compatibility)."""
        self._with_context().opt(depth=1).warning(message, *args, **kwargs)

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with context."""
        self._with_context().opt(depth=1).error(message, *args, **kwargs)

    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message with context."""
        self._with_context().opt(depth=1).critical(message, *args, **kwargs)

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log exception message with traceback."""
        self._with_context().opt(depth=1).exception(message, *args, **kwargs)

    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log success message with success prefix (preserved API)."""
        self._with_context().opt(depth=1).log("SUCCESS", f"✅ {message}", *args, **kwargs)

    def bind(self, **kwargs: Any) -> "LoggerWrapper":
        """Create logger with bound context."""
        wrapper = LoggerWrapper(self._name)
        wrapper._logger = self._logger.bind(**kwargs)
        return wrapper


def get_logger(name: str) -> LoggerWrapper:
    """Get a logger instance with the given name.

    Returns a LoggerWrapper that provides the same API as before
    but with loguru backend and enhanced features.
    """
    _configure_loguru()  # Ensure configuration is applied
    return LoggerWrapper(name)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration (preserved API).

    This function is preserved for backward compatibility.
    The actual configuration is handled by _configure_loguru().
    """
    global _configured
    _configured = False  # Force reconfiguration with new level

    # Set environment variable to influence loguru configuration
    os.environ["LOG_LEVEL"] = level.upper()

    # Reconfigure loguru
    _configure_loguru()

    # Log configuration change
    loguru_logger.info(f"Logging configured with level: {level.upper()}")


def log_timing[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to log function execution time with enhanced context."""

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        func_name = f"{func.__module__}.{func.__name__}"

        # Use loguru with function context
        func_logger = loguru_logger.bind(function_name=func_name, execution_type="async")

        func_logger.debug(f"⏱️  Starting {func_name}")
        try:
            result: T = await func(*args, **kwargs)  # type: ignore[misc]
            elapsed = time.perf_counter() - start_time
            func_logger.info(f"✅ {func_name} completed in {elapsed:.2f}s", duration=elapsed)
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            func_logger.error(
                f"❌ {func_name} failed after {elapsed:.2f}s: {e}", duration=elapsed, error=str(e)
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.perf_counter()
        func_name = f"{func.__module__}.{func.__name__}"

        # Use loguru with function context
        func_logger = loguru_logger.bind(function_name=func_name, execution_type="sync")

        func_logger.debug(f"⏱️  Starting {func_name}")
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            func_logger.info(f"✅ {func_name} completed in {elapsed:.2f}s", duration=elapsed)
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            func_logger.error(
                f"❌ {func_name} failed after {elapsed:.2f}s: {e}", duration=elapsed, error=str(e)
            )
            raise

    if asyncio.iscoroutinefunction(func):
        return cast(Callable[..., T], async_wrapper)
    else:
        return cast(Callable[..., T], sync_wrapper)


def log_stage(stage_name: str, emoji: str = "🔄") -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to log pipeline stage transitions with Rich console output."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Use loguru with stage context
            stage_logger = loguru_logger.bind(
                stage=stage_name, stage_emoji=emoji, execution_type="async"
            )

            stage_logger.info(f"{emoji} Entering stage: {stage_name}")
            # Preserve Rich console output
            console.print(
                Panel(
                    Text(f"Stage: {stage_name}", style="bold cyan"),
                    title="Pipeline Stage",
                    border_style="cyan",
                )
            )

            try:
                result: T = await func(*args, **kwargs)  # type: ignore[misc]
                stage_logger.info(f"✅ Stage '{stage_name}' completed successfully")
                return result
            except Exception as e:
                stage_logger.error(f"❌ Stage '{stage_name}' failed: {e}", error=str(e))
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # Use loguru with stage context
            stage_logger = loguru_logger.bind(
                stage=stage_name, stage_emoji=emoji, execution_type="sync"
            )

            stage_logger.info(f"{emoji} Entering stage: {stage_name}")
            # Preserve Rich console output
            console.print(
                Panel(
                    Text(f"Stage: {stage_name}", style="bold cyan"),
                    title="Pipeline Stage",
                    border_style="cyan",
                )
            )

            try:
                result = func(*args, **kwargs)
                stage_logger.info(f"✅ Stage '{stage_name}' completed successfully")
                return result
            except Exception as e:
                stage_logger.error(f"❌ Stage '{stage_name}' failed: {e}", error=str(e))
                raise

        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


def log_metrics(**metrics: Any) -> None:
    """Log structured metrics with enhanced context."""
    metrics_str = " | ".join(f"{k}={v}" for k, v in metrics.items())
    loguru_logger.bind(**metrics).info(f"📊 Metrics: {metrics_str}")


def log_provider_fetch(
    provider_name: str, word: str, success: bool, response_size: int = 0, duration: float = 0.0
) -> None:
    """Log provider fetch attempt details with structured context."""
    status = "✅" if success else "❌"
    loguru_logger.bind(
        provider=provider_name,
        word=word,
        success=success,
        response_size=response_size,
        duration=duration,
    ).debug(
        f"{status} Provider '{provider_name}' for '{word}': "
        f"size={response_size} bytes, duration={duration:.2f}s"
    )


def log_search_method(
    method: str,
    query: str,
    result_count: int,
    duration: float = 0.0,
    scores: list[float] | None = None,
) -> None:
    """Log search method execution details with structured context."""
    score_info = ""
    avg_score = None
    if scores:
        avg_score = sum(scores) / len(scores) if scores else 0
        score_info = f", avg_score={avg_score:.3f}"

    loguru_logger.bind(
        search_method=method,
        query=query,
        result_count=result_count,
        duration=duration,
        avg_score=avg_score,
        scores=scores[:5] if scores else None,  # Log first 5 scores for context
    ).info(
        f"🔍 Search '{method}' for '{query}': "
        f"results={result_count}, duration={duration:.2f}s{score_info}"
    )


def log_ai_synthesis(
    word: str, token_usage: dict[str, int], cluster_count: int, duration: float = 0.0
) -> None:
    """Log AI synthesis details with structured context."""
    loguru_logger.bind(
        word=word,
        cluster_count=cluster_count,
        duration=duration,
        **token_usage,  # Spread token usage metrics
    ).info(
        f"🤖 AI synthesis for '{word}': "
        f"clusters={cluster_count}, tokens={token_usage.get('total_tokens', 0)}, "
        f"duration={duration:.2f}s"
    )


# Additional utility functions for enhanced logging capabilities


def set_request_context(**context: Any) -> None:
    """Set request-scoped context for all subsequent logs.

    Example:
        set_request_context(request_id="req-123", user_id="user-456")
    """
    request_context.set(context)


def clear_request_context() -> None:
    """Clear request-scoped context."""
    request_context.set({})


def get_correlation_logger(correlation_id: str) -> LoggerWrapper:
    """Get a logger with automatic correlation ID binding.

    Example:
        logger = get_correlation_logger("req-123")
        logger.info("Processing request")  # Includes correlation_id in logs
    """
    wrapper = LoggerWrapper("correlation")
    wrapper._logger = loguru_logger.bind(correlation_id=correlation_id)
    return wrapper


def log_performance(operation: str, **metrics: Any) -> None:
    """Log performance metrics with structured data.

    Example:
        log_performance("search", duration=0.123, result_count=42, cache_hit=True)
    """
    loguru_logger.bind(operation=operation, **metrics).info(
        f"⚡ Performance: {operation}", **metrics
    )


# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
