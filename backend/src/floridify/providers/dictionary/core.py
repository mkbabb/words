"""Dictionary-specific connector base class."""

from __future__ import annotations

from typing import Any

from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.dictionary import DictionaryEntry, DictionaryProvider
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

    def get_provider_identifier(self) -> str:
        """Get the provider identifier for resource IDs."""
        return self.provider.value

    def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
        """Get dictionary-specific metadata for a resource."""
        return {
            "word": resource_id,  # Keep word in metadata for backward compatibility
            "provider": self.provider.value,
            "provider_display_name": self.provider.display_name,
        }

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryEntry | None:
        """Fetch dictionary entry from provider and convert to DictionaryEntry.
        
        This method overrides the base fetch() to return a typed DictionaryEntry object
        instead of a raw dictionary. The flow is:
        1. Call parent fetch() which returns dict from _fetch_from_provider
        2. Convert the dict to a DictionaryEntry object
        3. Return the typed object
        
        Note: For now, we return the dict directly to maintain compatibility.
        Future versions will implement full DictionaryEntry conversion.
        """
        # Get the dictionary data from the provider
        result = await super().fetch(resource_id, config, state_tracker)
        
        if result is None:
            return None
            
        # For now, return the dict as-is to maintain compatibility
        # TODO: Implement conversion from dict to DictionaryEntry
        # This will require creating Word, Definition, Pronunciation objects
        # and getting their IDs to populate the DictionaryEntry
        return result

