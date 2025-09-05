"""URL-based language provider implementation."""

from __future__ import annotations

from typing import Any

from ....core.state_tracker import StateTracker
from ....providers.core import ConnectorConfig
from ....utils.logging import get_logger
from ..core import PARSER_MAP, SCRAPER_MAP, LanguageConnector
from ..models import LanguageProvider, LanguageSource, ParserType, ScraperType
from ..parsers import parse_scraped_data, parse_text_lines
from .scrapers import default_scraper

logger = get_logger(__name__)


class URLLanguageConnector(LanguageConnector):
    """Language connector that fetches from URLs."""

    def __init__(
        self,
        provider: LanguageProvider = LanguageProvider.CUSTOM_URL,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize URL language connector.

        Args:
            provider: Language provider enum value
            config: Connector configuration
        """
        super().__init__(provider=provider, config=config)

    async def _fetch_from_provider(
        self,
        query: LanguageSource,
        state_tracker: StateTracker | None = None,
    ) -> dict[str, Any] | None:
        """Fetch vocabulary from URL.

        Args:
            query: LanguageSource object with URL and parser info
            state_tracker: Optional state tracker for progress updates

        Returns:
            Dictionary containing vocabulary data
        """
        source = query

        try:
            if state_tracker:
                await state_tracker.update(
                    stage="downloading",
                    message=f"Downloading {source.name} from {source.url}",
                )

            # Get the appropriate scraper
            scraper_type = source.scraper or ScraperType.DEFAULT
            scraper_func = SCRAPER_MAP.get(scraper_type, default_scraper)

            # Fetch content using scraper with session
            async with self.scraper_session as client:
                content = await scraper_func(source.url, session=client)

            # Determine parser to use
            if isinstance(content, dict):
                # Structured data from custom scraper
                parser_func = parse_scraped_data
            else:
                # Text data - use configured parser
                parser_type = source.parser or ParserType.TEXT_LINES
                parser_func = PARSER_MAP.get(parser_type, parse_text_lines)

            # Parse content
            words, phrases = parser_func(content, source.language)

            # Combine words and phrases
            vocabulary = words + phrases

            # Return structured data
            return {
                "source_name": source.name,
                "language": source.language.value,
                "provider": self.provider.value,
                "vocabulary": vocabulary,
                "vocabulary_count": len(vocabulary),
                "words": words,
                "phrases": phrases,
                "source_url": source.url,
                "description": source.description,
            }

        except Exception as e:
            logger.error(f"Failed to fetch from {source.name}: {e}")
            if state_tracker:
                await state_tracker.update(
                    stage="error",
                    message=f"Failed to fetch {source.name}: {str(e)}",
                    error=str(e),
                )
            return None
