"""Dictionary-specific connector base class."""

from __future__ import annotations

from typing import Any

import httpx

from ...caching.manager import get_version_manager
from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.dictionary import DictionaryProvider
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig

logger = get_logger(__name__)


class DictionaryConnector(BaseConnector):
    """Base dictionary connector with versioned storage."""

    def __init__(
        self,
        provider: DictionaryProvider,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize dictionary connector."""
        super().__init__(config or ConnectorConfig())
        self.provider = provider

    def get_resource_type(self) -> ResourceType:
        """Get the resource type for dictionary entries."""
        return ResourceType.DICTIONARY

    def get_cache_namespace(self) -> CacheNamespace:
        """Get the cache namespace for dictionary entries."""
        return CacheNamespace.DICTIONARY

    async def get(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
    ) -> dict[str, Any] | None:
        """Get dictionary entry from versioned storage."""
        manager = get_version_manager()
        full_resource_id = f"{resource_id}_{self.provider.value}"

        result = await manager.get_latest(
            resource_id=full_resource_id,
            resource_type=self.get_resource_type(),
            config=config or VersionConfig(),
        )

        if result:
            # Access the content field for the actual data
            return result.content if result else None
        return None

    async def save(
        self,
        resource_id: str,
        content: dict[str, Any],
        config: VersionConfig | None = None,
    ) -> None:
        """Save dictionary entry to versioned storage."""
        manager = get_version_manager()
        full_resource_id = f"{resource_id}_{self.provider.value}"

        await manager.save(
            resource_id=full_resource_id,
            resource_type=self.get_resource_type(),
            namespace=self.get_cache_namespace(),
            content=content,
            metadata={
                "word": resource_id,  # Keep word in metadata for backward compatibility
                "provider": self.provider.value,
                "provider_display_name": self.provider.display_name,
            },
            config=config or VersionConfig(),
        )

        logger.info(f"Saved dictionary entry for '{resource_id}' from {self.provider.display_name}")

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> dict[str, Any] | None:
        """Fetch dictionary entry from provider and optionally save."""
        config = config or VersionConfig()

        # Check if we should use cached version
        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached:
                logger.info(
                    f"Using cached entry for '{resource_id}' from {self.provider.display_name}"
                )
                return cached

        # Rate limiting
        await self.rate_limiter.acquire()

        # Track state
        if state_tracker:
            await state_tracker.update(
                stage="fetching",
                message=f"{resource_id} from {self.provider.display_name}",
            )

        # Fetch from provider
        logger.info(f"Fetching '{resource_id}' from {self.provider.display_name}")
        result = await self._fetch_from_provider(resource_id, state_tracker)

        # Save if configured
        if result and self.config.save_versioned:
            await self.save(resource_id, result, config)

        return result

    @property
    def get_api_session(self) -> httpx.AsyncClient:
        """Get API session (alias for api_client).

        Provided for backward compatibility.
        """
        return self.api_client
