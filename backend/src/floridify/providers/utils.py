"""Core scraping utilities and patterns for respectful web scraping.

This module provides reusable scraping infrastructure used across all Floridify
connectors, ensuring consistent rate limiting, error handling, and respectful
web scraping practices.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..caching.core import get_global_cache
from ..caching.models import CacheNamespace
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


class ScrapingSession(BaseModel):
    """Manages scraping session state with resume capability and caching."""

    session_id: str = Field(..., description="Unique session identifier")
    source: str = Field(..., description="Source name (e.g., 'gutenberg', 'internet_archive')")
    total_items: int = Field(..., description="Total items to process")
    processed_items: int = Field(default=0, description="Items processed successfully")
    failed_items: int = Field(default=0, description="Items that failed processing")
    start_time: datetime = Field(default_factory=datetime.now, description="Session start time")
    last_checkpoint: datetime = Field(
        default_factory=datetime.now,
        description="Last checkpoint time",
    )
    errors: list[str] = Field(default_factory=list, description="List of error messages")
    cache_namespace: str = Field(default="scraping", description="Cache namespace for this session")

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.processed_items == 0:
            return 0.0
        return (self.processed_items - self.failed_items) / self.processed_items * 100

    @property
    def items_per_second(self) -> float:
        """Calculate processing rate."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.processed_items / elapsed

    @property
    def eta_seconds(self) -> float | None:
        """Estimate time to completion."""
        rate = self.items_per_second
        if rate == 0:
            return None
        remaining = self.total_items - self.processed_items
        return remaining / rate


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
            # Use server-specified retry delay
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


class RespectfulHttpClient:
    """HTTP client with respectful scraping practices."""

    def __init__(
        self,
        rate_limiter: AdaptiveRateLimiter,
        timeout: float = 30.0,
        max_connections: int = 5,
        user_agent: str | None = None,
    ):
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self.max_connections = max_connections
        self.user_agent = user_agent or random.choice(list(UserAgent)).value
        self._session: httpx.AsyncClient | None = None

    async def __aenter__(self) -> RespectfulHttpClient:
        """Async context manager entry."""
        limits = httpx.Limits(
            max_connections=max(20, self.max_connections),  # Min 20 connections
            max_keepalive_connections=max(10, self.max_connections // 2),  # Min 10 keepalive
            keepalive_expiry=30.0,  # 30s keepalive window
        )

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        self._session = httpx.AsyncClient(
            http2=True,  # Enable HTTP/2 for multiplexing
            timeout=self.timeout,
            limits=limits,
            headers=headers,
            follow_redirects=True,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a respectful GET request."""
        if not self._session:
            raise ValueError("Client must be used as async context manager")

        await self.rate_limiter.acquire()

        try:
            response = await self._session.get(url, **kwargs)

            if response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("Retry-After")
                retry_delay = float(retry_after) if retry_after else None
                self.rate_limiter.record_error(retry_delay)
                raise RateLimitError(f"Rate limited: {response.status_code}")
            if response.status_code >= 500:
                # Server error
                self.rate_limiter.record_error()
                raise ScrapingError(f"Server error: {response.status_code}")
            if response.status_code >= 400:
                # Client error
                raise ScrapingError(f"Client error: {response.status_code}")
            # Success
            self.rate_limiter.record_success()
            return response

        except httpx.RequestError as e:
            self.rate_limiter.record_error()
            raise ScrapingError(f"Request failed: {e}") from e


class SessionManager:
    """Manages scraping session persistence and recovery using global cache."""

    def __init__(self) -> None:
        """Initialize session manager with global cache integration."""
        self._cache: Any = None  # Will be initialized on first use

    async def _get_cache(self) -> Any:
        """Get global cache instance."""
        if self._cache is None:
            self._cache = await get_global_cache()
        return self._cache

    def _get_cache_key(self, session_id: str) -> str:
        """Generate cache key for session."""
        safe_id = hashlib.md5(session_id.encode()).hexdigest()
        return f"session_{safe_id}"

    async def save_session(self, session: ScrapingSession) -> None:
        """Save session state to global cache."""

        cache = await self._get_cache()
        cache_key = self._get_cache_key(session.session_id)

        # Keep only last 50 errors for storage efficiency
        session_data = session.model_copy(update={"errors": session.errors[-50:]})

        # Save to cache with 24-hour TTL
        await cache.set(
            namespace=CacheNamespace.SCRAPING,
            key=cache_key,
            value=session_data.model_dump(mode="json"),
            ttl_override=timedelta(hours=24),
        )

        logger.debug(f"💾 Saved session {session.session_id} to cache")

    async def load_session(self, session_id: str) -> ScrapingSession | None:
        """Load session state from global cache."""

        cache = await self._get_cache()
        cache_key = self._get_cache_key(session_id)

        # Try to get from cache
        session_data = await cache.get(namespace=CacheNamespace.SCRAPING, key=cache_key)

        if session_data is None:
            return None

        try:
            # Reconstruct ScrapingSession from cached data
            session = ScrapingSession(**session_data)

            logger.info(
                f"📋 Loaded session {session_id} ({session.processed_items}/{session.total_items})",
            )
            return session

        except Exception as e:
            logger.error(f"❌ Failed to load session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> None:
        """Delete session from cache."""

        cache = await self._get_cache()
        cache_key = self._get_cache_key(session_id)

        deleted = await cache.delete(CacheNamespace.SCRAPING, cache_key)
        if deleted:
            logger.debug(f"🗑️ Deleted session {session_id}")


@asynccontextmanager
async def respectful_scraper(
    source: str,
    rate_config: RateLimitConfig | None = None,
    **client_kwargs: Any,
) -> AsyncGenerator[RespectfulHttpClient]:
    """Context manager for respectful scraping sessions."""
    rate_config = rate_config or RateLimitConfig(base_requests_per_second=2.0)
    rate_limiter = AdaptiveRateLimiter(rate_config)

    logger.info(f"🌐 Starting respectful scraping session for {source}")

    async with RespectfulHttpClient(rate_limiter, **client_kwargs) as client:
        try:
            yield client
            logger.info(f"✅ Completed scraping session for {source}")
        except Exception as e:
            logger.error(f"❌ Scraping session failed for {source}: {e}")
            raise


class ContentProcessor:
    """Utilities for processing scraped content."""

    @staticmethod
    def clean_html(html: str) -> str:
        """Clean HTML content to plain text."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

        # Get text and clean whitespace
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        return text

    @staticmethod
    def extract_metadata(html: str) -> dict[str, Any]:
        """Extract metadata from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        metadata = {}

        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            if name and meta.get("content"):
                metadata[name] = meta.get("content")

        return metadata

    @staticmethod
    def validate_text_content(text: str, min_length: int = 100) -> bool:
        """Validate that text content meets quality standards."""
        if not text or len(text.strip()) < min_length:
            return False

        # Check for reasonable character distribution
        printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)
        if printable_ratio < 0.8:
            return False

        return True
