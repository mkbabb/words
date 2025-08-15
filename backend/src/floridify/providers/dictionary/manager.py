"""Dictionary provider manager with unified versioning."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from ...caching.models import CacheTTL
from ...caching.manager import BaseManager
from ...core.constants import ResourceType
from ...caching.versioned import VersionConfig, VersionedDataManager, get_dictionary_version_manager
from ...models.dictionary import DictionaryProvider, DictionaryProviderData, Word
from ...models.versioned import DictionaryVersionedData
from ...utils.logging import get_logger
from .api.free_dictionary import FreeDictionaryConnector
from .api.merriam_webster import MerriamWebsterConnector
from .api.oxford import OxfordConnector
from .base import DictionaryConnector
from .scraper.wiktionary import WiktionaryConnector
from .scraper.wordhippo import WordHippoConnector

logger = get_logger(__name__)


class DictionaryProviderManager(BaseManager[DictionaryProviderData, DictionaryProviderData]):
    """Unified manager for dictionary providers with versioning support."""

    def __init__(self) -> None:
        """Initialize the dictionary provider manager."""
        super().__init__()

    @property
    def resource_type(self) -> ResourceType:
        """Get the resource type this manager handles."""
        return ResourceType.DICTIONARY

    @property
    def default_cache_ttl(self) -> timedelta | None:
        """Get default cache TTL for dictionary operations."""
        return CacheTTL.API_RESPONSE

    def _get_version_manager(self) -> VersionedDataManager[DictionaryVersionedData]:
        """Get the version manager for dictionary data."""
        return get_dictionary_version_manager()

    async def _reconstruct_resource(
        self, versioned_data: DictionaryVersionedData
    ) -> DictionaryProviderData | None:
        """Reconstruct dictionary provider data from versioned data."""
        try:
            if versioned_data.content_inline:
                return DictionaryProviderData(**versioned_data.content_inline)
            if versioned_data.content_location:
                # Load content from storage
                version_manager = self._get_version_manager()
                content = await version_manager.load_content(versioned_data.content_location)
                if content:
                    return DictionaryProviderData(**content)
            return None
        except Exception:
            return None

    def _get_provider_connector(self, provider: DictionaryProvider) -> DictionaryConnector | None:
        """Get a connector instance for the given provider."""
        provider_classes = {
            DictionaryProvider.FREE_DICTIONARY: FreeDictionaryConnector,
            DictionaryProvider.MERRIAM_WEBSTER: MerriamWebsterConnector,
            DictionaryProvider.OXFORD: OxfordConnector,
            DictionaryProvider.WIKTIONARY: WiktionaryConnector,
            DictionaryProvider.WORDHIPPO: WordHippoConnector,
        }

        connector_class = provider_classes.get(provider)
        if not connector_class:
            logger.warning(f"No connector class found for provider: {provider.value}")
            return None

        try:
            return connector_class()
        except Exception as e:
            logger.warning(f"Failed to initialize {provider.value}: {e}")
            return None

    async def fetch_definitions(
        self,
        word: Word,
        providers: list[DictionaryProvider] | None = None,
        use_ttl: bool = True,
    ) -> dict[DictionaryProvider, DictionaryProviderData]:
        """Fetch definitions from multiple providers in parallel.

        Args:
            word: The word to fetch definitions for
            providers: List of providers to use (None for all)
            use_ttl: Whether to use TTL for caching

        Returns:
            Dictionary mapping providers to their data

        """
        # Default to all available providers if none specified
        target_providers = providers or [
            DictionaryProvider.FREE_DICTIONARY,
            DictionaryProvider.MERRIAM_WEBSTER,
            DictionaryProvider.OXFORD,
            DictionaryProvider.WIKTIONARY,
            DictionaryProvider.WORDHIPPO,
        ]

        # Always run in parallel for performance
        tasks = []
        for provider in target_providers:
            connector = self._get_provider_connector(provider)
            if connector:
                tasks.append(self._fetch_from_provider(word, provider, connector, use_ttl))

        if not tasks:
            return {}

        results: dict[DictionaryProvider, DictionaryProviderData] = {}
        fetch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for provider, result in zip(target_providers, fetch_results, strict=False):
            if not isinstance(result, Exception) and result:
                results[provider] = result
            elif isinstance(result, Exception):
                logger.debug(f"Error fetching from {provider.value}: {result}")

        return results

    async def _fetch_from_provider(
        self,
        word: Word,
        provider: DictionaryProvider,
        connector: DictionaryConnector,
        use_ttl: bool = True,
    ) -> DictionaryProviderData | None:
        """Fetch from a single provider with versioning.

        Args:
            word: The word to fetch
            provider: The provider to use
            connector: The connector instance to use
            use_ttl: Whether to use TTL for caching

        Returns:
            Provider data or None

        """
        resource_id = f"{provider.value}:{word.word}"

        # Try to get from base manager first
        cached_data = await self.get(resource_id, use_ttl)
        if cached_data:
            logger.debug(f"Using cached version for {resource_id}")
            return cached_data

        # Fetch from provider
        try:
            data = await connector.fetch(word)

            if data:
                # Configure versioning with TTL
                config = VersionConfig(
                    save_versions=True,
                    ttl=CacheTTL.API_RESPONSE if use_ttl else None,
                )

                # Save to versioned storage
                version_manager = self._get_version_manager()
                await version_manager.save(
                    resource_id=resource_id,
                    content=data.model_dump(),
                    resource_type=self.resource_type.value,
                    metadata={
                        "provider": provider.value,
                        "word": word.word,
                        "language": word.language.value,
                    },
                    tags=[provider.value, "dictionary"],
                    config=config,
                )

                # Cache the result
                self._cache[resource_id] = data

            return data

        except Exception as e:
            logger.error(f"Failed to fetch from {provider.value}: {e}")
            return None

    async def get_or_create_definition(
        self,
        word: Word,
        provider: DictionaryProvider,
        use_ttl: bool = True,
    ) -> DictionaryProviderData | None:
        """Get existing definition or fetch new one.

        Args:
            word: The word to look up
            provider: The provider to use
            use_ttl: Whether to use TTL for caching

        Returns:
            Provider data or None

        """
        connector = self._get_provider_connector(provider)
        if not connector:
            return None
        return await self._fetch_from_provider(word, provider, connector, use_ttl)

    async def get_or_create(
        self,
        resource_id: str,
        use_ttl: bool = True,
    ) -> DictionaryProviderData | None:
        """Simplified get or create method.

        Args:
            resource_id: The resource identifier (format: provider:word)
            use_ttl: Whether to use TTL for caching

        Returns:
            Provider data or None

        """
        return await self.get(resource_id, use_ttl)

    async def cleanup_versions(
        self,
        word: Word | None = None,
        provider: DictionaryProvider | None = None,
        keep_count: int = 5,
    ) -> int:
        """Clean up old versions for a word or provider.

        Args:
            word: Optional word to clean up (None for all)
            provider: Optional provider to clean up (None for all)
            keep_count: Number of versions to keep

        Returns:
            Total number of versions deleted

        """
        if word and provider:
            resource_id = f"{provider.value}:{word.word}"
            return await super().cleanup_versions(resource_id, keep_count)
        logger.info("Full cleanup not yet implemented")
        return 0


# Global manager instance
_dictionary_manager: DictionaryProviderManager | None = None


def get_dictionary_manager() -> DictionaryProviderManager:
    """Get the global dictionary provider manager instance."""
    global _dictionary_manager
    if _dictionary_manager is None:
        _dictionary_manager = DictionaryProviderManager()
    return _dictionary_manager
