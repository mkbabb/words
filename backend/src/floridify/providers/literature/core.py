"""Literature-specific connector base class."""

from __future__ import annotations

import hashlib
from typing import Any

from ...caching.core import get_global_cache
from ...caching.manager import get_version_manager
from ...caching.models import CacheNamespace
from ...core.state_tracker import StateTracker
from ...corpus.literature.models import LiteratureSource
from ...models.versioned import (
    ContentLocation,
    ResourceType,
    StorageType,
    VersionConfig,
)
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig, ProviderType

logger = get_logger(__name__)


class LiteratureConnector(BaseConnector):
    """Base class for literature providers."""

    def __init__(
        self,
        source: LiteratureSource,
        config: ConnectorConfig | None = None,
    ):
        super().__init__(
            provider_type=ProviderType.LITERATURE,
            config=config,
        )
        self.source = source

    async def get(
        self,
        source_id: str,  # This is the literature source ID
        config: VersionConfig | None = None,
    ) -> dict[str, Any] | None:
        """Get literature entry from versioned storage.

        Args:
            source_id: Source identifier
            config: Version configuration

        Returns:
            Literature entry data or None if not found
        """
        manager = get_version_manager()
        full_resource_id = f"literature_{self.source.value}_{source_id}"

        # Get from versioned storage
        versioned = await manager.get_latest(
            resource_id=full_resource_id,
            resource_type=ResourceType.LITERATURE,
            config=config or VersionConfig(),
        )

        if not versioned:
            return None

        # Load content
        content = await versioned.get_content()
        return content

    async def save(
        self,
        source_id: str,  # This is the literature source ID
        content: Any,
        config: VersionConfig | None = None,
    ) -> None:
        """Save literature entry using version manager.

        Args:
            source_id: Source identifier
            content: Literature entry data
            config: Version configuration
        """
        metadata: dict[str, Any] = {}
        manager = get_version_manager()
        full_resource_id = f"literature_{self.source.value}_{source_id}"

        # If content is the full text, store it separately
        if isinstance(content, dict) and "full_text" in content:
            text = content["full_text"]
            text_hash = hashlib.sha256(text.encode()).hexdigest()

            # Store text in cache
            cache = await get_global_cache()
            cache_key = f"work_{source_id}_{text_hash[:8]}"

            await cache.set(
                namespace=CacheNamespace.CORPUS,
                key=cache_key,
                value={"text": text, "metadata": metadata},
            )

            # Create content location
            content_location = ContentLocation(
                storage_type=StorageType.CACHE,
                cache_namespace=CacheNamespace.CORPUS,
                cache_key=cache_key,
                size_bytes=len(text),
                size_compressed=None,
                checksum=text_hash,
            )

            # Update content to store metadata only
            content = {
                **content,
                "content_location": content_location.model_dump(),
                "text_hash": text_hash,
            }
            del content["full_text"]

        await manager.save(
            resource_id=full_resource_id,
            resource_type=ResourceType.LITERATURE,
            namespace=CacheNamespace.LITERATURE,
            content=content,
            config=config or VersionConfig(),
            metadata={
                "source_id": source_id,
                "source": self.source.value,
                **metadata,
            },
        )
        logger.info(f"Saved literature entry '{source_id}' from {self.source.value}")

    async def fetch(
        self,
        source_id: str,  # This is the literature source ID
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> dict[str, Any] | None:
        """Fetch literature from provider and optionally save.

        Args:
            source_id: Source identifier
            config: Version configuration
            state_tracker: Optional state tracker for progress updates

        Returns:
            Literature entry data or None
        """
        config = config or VersionConfig()

        # Apply rate limiting
        await self.rate_limiter.acquire()

        try:
            # Call the implementation-specific method
            logger.info(f"Fetching literature '{source_id}' from {self.source.value}")
            data = await self._fetch_from_provider(source_id, state_tracker)

            if data:
                # Record success for rate limiter
                self.rate_limiter.record_success()

                # Save if configured to do so
                if self.config.save_versioned:
                    await self.save(source_id, data, config)

                return data  # type: ignore[no-any-return]

            # Still record success even if no data (not an error)
            self.rate_limiter.record_success()
            return None

        except Exception as e:
            # Record error for rate limiter
            self.rate_limiter.record_error()
            logger.error(f"Error fetching literature '{source_id}' from {self.source.value}: {e}")
            raise

    # Note: _fetch_from_provider is abstract and must be implemented by subclasses
