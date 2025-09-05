"""Literature-specific connector base class."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ...caching.manager import get_version_manager
from ...caching.models import CacheNamespace, ResourceType, VersionConfig
from ...core.state_tracker import StateTracker
from ...models.literature import LiteratureProvider
from ...utils.logging import get_logger
from ..core import BaseConnector, ConnectorConfig
from ..literature.models import ParserType, ScraperType
from .parsers import (
    parse_epub,
    parse_html,
    parse_markdown,
    parse_pdf,
    parse_text,
)
from .scraper.scrapers import (
    default_literature_scraper,
    scrape_archive_org,
    scrape_gutenberg,
    scrape_wikisource,
)

logger = get_logger(__name__)

# Type for scraper functions
ScraperFunc = Callable[..., Awaitable[str | dict[str, Any]]]

# Type for parser functions
ParserFunc = Callable[[str | dict[str, Any]], str]

# Map scraper enums to functions
SCRAPER_MAP: dict[ScraperType, ScraperFunc] = {
    ScraperType.DEFAULT: default_literature_scraper,
    ScraperType.GUTENBERG: scrape_gutenberg,
    ScraperType.ARCHIVE_ORG: scrape_archive_org,
    ScraperType.WIKISOURCE: scrape_wikisource,
}

# Map parser enums to functions
PARSER_MAP: dict[ParserType, ParserFunc] = {
    ParserType.PLAIN_TEXT: parse_text,
    ParserType.MARKDOWN: parse_markdown,
    ParserType.HTML: parse_html,
    ParserType.EPUB: parse_epub,
    ParserType.PDF: parse_pdf,
}


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

    async def get(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
    ) -> dict[str, Any] | None:
        """Get literature entry from versioned storage."""
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
        """Save literature entry to versioned storage."""
        manager = get_version_manager()
        full_resource_id = f"{resource_id}_{self.provider.value}"

        await manager.save(
            resource_id=full_resource_id,
            resource_type=self.get_resource_type(),
            namespace=self.get_cache_namespace(),
            content=content,
            metadata={
                "work_id": resource_id,
                "provider": self.provider.value,
                "provider_display_name": self.provider.value.replace("_", " ").title(),
            },
            config=config or VersionConfig(),
        )

        logger.info(f"Saved literature entry '{resource_id}' from {self.provider.value}")

    async def fetch(
        self,
        resource_id: str,
        config: VersionConfig | None = None,
        state_tracker: StateTracker | None = None,
    ) -> dict[str, Any] | None:
        """Fetch literature entry from provider and optionally save."""
        config = config or VersionConfig()

        # Check if we should use cached version
        if not config.force_rebuild:
            cached = await self.get(resource_id, config)
            if cached:
                logger.info(f"Using cached entry for '{resource_id}' from {self.provider.value}")
                return cached

        # Rate limiting
        await self.rate_limiter.acquire()

        # Track state
        if state_tracker:
            await state_tracker.update(
                stage="fetching",
                message=f"{resource_id} from {self.provider.value}",
            )

        # Fetch from provider
        logger.info(f"Fetching '{resource_id}' from {self.provider.value}")
        result = await self._fetch_from_provider(resource_id, state_tracker)

        # Save if configured
        if result and self.config.save_versioned:
            await self.save(resource_id, result, config)

        return result
