"""Dictionary-specific connector base class."""

from __future__ import annotations

from typing import Any

from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.dictionary import DictionaryProvider
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig
from .models import DictionaryProviderEntry

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

    def get_cache_key_suffix(self) -> str:
        return self.provider.value

    def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
        """Get dictionary-specific metadata for a resource."""
        return {
            "word": resource_id,
            "provider": self.provider.value,
            "provider_display_name": self.provider.display_name,
        }

    def _coerce_entry(
        self,
        payload: DictionaryProviderEntry | dict[str, Any],
    ) -> DictionaryProviderEntry:
        if isinstance(payload, DictionaryProviderEntry):
            return payload
        return DictionaryProviderEntry.model_validate(payload)

    def model_dump(self, content: Any) -> Any:
        entry = self._coerce_entry(content)
        return entry.model_dump(mode="json")

    def model_load(self, content: Any) -> Any:
        return DictionaryProviderEntry.model_validate(content)

    async def get(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
    ) -> DictionaryProviderEntry | None:
        result = await super().get(resource_id, config)
        if result is None:
            return None
        return self._coerce_entry(result)

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> DictionaryProviderEntry | None:
        """Fetch dictionary entry from provider and convert to provider model."""
        config = config or VersionConfig()

        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached is not None:
                logger.info(
                    "%s using cached %s entry for '%s'",
                    self.provider.value,
                    self.get_resource_type().value,
                    resource_id,
                )
                return cached

        await self.rate_limiter.acquire()

        if state_tracker:
            await state_tracker.update(
                stage="fetching",
                message=f"{resource_id} from {self.provider.value}",
            )

        entry = await self._fetch_from_provider(resource_id, state_tracker)
        if entry is None:
            return None

        typed_entry = self._coerce_entry(entry)

        if self.config.save_versioned:
            await self.save(resource_id, typed_entry, config)

        return typed_entry
