"""URL-based literature provider implementation."""

from __future__ import annotations

from ....core.state_tracker import StateTracker
from ....models.literature import AuthorInfo, Genre, LiteratureProvider, Period
from ....providers.core import ConnectorConfig
from ....utils.logging import get_logger
from ..core import PARSER_MAP, SCRAPER_MAP, LiteratureConnector
from ..models import LiteratureEntry, LiteratureSource, ParserType, ScraperType
from ..parsers import extract_metadata, parse_text
from .scrapers import default_literature_scraper

logger = get_logger(__name__)


class URLLiteratureConnector(LiteratureConnector):
    """Literature connector that fetches from URLs."""

    def __init__(
        self,
        provider: LiteratureProvider = LiteratureProvider.CUSTOM_URL,
        config: ConnectorConfig | None = None,
    ) -> None:
        """Initialize URL literature connector.

        Args:
            provider: Literature provider enum value
            config: Connector configuration
        """
        super().__init__(provider=provider, config=config)

    async def _fetch_from_provider(
        self,
        query: LiteratureSource,
        state_tracker: StateTracker | None = None,
    ) -> LiteratureEntry | None:
        """Fetch literature text from URL.

        Args:
            query: LiteratureSource object with URL and metadata
            state_tracker: Optional state tracker for progress updates

        Returns:
            LiteratureEntry with text content
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
            scraper_func = SCRAPER_MAP.get(scraper_type, default_literature_scraper)

            # Fetch content using scraper with session
            async with self.scraper_session as client:
                content = await scraper_func(source.url, session=client)

            # Determine parser to use
            parser_type = source.parser or ParserType.PLAIN_TEXT
            parser_func = PARSER_MAP.get(parser_type, parse_text)

            # Parse content
            text = parser_func(content)
            metadata = extract_metadata(content) if isinstance(content, dict) else {}

            # Create LiteratureEntry
            return LiteratureEntry(
                title=metadata.get("title", source.name),
                author=source.author
                or AuthorInfo(
                    name=metadata.get("author", "Unknown"),
                    period=source.period or Period.CONTEMPORARY,
                    primary_genre=source.genre or Genre.NOVEL,
                ),
                provider=self.provider,
                genre=source.genre or Genre.NOVEL,
                period=source.period or Period.CONTEMPORARY,
                language=source.language,
                text=text,
                year=metadata.get("year"),
                source_url=source.url,
                gutenberg_id=metadata.get("gutenberg_id"),
                work_id=source.name,
            )

        except Exception as e:
            logger.error(f"Failed to fetch from {source.name}: {e}")
            if state_tracker:
                await state_tracker.update(
                    stage="error",
                    message=f"Failed to fetch {source.name}: {str(e)}",
                    error=str(e),
                )
            return None
