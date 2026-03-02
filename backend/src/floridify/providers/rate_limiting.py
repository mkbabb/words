"""Rate limiting, circuit breakers, and scraping exceptions.

Provides adaptive rate limiting with exponential backoff, circuit breaker
pattern for fault tolerance, and scraping-related exception types.
"""

from __future__ import annotations

import asyncio
import random
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""


class RateLimitError(ScrapingError):
    """Raised when rate limiting is encountered."""


class ContentError(ScrapingError):
    """Raised when content cannot be parsed or is invalid."""


class UserAgent(str, Enum):
    """Realistic user agents for respectful scraping."""

    CHROME_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    FIREFOX_MAC = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0"
    )
    SAFARI_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
    CHROME_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    FIREFOX_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
    EDGE_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.144"


class RateLimitConfig(BaseModel):
    """Configuration for adaptive rate limiting."""

    base_requests_per_second: float = Field(default=2.0, ge=0.1, le=100.0, description="Base RPS")
    min_delay: float = Field(default=0.5, ge=0.0, description="Minimum delay between requests")
    max_delay: float = Field(default=10.0, ge=1.0, description="Maximum delay for backoff")
    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Exponential backoff multiplier",
    )
    success_speedup: float = Field(
        default=1.1,
        ge=1.0,
        description="Rate increase after successful requests",
    )
    success_threshold: int = Field(default=10, ge=1, description="Successes needed before speedup")
    max_consecutive_errors: int = Field(default=5, ge=1, description="Stop after this many errors")
    respect_retry_after: bool = Field(default=True, description="Honor server Retry-After headers")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for provider fault tolerance.

    After `failure_threshold` consecutive errors, the circuit opens and all
    requests are rejected for `recovery_timeout` seconds. After that, one
    request is allowed through (half-open). If it succeeds, the circuit
    closes; if it fails, the circuit re-opens.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.success_count = 0
        self.total_requests = 0
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check if request is allowed through the circuit."""
        async with self._lock:
            self.total_requests += 1

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                import time

                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN (testing recovery)")
                    return True
                return False

            # HALF_OPEN: allow one request through
            return True

    async def record_success(self) -> None:
        """Record a successful request."""
        async with self._lock:
            self.success_count += 1
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED (recovered)")
            else:
                self.failure_count = 0

    async def record_failure(self) -> None:
        """Record a failed request."""
        import time

        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN (still failing)")
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit {self.name}: CLOSED -> OPEN "
                    f"(after {self.failure_count} consecutive failures)"
                )

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# Global circuit breakers keyed by provider name
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider_name: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a provider."""
    if provider_name not in _circuit_breakers:
        _circuit_breakers[provider_name] = CircuitBreaker(name=provider_name)
    return _circuit_breakers[provider_name]


def get_all_circuit_statuses() -> list[dict[str, Any]]:
    """Get status of all circuit breakers for monitoring."""
    return [cb.get_status() for cb in _circuit_breakers.values()]


MAX_RETRY_AFTER = 3600  # Cap server-specified retry delays to 1 hour


class AdaptiveRateLimiter:
    """Adaptive rate limiter with backoff and server respect."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.current_rps = config.base_requests_per_second
        self.last_request_time = 0.0
        self.consecutive_successes = 0
        self.consecutive_errors = 0
        self.backoff_until = 0.0

    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        now = asyncio.get_running_loop().time()

        # Check if we're in backoff period
        if now < self.backoff_until:
            sleep_time = self.backoff_until - now
            logger.debug(f"⏸️ Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        # Calculate delay based on current rate
        min_interval = 1.0 / self.current_rps
        time_since_last = now - self.last_request_time

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            # Add small jitter to avoid thundering herd
            sleep_time += random.uniform(0.1, 0.3)
            await asyncio.sleep(sleep_time)

        self.last_request_time = asyncio.get_running_loop().time()

    def record_success(self) -> None:
        """Record a successful request."""
        self.consecutive_successes += 1
        self.consecutive_errors = 0

        # Speed up after successful requests
        if (
            self.consecutive_successes >= self.config.success_threshold
            and self.current_rps < self.config.base_requests_per_second * 2
        ):
            self.current_rps *= self.config.success_speedup
            self.consecutive_successes = 0
            logger.debug(f"📈 Rate increased to {self.current_rps:.2f} RPS")

    def record_error(self, retry_after: float | None = None) -> None:
        """Record a failed request and apply backoff."""
        self.consecutive_errors += 1
        self.consecutive_successes = 0

        if retry_after and self.config.respect_retry_after:
            # Cap server-specified retry delay
            if retry_after > MAX_RETRY_AFTER:
                logger.warning(
                    f"⚠️ Server Retry-After {retry_after}s exceeds max, capping to {MAX_RETRY_AFTER}s"
                )
                retry_after = MAX_RETRY_AFTER
            self.backoff_until = asyncio.get_running_loop().time() + retry_after
            logger.info(f"⏸️ Server requested {retry_after}s delay")
        else:
            # Apply exponential backoff
            backoff_delay = min(
                self.config.min_delay * (self.config.backoff_multiplier**self.consecutive_errors),
                self.config.max_delay,
            )
            self.backoff_until = asyncio.get_running_loop().time() + backoff_delay
            logger.warning(f"⚠️ Error backoff: {backoff_delay:.2f}s")

        # Reduce rate on errors
        self.current_rps = max(
            self.current_rps / self.config.backoff_multiplier,
            self.config.base_requests_per_second / 4,  # Don't go too slow
        )

        if self.consecutive_errors >= self.config.max_consecutive_errors:
            raise RateLimitError(f"Too many consecutive errors: {self.consecutive_errors}")


__all__ = [
    "AdaptiveRateLimiter",
    "CircuitBreaker",
    "CircuitState",
    "ContentError",
    "MAX_RETRY_AFTER",
    "RateLimitConfig",
    "RateLimitError",
    "ScrapingError",
    "UserAgent",
    "get_all_circuit_statuses",
    "get_circuit_breaker",
]
