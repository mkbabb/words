"""URL-based literature provider implementation."""

from __future__ import annotations

from ....core.state_tracker import StateTracker
from ....models.literature import AuthorInfo, Genre, LiteratureProvider, Period
from ....providers.core import ConnectorConfig
from ....utils.logging import get_logger
from ..core import LiteratureConnector
from ..models import LiteratureEntry, LiteratureSource, ParserType, ScraperType
from ..parsers import (
    extract_metadata,
    parse_epub,
    parse_html,
    parse_markdown,
    parse_pdf,
    parse_text,
)
from .scrapers import (
    default_literature_scraper,
    scrape_archive_org,
    scrape_gutenberg,
    scrape_wikisource,
)

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
            Dictionary with literature content

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
            client = self.scraper_session
            if scraper_type == ScraperType.GUTENBERG:
                content = await scrape_gutenberg(source.url, session=client)
            elif scraper_type == ScraperType.ARCHIVE_ORG:
                content = await scrape_archive_org(source.url, session=client)
            elif scraper_type == ScraperType.WIKISOURCE:
                content = await scrape_wikisource(source.url, session=client)
            else:  # DEFAULT or unknown
                content = await default_literature_scraper(source.url, session=client)

            # Determine parser to use and parse content
            parser_type = source.parser or ParserType.PLAIN_TEXT
            if parser_type == ParserType.MARKDOWN:
                text = parse_markdown(content)
            elif parser_type == ParserType.HTML:
                text = parse_html(content)
            elif parser_type == ParserType.EPUB:
                text = parse_epub(content)
            elif parser_type == ParserType.PDF:
                text = parse_pdf(content)
            else:  # PLAIN_TEXT or unknown
                text = parse_text(content)
            metadata = extract_metadata(content) if isinstance(content, dict) else {}

            # Return dict matching the pattern from other providers
            author = source.author or AuthorInfo(
                name=metadata.get("author", "Unknown"),
                period=source.period or Period.CONTEMPORARY,
                primary_genre=source.genre or Genre.NOVEL,
            )

            return LiteratureEntry(
                title=metadata.get("title", source.name),
                author=author,
                source=source,
                work_id=source.name,
                gutenberg_id=metadata.get("gutenberg_id"),
                year=metadata.get("year"),
                subtitle=metadata.get("subtitle"),
                description=metadata.get("description", source.description),
                keywords=metadata.get("keywords", []),
                genre=source.genre or metadata.get("genre"),
                period=source.period or metadata.get("period"),
                language=source.language,
                extracted_vocabulary=metadata.get("extracted_vocabulary", []),
                text=text,
                metadata={"source_url": source.url, **metadata},
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
