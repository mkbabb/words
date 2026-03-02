"""HTTP client infrastructure for respectful web scraping.

Provides session-managed HTTP clients with rate limiting integration,
scraping session persistence, and content processing utilities.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..caching.core import get_global_cache
from ..caching.models import CacheNamespace
from ..utils.logging import get_logger
from .rate_limiting import (
    AdaptiveRateLimiter,
    RateLimitConfig,
    RateLimitError,
    ScrapingError,
    UserAgent,
)

logger = get_logger(__name__)


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


__all__ = [
    "ContentProcessor",
    "RespectfulHttpClient",
    "ScrapingSession",
    "SessionManager",
    "respectful_scraper",
]
