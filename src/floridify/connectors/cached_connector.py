"""Enhanced connector base class with caching capabilities."""

from __future__ import annotations

from typing import Any

from ..models import ProviderData
from ..storage.mongodb import MongoDBStorage
from .base import DictionaryConnector


class CachedDictionaryConnector(DictionaryConnector):
    """Enhanced dictionary connector with automatic API response caching."""

    def __init__(self, storage: MongoDBStorage | None = None, rate_limit: float = 1.0) -> None:
        """Initialize cached connector.

        Args:
            storage: MongoDB storage for caching (optional)
            rate_limit: Maximum requests per second
        """
        super().__init__(rate_limit=rate_limit)
        self.storage = storage

    async def fetch_definition_with_cache(
        self, word: str, max_cache_hours: int = 24
    ) -> ProviderData | None:
        """Fetch definition with automatic caching.

        Args:
            word: The word to look up
            max_cache_hours: Maximum age of cached response in hours

        Returns:
            ProviderData if successful, None if not found or error
        """
        # Try cache first if storage is available
        if self.storage:
            cached_response = await self.storage.get_cached_response(
                word, self.provider_name, max_cache_hours
            )
            if cached_response:
                # Parse cached response back to ProviderData
                return self._parse_cached_response(cached_response)

        # Fetch fresh data
        result = await self.fetch_definition(word)

        # Cache the raw response if storage is available and we got data
        if self.storage and result:
            # Convert ProviderData back to cacheable format
            cache_data = self._prepare_for_cache(result)
            await self.storage.cache_api_response(word, self.provider_name, cache_data)

        return result

    def _prepare_for_cache(self, provider_data: ProviderData) -> dict[str, Any]:
        """Prepare ProviderData for caching.

        Args:
            provider_data: ProviderData to cache

        Returns:
            Dictionary representation for caching
        """
        return provider_data.model_dump()

    def _parse_cached_response(self, cached_data: dict[str, Any]) -> ProviderData:
        """Parse cached response back to ProviderData.

        Args:
            cached_data: Cached response data

        Returns:
            Reconstructed ProviderData
        """
        return ProviderData.model_validate(cached_data)