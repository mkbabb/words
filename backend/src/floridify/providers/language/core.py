"""Language-specific connector base class."""

from __future__ import annotations

from typing import Any

from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...providers.language.models import LanguageEntry, LanguageProvider
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig

logger = get_logger(__name__)


class LanguageConnector(BaseConnector):
    """Base language connector with versioned storage."""

    def __init__(
        self,
        provider: LanguageProvider,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize language connector."""
        super().__init__(config or ConnectorConfig())
        self.provider = provider

    def get_resource_type(self) -> ResourceType:
        """Get the resource type for language entries."""
        return ResourceType.LANGUAGE

    def get_cache_namespace(self) -> CacheNamespace:
        """Get the cache namespace for language entries."""
        return CacheNamespace.LANGUAGE

    def get_provider_identifier(self) -> str:
        """Get the provider identifier for resource IDs."""
        return self.provider.value

    def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
        """Get language-specific metadata for a resource."""
        return {
            "source_name": resource_id,
            "provider": self.provider.value,
            "provider_display_name": self.provider.display_name,
        }

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LanguageEntry | None:
        """Fetch language entry from provider and convert to LanguageEntry.
        
        This method overrides the base fetch() to return a typed LanguageEntry object
        instead of a raw dictionary. The flow is:
        1. Call parent fetch() which returns dict from _fetch_from_provider
        2. Convert the dict to a LanguageEntry object
        3. Return the typed object
        
        Note: For now, we return the dict directly to maintain compatibility.
        Future versions will implement full LanguageEntry conversion.
        """
        # Get the dictionary data from the provider
        result = await super().fetch(resource_id, config, state_tracker)
        
        if result is None:
            return None
            
        # For now, return the dict as-is to maintain compatibility
        # TODO: Convert dict to LanguageEntry
        return result
