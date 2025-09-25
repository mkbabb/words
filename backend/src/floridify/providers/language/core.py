"""Language-specific connector base class."""

from __future__ import annotations

from typing import Any

from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.base import Language
from ...providers.language.models import (
    LanguageEntry,
    LanguageProvider,
    LanguageSource,
    ParserType,
    ScraperType,
)
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

    def get_cache_key_suffix(self) -> str:
        return self.provider.value

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

    def _build_source(self, payload: dict[str, Any]) -> LanguageSource:
        raw_language = payload.get("language", Language.ENGLISH)
        language = (
            raw_language if isinstance(raw_language, Language) else Language(str(raw_language))
        )

        raw_parser = payload.get("parser") or payload.get("parser_type")
        parser = (
            raw_parser
            if isinstance(raw_parser, ParserType)
            else ParserType(str(raw_parser))
            if raw_parser
            else ParserType.TEXT_LINES
        )

        raw_scraper = payload.get("scraper")
        scraper = (
            raw_scraper
            if isinstance(raw_scraper, ScraperType)
            else ScraperType(str(raw_scraper))
            if raw_scraper
            else None
        )

        return LanguageSource(
            name=payload.get("source_name", payload.get("resource_id", "")),
            url=payload.get("source_url", payload.get("url", "")),
            parser=parser,
            language=language,
            description=payload.get("description", ""),
            scraper=scraper,
        )

    def _coerce_entry(self, payload: LanguageEntry | dict[str, Any]) -> LanguageEntry:
        if isinstance(payload, LanguageEntry):
            entry = payload
        else:
            entry = LanguageEntry.model_validate(payload)

        if entry.provider != self.provider:
            entry = entry.model_copy(update={"provider": self.provider})

        if not isinstance(entry.source, LanguageSource):
            entry = entry.model_copy(update={"source": LanguageSource.model_validate(entry.source)})

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
    ) -> LanguageEntry | None:
        result = await super().get(resource_id, config)
        if result is None:
            return None
        return self._coerce_entry(result)

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LanguageEntry | None:
        config = config or VersionConfig()

        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached is not None:
                return cached

        cached_metadata = await self.get(resource_id)
        if cached_metadata is None:
            raise ValueError(
                "No cached language entry for resource; supply a LanguageSource via fetch_source",
            )

        return await self.fetch_source(
            cached_metadata.source, config=config, state_tracker=state_tracker
        )

    async def fetch_source(
        self,
        source: LanguageSource,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> LanguageEntry | None:
        config = config or VersionConfig()
        resource_id = source.name

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
