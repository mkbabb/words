"""URL-based language provider implementation."""

from __future__ import annotations

import json
from typing import Any

from ....core.state_tracker import StateTracker
from ....providers.core import ConnectorConfig, RateLimitPresets
from ....utils.logging import get_logger
from ..core import LanguageConnector
from ..models import LanguageEntry, LanguageProvider, LanguageSource, ParserType, ScraperType
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
    ) -> LanguageEntry | None:
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
            client = self.scraper_session
            if scraper_type == ScraperType.FRENCH_EXPRESSIONS:
                content = await scrape_french_expressions(source.url, session=client)
            else:  # DEFAULT or unknown
                content = await default_scraper(source.url, session=client)

            # Determine parser to use and parse content
            parser_type = source.parser or ParserType.TEXT_LINES
            if isinstance(content, dict):
                # Structured data from custom scraper - use JSON parser which handles
                # various structures including {"data": [...]} from French expressions
                if parser_type in (ParserType.CUSTOM, ParserType.JSON_VOCABULARY):
                    words, phrases = parse_json_vocabulary(content, source.language)
                else:
                    words, phrases = parse_scraped_data(content, source.language)
            # Text data - use configured parser
            elif parser_type == ParserType.JSON_VOCABULARY:
                words, phrases = parse_json_vocabulary(content, source.language)
            elif parser_type == ParserType.CSV_WORDS:
                words, phrases = parse_csv_words(content, source.language)
            else:  # TEXT_LINES or unknown
                words, phrases = parse_text_lines(content, source.language)

            vocabulary = list(dict.fromkeys([*words, *phrases]))
            idioms: list[str] = []
            metadata: dict[str, Any] = {}

            # Extract idioms from parsed JSON data
            if parser_type == ParserType.JSON_VOCABULARY and isinstance(content, str):
                try:

                    json_data = json.loads(content)
                    if isinstance(json_data, dict) and "idioms" in json_data:
                        idioms = list(dict.fromkeys(json_data.get("idioms", [])))
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

            if isinstance(content, dict):
                idioms = list(dict.fromkeys(content.get("idioms", [])))
                metadata = content.get("metadata", {})

            return LanguageEntry(
                provider=self.provider,
                source=source,
                vocabulary=vocabulary,
                phrases=list(dict.fromkeys(phrases)),
                idioms=idioms,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to fetch from {source.name}: {e}")
            if state_tracker:
                await state_tracker.update(
                    stage="error",
                    message=f"Failed to fetch {source.name}: {e!s}",
                    error=str(e),
                )
            return None
