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
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
import httpx
from bs4 import BeautifulSoup

from ..utils.logging import get_logger
from ..utils.paths import get_cache_directory

logger = get_logger(__name__)


class ScrapingError(Exception):
    """Base exception for scraping-related errors."""

    pass


class RateLimitError(ScrapingError):
    """Raised when rate limiting is encountered."""

    pass


class ContentError(ScrapingError):
    """Raised when content cannot be parsed or is invalid."""

    pass


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


@dataclass
class RateLimitConfig:
    """Configuration for adaptive rate limiting."""

    base_requests_per_second: float = 2.0
    min_delay: float = 0.5  # Minimum delay between requests
    max_delay: float = 10.0  # Maximum delay for backoff
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    success_speedup: float = 1.1  # Rate increase after successful requests
    success_threshold: int = 10  # Successes needed before speedup
    max_consecutive_errors: int = 5  # Stop after this many errors
    respect_retry_after: bool = True  # Honor server Retry-After headers


@dataclass
class ScrapingSession:
    """Manages scraping session state with resume capability."""

    session_id: str
    source: str  # e.g., "gutenberg", "internet_archive"
    total_items: int
    processed_items: int = 0
    failed_items: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    last_checkpoint: datetime = field(default_factory=datetime.now)
    errors: list[str] = field(default_factory=list)

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
        now = asyncio.get_event_loop().time()

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

        self.last_request_time = asyncio.get_event_loop().time()

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
            self.backoff_until = asyncio.get_event_loop().time() + retry_after
            logger.info(f"⏸️ Server requested {retry_after}s delay")
        else:
            # Apply exponential backoff
            backoff_delay = min(
                self.config.min_delay * (self.config.backoff_multiplier**self.consecutive_errors),
                self.config.max_delay,
            )
            self.backoff_until = asyncio.get_event_loop().time() + backoff_delay
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

    async def __aenter__(self):
        """Async context manager entry."""
        limits = httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=max(2, self.max_connections // 2),
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
            timeout=self.timeout, limits=limits, headers=headers, follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def get(self, url: str, **kwargs) -> httpx.Response:
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
            elif response.status_code >= 500:
                # Server error
                self.rate_limiter.record_error()
                raise ScrapingError(f"Server error: {response.status_code}")
            elif response.status_code >= 400:
                # Client error
                raise ScrapingError(f"Client error: {response.status_code}")
            else:
                # Success
                self.rate_limiter.record_success()
                return response

        except httpx.RequestError as e:
            self.rate_limiter.record_error()
            raise ScrapingError(f"Request failed: {e}") from e


class SessionManager:
    """Manages scraping session persistence and recovery."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or get_cache_directory("scraping_sessions")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, session_id: str) -> Path:
        """Get file path for session storage."""
        safe_id = hashlib.md5(session_id.encode()).hexdigest()
        return self.cache_dir / f"session_{safe_id}.json"

    async def save_session(self, session: ScrapingSession) -> None:
        """Save session state to disk."""
        session_data = {
            "session_id": session.session_id,
            "source": session.source,
            "total_items": session.total_items,
            "processed_items": session.processed_items,
            "failed_items": session.failed_items,
            "start_time": session.start_time.isoformat(),
            "last_checkpoint": session.last_checkpoint.isoformat(),
            "errors": session.errors[-50:],  # Keep last 50 errors
        }

        session_path = self.get_session_path(session.session_id)

        async with aiofiles.open(session_path, "w") as f:
            import json

            await f.write(json.dumps(session_data, indent=2))

        logger.debug(f"💾 Saved session {session.session_id}")

    async def load_session(self, session_id: str) -> ScrapingSession | None:
        """Load session state from disk."""
        session_path = self.get_session_path(session_id)

        if not session_path.exists():
            return None

        try:
            async with aiofiles.open(session_path) as f:
                import json

                session_data = json.loads(await f.read())

            session = ScrapingSession(
                session_id=session_data["session_id"],
                source=session_data["source"],
                total_items=session_data["total_items"],
                processed_items=session_data["processed_items"],
                failed_items=session_data["failed_items"],
                start_time=datetime.fromisoformat(session_data["start_time"]),
                last_checkpoint=datetime.fromisoformat(session_data["last_checkpoint"]),
                errors=session_data["errors"],
            )

            logger.info(
                f"📋 Loaded session {session_id} ({session.processed_items}/{session.total_items})"
            )
            return session

        except Exception as e:
            logger.error(f"❌ Failed to load session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> None:
        """Delete session file."""
        session_path = self.get_session_path(session_id)
        if session_path.exists():
            session_path.unlink()
            logger.debug(f"🗑️ Deleted session {session_id}")


@asynccontextmanager
async def respectful_scraper(
    source: str, rate_config: RateLimitConfig | None = None, **client_kwargs
) -> AsyncGenerator[RespectfulHttpClient, None]:
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


# Convenience functions for common patterns
async def download_with_retry(
    url: str, max_retries: int = 3, rate_config: RateLimitConfig | None = None
) -> str:
    """Download content with automatic retry on failure."""

    rate_config = rate_config or RateLimitConfig()

    for attempt in range(max_retries + 1):
        try:
            async with respectful_scraper("generic", rate_config) as client:
                response = await client.get(url)
                return response.text

        except Exception as e:
            if attempt == max_retries:
                raise

            wait_time = 2**attempt  # Exponential backoff
            logger.warning(f"⚠️ Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)

    raise ScrapingError("All retry attempts failed")
