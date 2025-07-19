"""Logging utilities and decorators for pipeline debugging."""

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
logger = logging.getLogger(__name__)

T = TypeVar('T')


class LoggerWrapper:
    """Wrapper around logging.Logger to add success method."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        
    def __getattr__(self, name: str) -> Any:
        """Delegate to underlying logger."""
        return getattr(self._logger, name)
    
    def success(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log success message at INFO level with success prefix."""
        self._logger.info(f"✅ {message}", *args, **kwargs)


def get_logger(name: str) -> LoggerWrapper:
    """Get a logger instance with the given name."""
    return LoggerWrapper(logging.getLogger(name))


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def log_timing(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to log function execution time."""
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__name__}"
        
        logger.debug(f"⏱️  Starting {func_name}")
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"✅ {func_name} completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {func_name} failed after {elapsed:.2f}s: {e}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> T:
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__name__}"
        
        logger.debug(f"⏱️  Starting {func_name}")
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"✅ {func_name} completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ {func_name} failed after {elapsed:.2f}s: {e}")
            raise
    
    if asyncio.iscoroutinefunction(func):
        return cast(Callable[..., T], async_wrapper)
    else:
        return cast(Callable[..., T], sync_wrapper)


def log_stage(stage_name: str, emoji: str = "🔄") -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to log pipeline stage transitions."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            logger.info(f"{emoji} Entering stage: {stage_name}")
            console.print(Panel(
                Text(f"Stage: {stage_name}", style="bold cyan"),
                title="Pipeline Stage",
                border_style="cyan"
            ))
            
            try:
                result = await func(*args, **kwargs)
                logger.info(f"✅ Stage '{stage_name}' completed successfully")
                return result
            except Exception as e:
                logger.error(f"❌ Stage '{stage_name}' failed: {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            logger.info(f"{emoji} Entering stage: {stage_name}")
            console.print(Panel(
                Text(f"Stage: {stage_name}", style="bold cyan"),
                title="Pipeline Stage",
                border_style="cyan"
            ))
            
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ Stage '{stage_name}' completed successfully")
                return result
            except Exception as e:
                logger.error(f"❌ Stage '{stage_name}' failed: {e}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)
    
    return decorator


def log_metrics(**metrics: Any) -> None:
    """Log structured metrics for easy parsing."""
    metrics_str = " | ".join(f"{k}={v}" for k, v in metrics.items())
    logger.info(f"📊 Metrics: {metrics_str}")


def log_provider_fetch(provider_name: str, word: str, success: bool, 
                      response_size: int = 0, duration: float = 0.0) -> None:
    """Log provider fetch attempt details."""
    status = "✅" if success else "❌"
    logger.debug(
        f"{status} Provider '{provider_name}' for '{word}': "
        f"size={response_size} bytes, duration={duration:.2f}s"
    )


def log_search_method(method: str, query: str, result_count: int, 
                     duration: float = 0.0, scores: list[float] | None = None) -> None:
    """Log search method execution details."""
    score_info = ""
    if scores:
        avg_score = sum(scores) / len(scores) if scores else 0
        score_info = f", avg_score={avg_score:.3f}"
    
    logger.info(
        f"🔍 Search '{method}' for '{query}': "
        f"results={result_count}, duration={duration:.2f}s{score_info}"
    )


def log_ai_synthesis(word: str, token_usage: dict[str, int], 
                    cluster_count: int, duration: float = 0.0) -> None:
    """Log AI synthesis details."""
    logger.info(
        f"🤖 AI synthesis for '{word}': "
        f"clusters={cluster_count}, tokens={token_usage.get('total_tokens', 0)}, "
        f"duration={duration:.2f}s"
    )


