"""Base connector class for all providers.

Provides common functionality for rate limiting, version management,
and caching integration with RespectfulHttpClient support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import Any, Self, TypeVar

import httpx
from pydantic import BaseModel, Field

from ..caching.models import CacheNamespace, ResourceType, VersionConfig
from ..core.state_tracker import StateTracker
from ..utils.logging import get_logger
from .utils import AdaptiveRateLimiter, RateLimitConfig

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

    # Rate limiting configuration
    rate_limit_config: RateLimitConfig | None = Field(
        default=None,
        description="Rate limiting configuration",
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        description="User agent for requests",
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
    """Base connector for all data providers."""

    def __init__(
        self,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize base connector with configuration."""
        self.config = config or ConnectorConfig()
        self._scraper_session: httpx.AsyncClient | None = None
        self._api_client: httpx.AsyncClient | None = None

        # Set up rate limiter
        if config and config.rate_limit_config:
            # Use custom configuration
            self.rate_limiter = AdaptiveRateLimiter(config.rate_limit_config)
        else:
            # Use default configuration
            self.rate_limiter = AdaptiveRateLimiter(RateLimitConfig())

    @abstractmethod
    def get_resource_type(self) -> ResourceType:
        """Get the resource type for this connector."""

    @abstractmethod
    def get_cache_namespace(self) -> CacheNamespace:
        """Get the cache namespace for this connector."""

    @abstractmethod
    def model_dump(self, content: Any) -> Any:
        """Prepare content for persistence."""
        if hasattr(content, "model_dump"):
            return content.model_dump(mode="json")  # type: ignore[attr-defined]
        return content

    def model_load(self, content: Any) -> Any:
        """Convert persisted payload back into provider object."""
        return content

    async def get(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
    ) -> Any | None:
        """Get resource from versioned storage."""
        from ..caching.core import get_versioned_content
        from ..caching.manager import get_version_manager

        manager = get_version_manager()
        full_resource_id = f"{resource_id}_{self.get_cache_key_suffix()}"

        result = await manager.get_latest(
            resource_id=full_resource_id,
            resource_type=self.get_resource_type(),
            config=config or VersionConfig(),
        )

        if result:
            payload = await get_versioned_content(result)
            if payload is not None:
                return self.model_load(payload)
        return None

    def get_cache_key_suffix(self) -> str:
        """Suffix used when building cache keys."""
        return self.__class__.__name__

    def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
        """Base metadata for persisted entries."""
        return {"resource_id": resource_id, "resource_type": self.get_resource_type().value}

    async def save(
        self,
        resource_id: str,
        content: Any,
        config: VersionConfig | None = None,
    ) -> None:
        """Save resource to versioned storage."""
        from ..caching.manager import get_version_manager

        manager = get_version_manager()
        full_resource_id = f"{resource_id}_{self.get_cache_key_suffix()}"

        content_to_save = self.model_dump(content)

        await manager.save(
            resource_id=full_resource_id,
            content=content_to_save,
            resource_type=self.get_resource_type(),
            namespace=self.get_cache_namespace(),
            metadata=self.get_metadata_for_resource(resource_id),
            config=config or VersionConfig(),
        )

        logger.info(
            "%s saved %s entry for '%s'",
            self.get_cache_key_suffix(),
            self.get_resource_type().value,
            resource_id,
        )

    @abstractmethod
    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> Any | None:
        """Fetch resource from provider and optionally persist."""

    @abstractmethod
    async def _fetch_from_provider(
        self,
        query: Any,
        state_tracker: StateTracker | None = None,
    ) -> Any | None:
        """Implementation-specific fetch method."""

    async def get_or_fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> Any | None:
        """Get existing resource or fetch from provider."""
        # Try to get from storage first
        result = await self.get(resource_id, config)
        if result:
            return result

        # Fetch from provider if not found
        return await self.fetch(resource_id, config, state_tracker)

    @property
    def scraper_session(self) -> httpx.AsyncClient:
        """Get or create scraper session with HTTP/2 support."""
        if self._scraper_session is None:
            self._scraper_session = httpx.AsyncClient(
                http2=True,  # Enable HTTP/2 for connection reuse
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(
                    max_keepalive_connections=50,  # Increased for parallel ops
                    max_connections=200,  # Increased for burst traffic
                    keepalive_expiry=30.0,  # 30s matches batch operation duration
                ),
                headers={"User-Agent": self.config.user_agent},
            )
        return self._scraper_session

    @property
    def api_client(self) -> httpx.AsyncClient:
        """Get or create API client with HTTP/2 support."""
        if self._api_client is None:
            self._api_client = httpx.AsyncClient(
                http2=True,  # Enable HTTP/2 for connection reuse
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(
                    max_keepalive_connections=50,  # Increased for parallel ops
                    max_connections=200,  # Increased for burst traffic
                    keepalive_expiry=30.0,  # 30s matches batch operation duration
                ),
            )
        return self._api_client

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close all connections."""
        if self._scraper_session:
            await self._scraper_session.aclose()
            self._scraper_session = None
        if self._api_client:
            await self._api_client.aclose()
            self._api_client = None
