"""Dictionary-specific connector base class."""

from __future__ import annotations

from typing import Any

from ...caching.manager import get_version_manager
from ...caching.models import CacheNamespace
from ...core.state_tracker import StateTracker
from ...models.dictionary import DictionaryProvider, Language
from ...models.versioned import (
    ResourceType,
    VersionConfig,
)
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig, ProviderType

logger = get_logger(__name__)


class DictionaryConnector(BaseConnector):
    """Base class for dictionary providers."""

    def __init__(
        self,
        provider: DictionaryProvider,
        config: ConnectorConfig | None = None,
    ):
        super().__init__(
            provider_type=ProviderType.DICTIONARY,
            config=config,
        )
        self.provider = provider

    async def get(
        self,
        word: str,
        config: VersionConfig | None = None,
    ) -> dict[str, Any] | None:
        """Get dictionary entry from versioned storage.

        Args:
            word: Word to look up
            config: Version configuration

        Returns:
            Dictionary entry data or None if not found
        """
        manager = get_version_manager()
        full_resource_id = f"{word}_{self.provider.value}"

        # Get from versioned storage
        versioned = await manager.get_latest(
            resource_id=full_resource_id,
            resource_type=ResourceType.DICTIONARY,
            config=config or VersionConfig(),
        )

        if not versioned:
            return None

        # Load content
        content = await versioned.get_content()
        return content

    async def save(
        self,
        word: str,
        content: Any,
        config: VersionConfig | None = None,
    ) -> None:
        """Save dictionary entry using version manager.

        Args:
            word: Word to save
            content: Dictionary entry data
            config: Version configuration
        """
        manager = get_version_manager()
        full_resource_id = f"{word}_{self.provider.value}"

        await manager.save(
            resource_id=full_resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.DICTIONARY,
            content=content,
            config=config or VersionConfig(),
            metadata={
                "word": word,
                "provider": self.provider.value,
                "language": Language.ENGLISH.value,
            },
        )
        logger.info(f"Saved dictionary entry for '{word}' from {self.provider.display_name}")

    async def fetch(
        self,
        word: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> dict[str, Any] | None:
        """Fetch definition from provider and optionally save.

        Args:
            word: Word to fetch
            config: Version configuration
            state_tracker: Optional state tracker for progress updates

        Returns:
            Dictionary entry data or None
        """
        config = config or VersionConfig()

        # Apply rate limiting
        await self.rate_limiter.acquire()

        try:
            # Call the implementation-specific method
            logger.info(f"Fetching '{word}' from {self.provider.display_name}")
            data = await self._fetch_from_provider(word, state_tracker)

            if data:
                # Record success for rate limiter
                self.rate_limiter.record_success()

                # Save if configured to do so
                if self.config.save_versioned:
                    await self.save(word, data, config)

                return data  # type: ignore[no-any-return]

            # Still record success even if no data (not an error)
            self.rate_limiter.record_success()
            return None

        except Exception as e:
            # Record error for rate limiter
            self.rate_limiter.record_error()
            logger.error(f"Error fetching '{word}' from {self.provider.display_name}: {e}")
            raise

    # Note: _fetch_from_provider is abstract and must be implemented by subclasses
