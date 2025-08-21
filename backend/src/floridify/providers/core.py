"""Base connector class for all providers.

Provides common functionality for rate limiting, version management,
and caching integration with RespectfulHttpClient support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, Field

from ..core.state_tracker import StateTracker
from ..models.versioned import VersionConfig
from ..utils.logging import get_logger
from .utils import AdaptiveRateLimiter, RateLimitConfig, RespectfulHttpClient

logger = get_logger(__name__)

T = TypeVar("T")


class ProviderType(str, Enum):
    """Provider type enumeration."""

    DICTIONARY = "dictionary"
    LANGUAGE = "language"
    LITERATURE = "literature"
    SYNTHESIS = "synthesis"


class RateLimitPresets(Enum):
    """Pre-configured rate limit settings for different provider types."""

    # API providers - more aggressive rate limits
    API_FAST = RateLimitConfig(
        base_requests_per_second=10.0,
        min_delay=0.1,
        max_delay=5.0,
        backoff_multiplier=1.5,
        success_speedup=1.2,
        success_threshold=5,
    )

    API_STANDARD = RateLimitConfig(
        base_requests_per_second=5.0,
        min_delay=0.2,
        max_delay=10.0,
        backoff_multiplier=2.0,
        success_speedup=1.1,
        success_threshold=10,
    )

    API_CONSERVATIVE = RateLimitConfig(
        base_requests_per_second=2.0,
        min_delay=0.5,
        max_delay=30.0,
        backoff_multiplier=2.5,
        success_speedup=1.05,
        success_threshold=20,
    )

    # Scraper providers - respectful rate limits
    SCRAPER_RESPECTFUL = RateLimitConfig(
        base_requests_per_second=1.0,
        min_delay=1.0,
        max_delay=60.0,
        backoff_multiplier=3.0,
        success_speedup=1.0,  # No speedup for scrapers
        success_threshold=50,
        respect_retry_after=True,
    )

    SCRAPER_AGGRESSIVE = RateLimitConfig(
        base_requests_per_second=2.0,
        min_delay=0.5,
        max_delay=30.0,
        backoff_multiplier=2.0,
        success_speedup=1.05,
        success_threshold=25,
        respect_retry_after=True,
    )

    # Literature/bulk download - very conservative
    BULK_DOWNLOAD = RateLimitConfig(
        base_requests_per_second=0.5,
        min_delay=2.0,
        max_delay=120.0,
        backoff_multiplier=4.0,
        success_speedup=1.0,  # No speedup for bulk
        success_threshold=100,
        respect_retry_after=True,
    )

    # Local providers - no rate limiting needed
    LOCAL = RateLimitConfig(
        base_requests_per_second=100.0,  # Maximum allowed by constraint
        min_delay=0.0,
        max_delay=1.0,  # Minimum allowed by constraint
        backoff_multiplier=1.0,
        success_speedup=1.0,
        success_threshold=1,
    )


class ConnectorConfig(BaseModel):
    """Configuration for connectors with integrated rate limiting."""

    # Rate limiting configuration as sub-model
    rate_limit_config: RateLimitConfig = Field(
        default_factory=RateLimitConfig, description="Rate limiting configuration"
    )

    # Connection configuration
    timeout: float = Field(default=30.0, ge=1.0, le=300.0, description="Request timeout in seconds")
    max_connections: int = Field(default=5, ge=1, le=50, description="Max concurrent connections")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")

    # Cache configuration
    use_cache: bool = Field(default=True, description="Use caching")
    force_refresh: bool = Field(default=False, description="Force refresh cached data")
    default_ttl: timedelta = Field(default=timedelta(days=7), description="Default cache TTL")

    # Storage configuration
    save_versioned: bool = Field(default=True, description="Save versioned data")


class BaseConnector(ABC):
    """Abstract base class for all connectors.

    Provides standard interface with RespectfulHttpClient integration:
    - get: Retrieve from storage
    - save: Save to storage
    - fetch: Fetch from provider and optionally save
    - get_or_fetch: Get existing or fetch new
    """

    def __init__(
        self,
        provider_type: ProviderType,
        config: ConnectorConfig | None = None,
    ):
        self.provider_type = provider_type
        self.config = config or ConnectorConfig()
        self.provider_version = "1.0.0"

        # Initialize rate limiter
        self.rate_limiter = AdaptiveRateLimiter(self.config.rate_limit_config)

        # Sessions will be created on demand
        self._scraper_session: RespectfulHttpClient | None = None
        self._api_session: httpx.AsyncClient | None = None

    async def get_scraper_session(self) -> RespectfulHttpClient:
        """Get or create scraper session with rate limiting.

        Used for web scraping (WordHippo, Wiktionary scraper, etc.)
        """
        if self._scraper_session is None:
            self._scraper_session = RespectfulHttpClient(
                rate_limiter=self.rate_limiter,
                timeout=self.config.timeout,
                max_connections=self.config.max_connections,
            )
        return self._scraper_session

    async def get_api_session(self) -> httpx.AsyncClient:
        """Get or create API session.

        Used for API calls (Merriam-Webster, Oxford, etc.)
        """
        if self._api_session is None:
            self._api_session = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_connections=self.config.max_connections,
                    max_keepalive_connections=self.config.max_connections,
                ),
            )
        return self._api_session

    async def close(self) -> None:
        """Close all sessions."""
        # Note: RespectfulHttpClient doesn't have a close method
        # It's designed to be used as a context manager
        # We'll just close the API session
        if self._api_session:
            await self._api_session.aclose()
        # Reset scraper session so it gets recreated next time
        self._scraper_session = None

    @abstractmethod
    async def get(
        self,
        word: str,
        config: VersionConfig | None = None,
    ) -> Any | None:
        """Get resource from versioned storage.

        Args:
            word: Word/resource to retrieve
            config: Version configuration

        Returns:
            Resource data or None if not found
        """

    @abstractmethod
    async def save(
        self,
        word: str,
        content: Any,
        config: VersionConfig | None = None,
    ) -> None:
        """Save resource to versioned storage.

        Args:
            word: Word/resource identifier
            content: Content to save
            config: Version configuration
        """

    @abstractmethod
    async def fetch(
        self,
        word: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> Any | None:
        """Fetch resource from provider and optionally save.

        This method should:
        1. Call _fetch_from_provider to get data
        2. If config.save_versioned is True, save the data
        3. Return the fetched data

        Args:
            word: Word/resource to fetch
            config: Version configuration
            state_tracker: Optional state tracker for progress updates

        Returns:
            Fetched data or None
        """

    @abstractmethod
    async def _fetch_from_provider(
        self,
        query: str,
        state_tracker: StateTracker | None = None,
    ) -> Any | None:
        """Implementation-specific fetch method.

        Must be implemented by subclasses to fetch from actual provider.

        Args:
            query: Query/resource identifier
            state_tracker: Optional state tracker for progress updates

        Returns:
            Fetched data or None
        """

    async def get_or_fetch(
        self,
        word: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> Any | None:
        """Get existing resource or fetch from provider.

        Args:
            word: Word/resource identifier
            config: Version configuration
            state_tracker: Optional state tracker for progress updates

        Returns:
            Resource data or None
        """
        config = config or VersionConfig()

        # Try to get existing unless forced refresh
        if not config.force_rebuild:
            existing = await self.get(word, config)
            if existing:
                logger.debug(f"Found existing entry for '{word}'")
                return existing

        # Fetch from provider (will save if configured)
        return await self.fetch(word, config, state_tracker)

    async def __aenter__(self) -> BaseConnector:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()
