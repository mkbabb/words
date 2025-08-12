"""Base connector class for all providers.

Provides common functionality for rate limiting, version management,
and caching integration.
"""

from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from ..caching.unified import get_unified
from ..core.state_tracker import StateTracker
from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ProviderType(str, Enum):
    """Types of providers."""
    
    DICTIONARY = "dictionary"
    LITERATURE = "literature"


@dataclass
class ConnectorConfig:
    """Configuration for connectors."""
    
    rate_limit: float = 1.0  # Requests per second
    force_refresh: bool = False
    save_versioned: bool = True
    use_cache: bool = True
    timeout: float = 30.0
    max_retries: int = 3


class BaseConnector(ABC):
    """Abstract base class for all connectors."""
    
    def __init__(
        self,
        provider_type: ProviderType,
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
        ttl: int | None = None,
        namespace: str | None = None,
    ) -> None:
        """Set data in unified cache."""
        if not self.config.use_cache:
            return
            
        try:
            cache = await get_unified()
            namespace = namespace or f"{self.provider_type}_{self.provider_name}"
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
        pass