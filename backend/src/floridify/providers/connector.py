"""Base connector class for all providers.

Provides common functionality for rate limiting, version management,
and caching integration.
"""

from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from ..caching.unified import get_unified
from ..core.state_tracker import StateTracker
from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ConnectorConfig(BaseModel):
    """Configuration for connectors."""

    rate_limit: float = Field(default=1.0, ge=0.1, le=100.0, description="Requests per second")
    force_refresh: bool = Field(default=False, description="Force refresh cached data")
    save_versioned: bool = Field(default=True, description="Save versioned data")
    use_cache: bool = Field(default=True, description="Use caching")
    timeout: float = Field(default=30.0, ge=1.0, le=300.0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    default_ttl: timedelta = Field(default=timedelta(days=7), description="Default cache TTL")


class BaseConnector(ABC):
    """Abstract base class for all connectors."""

    def __init__(
        self,
        provider_type: str,
        provider_name: str,
        config: ConnectorConfig | None = None,
    ):
        self.provider_type = provider_type
        self.provider_name = provider_name
        self.config = config or ConnectorConfig()
        self.provider_version = "1.0.0"

        # Rate limiting
        self._last_request_time = 0.0
        self._request_interval = 1.0 / self.config.rate_limit

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._request_interval:
            sleep_time = self._request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)

        self._last_request_time = asyncio.get_event_loop().time()

    def compute_hash(self, content: Any) -> str:
        """Compute hash of content for deduplication."""
        if isinstance(content, str):
            data = content.encode()
        elif isinstance(content, dict):
            import json

            data = json.dumps(content, sort_keys=True).encode()
        else:
            data = str(content).encode()

        return hashlib.sha256(data).hexdigest()

    async def get_from_cache(
        self,
        cache_key: str,
        namespace: str | None = None,
    ) -> Any | None:
        """Get data from unified cache."""
        if not self.config.use_cache:
            return None

        try:
            cache = await get_unified()
            namespace = namespace or f"{self.provider_type}_{self.provider_name}"
            return await cache.get(namespace, cache_key)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
            return None

    async def set_in_cache(
        self,
        cache_key: str,
        value: Any,
        use_ttl: bool = True,
        namespace: str | None = None,
    ) -> None:
        """Set data in unified cache."""
        if not self.config.use_cache:
            return

        try:
            cache = await get_unified()
            namespace = namespace or f"{self.provider_type}_{self.provider_name}"
            ttl = self.config.default_ttl if use_ttl else None
            await cache.set(namespace, cache_key, value, ttl=ttl)
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    @abstractmethod
    async def fetch(
        self,
        resource_id: str,
        state_tracker: StateTracker | None = None,
        **kwargs: Any,
    ) -> Any | None:
        """Fetch resource from provider.

        Must be implemented by subclasses.
        """
