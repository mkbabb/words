"""URL-based language provider implementation."""

from __future__ import annotations

from typing import Any

from ....core.state_tracker import StateTracker
from ....providers.core import ConnectorConfig, RateLimitPresets
from ....utils.logging import get_logger
from ..core import LanguageConnector
from ..models import LanguageProvider, LanguageSource, ParserType, ScraperType
from ..parsers import (
    parse_csv_words,
    parse_json_vocabulary,
    parse_scraped_data,
    parse_text_lines,
)
from .scrapers import default_scraper, scrape_french_expressions

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
        if config is None:
            config = ConnectorConfig(rate_limit_config=RateLimitPresets.SCRAPER_RESPECTFUL.value)
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

            # Get the appropriate scraper and fetch content
            scraper_type = source.scraper or ScraperType.DEFAULT
            content: dict[str, Any] | str
            async with self.scraper_session as client:
                if scraper_type == ScraperType.FRENCH_EXPRESSIONS:
                    content = await scrape_french_expressions(source.url, session=client)
                else:  # DEFAULT or unknown
                    content = await default_scraper(source.url, session=client)

            # Determine parser to use and parse content
            if isinstance(content, dict):
                # Structured data from custom scraper
                words, phrases = parse_scraped_data(content, source.language)
            else:
                # Text data - use configured parser
                parser_type = source.parser or ParserType.TEXT_LINES
                if parser_type == ParserType.JSON_VOCABULARY:
                    words, phrases = parse_json_vocabulary(content, source.language)
                elif parser_type == ParserType.CSV_WORDS:
                    words, phrases = parse_csv_words(content, source.language)
                else:  # TEXT_LINES or unknown
                    words, phrases = parse_text_lines(content, source.language)

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
