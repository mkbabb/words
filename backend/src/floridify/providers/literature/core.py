"""Literature-specific connector base class."""

from __future__ import annotations

from typing import Any

from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.literature import AuthorInfo, LiteratureProvider
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig
from .models import LiteratureEntry, LiteratureSource

logger = get_logger(__name__)


class LiteratureConnector(BaseConnector):
    """Base literature connector with versioned storage."""

    def __init__(
        self,
        provider: LiteratureProvider,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize literature connector."""
        super().__init__(config or ConnectorConfig())
        self.provider = provider

    def get_resource_type(self) -> ResourceType:
        """Get the resource type for literature entries."""
        return ResourceType.LITERATURE

    def get_cache_namespace(self) -> CacheNamespace:
        """Get the cache namespace for literature entries."""
        return CacheNamespace.LITERATURE

    def get_cache_key_suffix(self) -> str:
        return self.provider.value

    def get_provider_identifier(self) -> str:
        """Get the provider identifier for resource IDs."""
        return self.provider.value

    def get_metadata_for_resource(self, resource_id: str) -> dict[str, Any]:
        """Get literature-specific metadata for a resource."""
        return {
            "work_id": resource_id,
            "provider": self.provider.value,
            "provider_display_name": self.provider.value.replace("_", " ").title(),
        }

    def _coerce_entry(self, payload: LiteratureEntry | dict[str, Any]) -> LiteratureEntry:
        if isinstance(payload, LiteratureEntry):
            entry = payload
        else:
            entry = LiteratureEntry.model_validate(payload)

        if not isinstance(entry.author, AuthorInfo):
            entry = entry.model_copy(update={"author": AuthorInfo.model_validate(entry.author)})

        if entry.source and not isinstance(entry.source, LiteratureSource):
            entry = entry.model_copy(
                update={"source": LiteratureSource.model_validate(entry.source)}
            )

        return entry

    def model_dump(self, content: Any) -> Any:
        entry = self._coerce_entry(content)
        return entry.model_dump(mode="json")

    def model_load(self, content: Any) -> Any:
        return self._coerce_entry(content)

    async def get(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
    ) -> LiteratureEntry | None:
        result = await super().get(resource_id, config)
        if result is None:
            return None
        return self._coerce_entry(result)

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LiteratureEntry | None:
        config = config or VersionConfig()

        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached is not None:
                return cached

        cached_entry = await self.get(resource_id)
        if cached_entry is None or cached_entry.source is None:
            raise ValueError("Cannot refresh literature entry without source metadata")

        return await self.fetch_source(
            cached_entry.source, config=config, state_tracker=state_tracker
        )

    async def fetch_source(
        self,
        source: LiteratureSource,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LiteratureEntry | None:
        config = config or VersionConfig()
        resource_id = source.name or source.url

        if not resource_id:
            raise ValueError("Literature sources require a name or URL")

        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached is not None:
                return cached

        await self.rate_limiter.acquire()

        if state_tracker:
            await state_tracker.update(
                stage="fetching",
                message=f"{resource_id} from {self.provider.value}",
            )

        payload = await self._fetch_from_provider(source, state_tracker)
        if payload is None:
            return None

        entry = self._coerce_entry(payload)

        if self.config.save_versioned:
            await self.save(resource_id, entry, config)

        return entry
