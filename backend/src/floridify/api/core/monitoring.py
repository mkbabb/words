"""Performance monitoring utilities for API operations."""

import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request, Response

from ...utils.logging import get_logger

logger = get_logger(__name__)


class PerformanceMetrics:
    """Singleton for collecting performance metrics."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize metrics storage."""
        self.request_times = defaultdict(list)
        self.cache_stats = defaultdict(int)
        self.db_query_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.start_time = datetime.utcnow()

    def record_request(self, endpoint: str, duration: float, status_code: int):
        """Record request timing."""
        self.request_times[endpoint].append(
            {
                "duration": duration,
                "status_code": status_code,
                "timestamp": datetime.utcnow(),
            }
        )

        # Keep only last 1000 entries per endpoint
        if len(self.request_times[endpoint]) > 1000:
            self.request_times[endpoint] = self.request_times[endpoint][-1000:]

    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        self.cache_stats[f"{cache_type}_hits"] += 1

    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        self.cache_stats[f"{cache_type}_misses"] += 1

    def record_db_query(self, collection: str, operation: str, duration: float):
        """Record database query timing."""
        key = f"{collection}:{operation}"
        self.db_query_times[key].append(
            {
                "duration": duration,
                "timestamp": datetime.utcnow(),
            }
        )

        # Keep only last 500 entries per query type
        if len(self.db_query_times[key]) > 500:
            self.db_query_times[key] = self.db_query_times[key][-500:]

    def record_error(self, endpoint: str, error_type: str):
        """Record error occurrence."""
        key = f"{endpoint}:{error_type}"
        self.error_counts[key] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get current performance statistics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()

        # Calculate request stats
        request_stats = {}
        for endpoint, times in self.request_times.items():
            if times:
                durations = [t["duration"] for t in times]
                request_stats[endpoint] = {
                    "count": len(times),
                    "avg_ms": sum(durations) / len(durations) * 1000,
                    "min_ms": min(durations) * 1000,
                    "max_ms": max(durations) * 1000,
                    "p95_ms": sorted(durations)[int(len(durations) * 0.95)] * 1000
                    if len(durations) > 20
                    else None,
                }

        # Calculate cache hit rates
        cache_hit_rates = {}
        for cache_type in set(k.split("_")[0] for k in self.cache_stats.keys()):
            hits = self.cache_stats.get(f"{cache_type}_hits", 0)
            misses = self.cache_stats.get(f"{cache_type}_misses", 0)
            total = hits + misses
            cache_hit_rates[cache_type] = {
                "hits": hits,
                "misses": misses,
                "hit_rate": hits / total if total > 0 else 0,
            }

        # Calculate DB query stats
        db_stats = {}
        for query_type, times in self.db_query_times.items():
            if times:
                durations = [t["duration"] for t in times]
                db_stats[query_type] = {
                    "count": len(times),
                    "avg_ms": sum(durations) / len(durations) * 1000,
                    "max_ms": max(durations) * 1000,
                }

        return {
            "uptime_seconds": uptime,
            "request_stats": request_stats,
            "cache_stats": cache_hit_rates,
            "db_stats": db_stats,
            "error_counts": dict(self.error_counts),
        }

    def reset_stats(self):
        """Reset all statistics."""
        self._initialize()


# Global metrics instance
metrics = PerformanceMetrics()


@asynccontextmanager
async def track_request_performance(request: Request, response: Response):
    """Context manager for tracking request performance."""
    start_time = time.time()
    endpoint = f"{request.method} {request.url.path}"

    try:
        yield
    finally:
        duration = time.time() - start_time
        status_code = response.status_code

        # Record metrics
        metrics.record_request(endpoint, duration, status_code)

        # Set response headers
        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"

        # Log slow requests
        if duration > 1.0:
            logger.warning(f"Slow request: {endpoint} took {duration:.2f}s")


def track_db_operation(collection: str, operation: str):
    """Decorator for tracking database operation performance."""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metrics.record_db_query(collection, operation, duration)

                if duration > 0.1:
                    logger.warning(f"Slow DB query: {collection}.{operation} took {duration:.3f}s")

        return wrapper

    return decorator


class SlowQueryDetector:
    """Utility for detecting and logging slow queries."""

    def __init__(self, threshold_ms: float = 100):
        self.threshold_ms = threshold_ms
        self.slow_queries = []

    @asynccontextmanager
    async def track(self, query_description: str):
        """Track a query execution."""
        start_time = time.time()

        yield

        duration_ms = (time.time() - start_time) * 1000

        if duration_ms > self.threshold_ms:
            query_info = {
                "description": query_description,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow(),
            }

            self.slow_queries.append(query_info)

            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

            logger.warning(f"Slow query detected: {query_description} took {duration_ms:.2f}ms")

    def get_slow_queries(self) -> list[dict[str, Any]]:
        """Get recent slow queries."""
        return self.slow_queries


# Global slow query detector
slow_query_detector = SlowQueryDetector()


class RequestRateLimiter:
    """Simple in-memory rate limiter for API endpoints."""

    def __init__(self):
        self.requests = defaultdict(list)

    async def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is within rate limit."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        # Clean old requests
        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]

        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False

        # Record request
        self.requests[key].append(now)
        return True

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get remaining requests in current window."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        # Count recent requests
        recent = sum(1 for ts in self.requests[key] if ts > cutoff)
        return max(0, max_requests - recent)


# Global rate limiter
rate_limiter = RequestRateLimiter()
