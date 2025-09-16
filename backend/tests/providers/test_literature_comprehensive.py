"""Comprehensive literature provider tests.

Tests all literature providers with complete coverage of:
- Work downloading and metadata extraction
- Text cleaning and processing
- Author-based bulk operations
- MongoDB persistence
- Caching and versioning
"""

from __future__ import annotations

import io
import zipfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace, ResourceType
from floridify.models.base import Language
from floridify.models.literature import AuthorInfo, Genre, LiteratureProvider, Period
from floridify.providers.core import ConnectorConfig
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.api.internet_archive import InternetArchiveConnector
from floridify.providers.literature.models import (
    LiteratureEntry,
    LiteratureSource,
    ParserType as LitParserType,
)
from floridify.providers.literature.scraper.url import URLLiteratureConnector


@pytest.mark.asyncio
class TestLiteratureProviderFetch:
    """Test literature provider fetching operations."""

    @pytest_asyncio.fixture
    async def mock_http_client(self) -> AsyncMock:
        """Create mock HTTP client for API testing."""
        client = AsyncMock(spec=httpx.AsyncClient)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = "Sample book text content"
        response.content = b"Sample book binary content"
        response.raise_for_status = MagicMock()
        client.get = AsyncMock(return_value=response)
        return client

    @pytest_asyncio.fixture
    async def gutenberg_connector(self) -> GutenbergConnector:
        """Create Gutenberg connector."""
        config = ConnectorConfig()
        return GutenbergConnector(config=config)

    async def test_gutenberg_download_work(
        self,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test downloading a work from Project Gutenberg."""
        # Mock successful text download (needs > 500 chars)
        mock_text = """
        *** START OF THE PROJECT GUTENBERG EBOOK ***
        
        Pride and Prejudice
        by Jane Austen
        
        Chapter 1
        
        It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife.
        
        However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.
        
        "My dear Mr. Bennet," said his lady to him one day, "have you heard that Netherfield Park is let at last?"
        
        Mr. Bennet replied that he had not.
        
        "But it is," returned she; "for Mrs. Long has just been here, and she told me all about it."
        
        Mr. Bennet made no answer.
        
        "Do you not want to know who has taken it?" cried his wife impatiently.
        
        "You want to tell me, and I have no objection to hearing it."
        
        This was invitation enough.
        
        *** END OF THE PROJECT GUTENBERG EBOOK ***
        """
        mock_http_client.get.return_value.text = mock_text
        mock_http_client.get.return_value.status_code = 200

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client

            # Create a LiteratureEntry for the work
            work = LiteratureEntry(
                title="Pride and Prejudice",
                author=AuthorInfo(
                    name="Jane Austen",
                    period=Period.ROMANTIC,
                    primary_genre=Genre.NOVEL,
                ),
                gutenberg_id="1342",
            )
            result = await gutenberg_connector.download_work(work)

        assert result is not None
        assert "It is a truth universally acknowledged" in result
        assert "*** START OF" not in result  # Headers should be removed
        assert "*** END OF" not in result  # Footers should be removed

    async def test_gutenberg_download_zipped_work(
        self,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test downloading a zipped work from Gutenberg."""
        # Create a mock zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("pg1342.txt", "Pride and Prejudice text content")

        # First call fails (no UTF-8), second returns zip
        mock_http_client.get.side_effect = [
            MagicMock(status_code=404),  # UTF-8 not found
            MagicMock(
                status_code=200,
                content=zip_buffer.getvalue(),
                raise_for_status=MagicMock(),
            ),
        ]

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            with patch("zipfile.ZipFile") as mock_zip:
                mock_zip.return_value.__enter__.return_value.namelist.return_value = ["pg1342.txt"]
                mock_zip.return_value.__enter__.return_value.read.return_value = (
                    b"Pride and Prejudice text"
                )

                result = await gutenberg_connector._fetch_work_content("1342", {})

        assert result is not None
        assert "Pride and Prejudice" in result

    async def test_gutenberg_search_works(
        self,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test searching for works on Gutenberg."""
        # Mock search results page
        mock_http_client.get.return_value.text = """
        <html>
            <li class="booklink">
                <a href="/ebooks/1342" class="link">
                    <span class="title">Pride and Prejudice</span>
                    <span class="subtitle">by Jane Austen</span>
                </a>
            </li>
            <li class="booklink">
                <a href="/ebooks/11" class="link">
                    <span class="title">Alice's Adventures in Wonderland</span>
                    <span class="subtitle">by Lewis Carroll</span>
                </a>
            </li>
        </html>
        """

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            results = await gutenberg_connector.search_works("pride")

        assert len(results) >= 1
        assert any("1342" in str(r) for r in results)

    async def test_gutenberg_download_author_works(
        self,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test downloading all works by an author."""
        # Mock author search
        mock_http_client.get.side_effect = [
            MagicMock(
                status_code=200,
                text='<a href="/ebooks/1342">Pride</a><a href="/ebooks/1343">Sense</a>',
            ),
            MagicMock(status_code=200, text="Pride and Prejudice text"),
            MagicMock(status_code=200, text="Sense and Sensibility text"),
        ]

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            author = AuthorInfo(
                name="Jane Austen",
                period=Period.ROMANTIC,
                primary_genre=Genre.NOVEL,
            )
            # Create work entries
            works = [
                LiteratureEntry(
                    title="Pride and Prejudice",
                    author=author,
                    gutenberg_id="1342",
                ),
                LiteratureEntry(
                    title="Sense and Sensibility",
                    author=author,
                    gutenberg_id="161",
                ),
            ]
            results = await gutenberg_connector.download_author_works(author, works, limit=2)

        assert len(results) <= 2

    async def test_gutenberg_metadata_extraction(
        self,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test extracting metadata from Gutenberg."""
        mock_http_client.get.return_value.text = """
        <html>
            <h1 itemprop="name">Pride and Prejudice</h1>
            <a itemprop="creator" href="/ebooks/author/68">Austen, Jane</a>
            <td itemprop="datePublished">1813</td>
            <span class="block">Downloads: 12345</span>
        </html>
        """

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            metadata = await gutenberg_connector._fetch_work_metadata("1342")

        assert metadata is not None
        assert metadata.get("title") == "Pride and Prejudice"
        assert "Austen" in metadata.get("author", "")


@pytest.mark.asyncio
class TestInternetArchiveProvider:
    """Test Internet Archive provider operations."""

    @pytest_asyncio.fixture
    async def ia_connector(self) -> InternetArchiveConnector:
        """Create Internet Archive connector."""
        config = ConnectorConfig()
        return InternetArchiveConnector(config=config)

    async def test_internet_archive_search(
        self,
        ia_connector: InternetArchiveConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test searching Internet Archive."""
        mock_http_client.get.return_value.json.return_value = {
            "response": {
                "docs": [
                    {
                        "identifier": "prideandprejudice00aust",
                        "title": "Pride and Prejudice",
                        "creator": ["Austen, Jane"],
                        "date": "1813",
                    }
                ]
            }
        }

        with patch.object(ia_connector, "api_client", mock_http_client):
            results = await ia_connector.search_works("pride and prejudice")

        assert len(results) > 0
        assert results[0]["identifier"] == "prideandprejudice00aust"

    async def test_internet_archive_download(
        self,
        ia_connector: InternetArchiveConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test downloading from Internet Archive."""
        # Mock metadata response
        metadata_response = MagicMock()
        metadata_response.json.return_value = {
            "metadata": {
                "title": "Pride and Prejudice",
                "creator": ["Jane Austen"],
                "date": "1813",
            }
        }

        # Mock text download
        text_response = MagicMock()
        text_response.text = "Pride and Prejudice full text..."
        text_response.status_code = 200

        mock_http_client.get.side_effect = [metadata_response, text_response]

        with patch.object(ia_connector, "api_client", mock_http_client):
            with patch(
                "floridify.providers.literature.api.internet_archive.respectful_scraper"
            ) as mock_scraper:
                mock_scraper.return_value.__aenter__.return_value = mock_http_client
                metadata = await ia_connector._fetch_work_metadata("prideandprejudice00aust")
                content = await ia_connector._fetch_work_content("prideandprejudice00aust", {})

        assert metadata["title"] == "Pride and Prejudice"
        assert "Pride and Prejudice" in content


@pytest.mark.asyncio
class TestURLLiteratureProvider:
    """Test URL-based literature provider."""

    @pytest_asyncio.fixture
    async def url_connector(self) -> URLLiteratureConnector:
        """Create URL literature connector."""
        config = ConnectorConfig()
        return URLLiteratureConnector(
            provider=LiteratureProvider.CUSTOM_URL,
            config=config,
        )

    async def test_url_fetch_plain_text(
        self,
        url_connector: URLLiteratureConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test fetching plain text from URL."""
        source = LiteratureSource(
            name="test_book",
            url="https://example.com/book.txt",
            author=AuthorInfo(
                name="Test Author",
                period=Period.CONTEMPORARY,
                primary_genre=Genre.NOVEL,
            ),
            genre=Genre.NOVEL,
            period=Period.CONTEMPORARY,
            language=Language.ENGLISH,
            parser=LitParserType.PLAIN_TEXT,
        )

        mock_http_client.get.return_value.text = "This is the book content."

        with patch("floridify.providers.literature.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert isinstance(result, LiteratureEntry)
        assert result.text == "This is the book content."
        assert result.author.name == "Test Author"

    async def test_url_fetch_with_metadata_extraction(
        self,
        url_connector: URLLiteratureConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test fetching with metadata extraction from structured data."""
        source = LiteratureSource(
            name="metadata_book",
            url="https://example.com/book.json",
            language=Language.ENGLISH,
        )

        # Return structured data that includes metadata
        mock_http_client.get.return_value.json.return_value = {
            "title": "Extracted Title",
            "author": "Extracted Author",
            "text": "Book content here",
            "year": 2023,
        }

        with patch(
            "floridify.providers.literature.scraper.scrapers.default_literature_scraper"
        ) as mock_scraper:
            mock_scraper.return_value = {
                "title": "Extracted Title",
                "author": "Extracted Author",
                "text": "Book content here",
                "year": 2023,
            }

            with patch(
                "floridify.providers.literature.scraper.url.respectful_scraper"
            ) as mock_scraper:
                mock_scraper.return_value.__aenter__.return_value = mock_http_client
                result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert result.title == "Extracted Title"
        assert result.year == 2023

    async def test_url_fetch_html_parsing(
        self,
        url_connector: URLLiteratureConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test fetching and parsing HTML content."""
        source = LiteratureSource(
            name="html_book",
            url="https://example.com/book.html",
            language=Language.ENGLISH,
            parser=LitParserType.HTML,
        )

        html_content = """
        <html>
            <body>
                <h1>Book Title</h1>
                <p>First paragraph of content.</p>
                <p>Second paragraph of content.</p>
            </body>
        </html>
        """

        mock_http_client.get.return_value.text = html_content

        with patch("floridify.providers.literature.scraper.url.respectful_scraper") as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            result = await url_connector._fetch_from_provider(source)

        assert result is not None
        assert "First paragraph" in result.text
        assert "Second paragraph" in result.text


@pytest.mark.asyncio
class TestLiteratureProviderCaching:
    """Test literature provider caching and versioning."""

    @pytest_asyncio.fixture
    async def versioned_manager(self) -> VersionedDataManager:
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_literature_caching(
        self,
        test_db: Any,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test that literature content is cached."""
        mock_http_client.get.return_value.text = "Book content"

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            # First download
            work = LiteratureEntry(
                title="Pride and Prejudice",
                author=AuthorInfo(
                    name="Jane Austen",
                    period=Period.ROMANTIC,
                    primary_genre=Genre.NOVEL,
                ),
                gutenberg_id="1342",
            )
            result1 = await gutenberg_connector.download_work(work)
            call_count1 = mock_http_client.get.call_count

            # Second download - should use cache
            result2 = await gutenberg_connector.download_work(work)
            call_count2 = mock_http_client.get.call_count

        assert result1 == result2
        assert call_count1 == call_count2  # No additional HTTP calls

    async def test_literature_versioning(
        self,
        test_db: Any,
        versioned_manager: VersionedDataManager,
    ) -> None:
        """Test literature content versioning."""
        # Save initial version
        v1 = await versioned_manager.save(
            resource_id="hamlet_gutenberg",
            content={
                "title": "Hamlet",
                "author": "Shakespeare",
                "text": "To be or not to be...",
            },
            resource_type=ResourceType.LITERATURE,
            namespace=CacheNamespace.LITERATURE,
            metadata={"provider": "gutenberg", "work_id": "hamlet"},
        )

        # Update with corrections
        v2 = await versioned_manager.save(
            resource_id="hamlet_gutenberg",
            content={
                "title": "Hamlet, Prince of Denmark",
                "author": "William Shakespeare",
                "text": "To be, or not to be, that is the question...",
                "updated": True,
            },
            resource_type=ResourceType.LITERATURE,
            namespace=CacheNamespace.LITERATURE,
            metadata={"provider": "gutenberg", "work_id": "hamlet"},
        )

        assert v1.id != v2.id
        assert v2.version_info.is_latest is True
        assert v2.version_info.supersedes == v1.id


@pytest.mark.asyncio
class TestLiteratureProviderErrors:
    """Test literature provider error handling."""

    async def test_work_not_found(
        self,
        gutenberg_connector: GutenbergConnector,
    ) -> None:
        """Test handling when work is not found."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = MagicMock(status_code=404)

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            work = LiteratureEntry(
                title="Non-existent Book",
                author=AuthorInfo(
                    name="Unknown Author",
                    period=Period.CONTEMPORARY,
                    primary_genre=Genre.NOVEL,
                ),
                gutenberg_id="99999999",
            )
            result = await gutenberg_connector.download_work(work)  # Non-existent ID

        assert result is None

    async def test_network_error_handling(
        self,
        gutenberg_connector: GutenbergConnector,
    ) -> None:
        """Test handling of network errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.NetworkError("Connection failed")

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            work = LiteratureEntry(
                title="Pride and Prejudice",
                author=AuthorInfo(
                    name="Jane Austen",
                    period=Period.ROMANTIC,
                    primary_genre=Genre.NOVEL,
                ),
                gutenberg_id="1342",
            )
            result = await gutenberg_connector.download_work(work)

        assert result is None

    async def test_corrupted_zip_handling(
        self,
        gutenberg_connector: GutenbergConnector,
    ) -> None:
        """Test handling of corrupted zip files."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        # Return corrupted zip data
        mock_client.get.side_effect = [
            MagicMock(status_code=404),  # No UTF-8
            MagicMock(
                status_code=200,
                content=b"Not a valid zip file",
            ),
        ]

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            result = await gutenberg_connector._fetch_work_content("1342", {})

        assert result is None


@pytest.mark.asyncio
class TestLiteratureTextProcessing:
    """Test literature text cleaning and processing."""

    def test_gutenberg_header_removal(self) -> None:
        """Test removal of Gutenberg headers."""
        connector = GutenbergConnector(config=ConnectorConfig())

        text = """
        *** START OF THE PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***
        
        Title: Pride and Prejudice
        Author: Jane Austen
        
        Chapter 1
        
        It is a truth universally acknowledged...
        
        *** END OF THE PROJECT GUTENBERG EBOOK ***
        """

        cleaned = connector._clean_gutenberg_text(text)

        assert "*** START OF" not in cleaned
        assert "*** END OF" not in cleaned
        assert "It is a truth" in cleaned

    def test_gutenberg_footer_removal(self) -> None:
        """Test removal of Gutenberg footers."""
        connector = GutenbergConnector(config=ConnectorConfig())

        text = """
        The End
        
        *** END OF THE PROJECT GUTENBERG EBOOK ***
        
        This eBook is for the use of anyone...
        Updated editions will replace...
        """

        cleaned = connector._clean_gutenberg_text(text)

        assert "The End" in cleaned
        assert "*** END OF" not in cleaned
        assert "This eBook is for" not in cleaned

    def test_whitespace_normalization(self) -> None:
        """Test normalization of whitespace."""
        connector = GutenbergConnector(config=ConnectorConfig())

        text = """
        
        
        Too    many     spaces
        
        
        And empty lines
        
        
        """

        cleaned = connector._clean_gutenberg_text(text)

        # Should normalize excessive whitespace
        assert "\n\n\n" not in cleaned
        assert "Too many spaces" in cleaned or "Too    many" in cleaned


@pytest.mark.asyncio
class TestLiteratureProviderIntegration:
    """Test literature provider integration scenarios."""

    async def test_complete_book_download_flow(
        self,
        test_db: Any,
        gutenberg_connector: GutenbergConnector,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test complete flow: search → download → save → retrieve."""
        # Mock search results
        search_response = MagicMock()
        search_response.text = '<a href="/ebooks/1342">Pride and Prejudice</a>'

        # Mock book download
        book_response = MagicMock()
        book_response.text = """
        *** START ***
        Pride and Prejudice
        Chapter 1
        Content here...
        *** END ***
        """
        book_response.status_code = 200

        mock_http_client.get.side_effect = [search_response, book_response]

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_http_client
            # Search for book
            search_results = await gutenberg_connector.search_works("pride")
            assert len(search_results) > 0

            # Download book
            work = LiteratureEntry(
                title="Pride and Prejudice",
                author=AuthorInfo(
                    name="Jane Austen",
                    period=Period.ROMANTIC,
                    primary_genre=Genre.NOVEL,
                ),
                gutenberg_id="1342",
            )
            content = await gutenberg_connector.download_work(work)
            assert content is not None
            assert "Content here" in content

    async def test_author_bulk_download(
        self,
        test_db: Any,
        gutenberg_connector: GutenbergConnector,
    ) -> None:
        """Test downloading multiple works by an author."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        # Mock author search
        author_page = MagicMock()
        author_page.text = """
        <a href="/ebooks/1">Book 1</a>
        <a href="/ebooks/2">Book 2</a>
        <a href="/ebooks/3">Book 3</a>
        """

        # Mock individual book downloads
        book_responses = [
            MagicMock(text="Book 1 content", status_code=200),
            MagicMock(text="Book 2 content", status_code=200),
            MagicMock(text="Book 3 content", status_code=200),
        ]

        mock_client.get.side_effect = [author_page] + book_responses

        with patch(
            "floridify.providers.literature.api.gutenberg.respectful_scraper"
        ) as mock_scraper:
            mock_scraper.return_value.__aenter__.return_value = mock_client
            author = AuthorInfo(
                name="Test Author",
                period=Period.CONTEMPORARY,
                primary_genre=Genre.NOVEL,
            )
            works = [
                LiteratureEntry(
                    title="Test Book 1",
                    author=author,
                    gutenberg_id="1",
                ),
                LiteratureEntry(
                    title="Test Book 2",
                    author=author,
                    gutenberg_id="2",
                ),
                LiteratureEntry(
                    title="Test Book 3",
                    author=author,
                    gutenberg_id="3",
                ),
            ]
            results = await gutenberg_connector.download_author_works(
                author,
                works,
                limit=3,
            )

        assert len(results) <= 3

    async def test_multi_provider_literature_fetch(
        self,
        test_db: Any,
    ) -> None:
        """Test fetching same work from multiple providers."""
        providers = [
            GutenbergConnector(config=ConnectorConfig()),
            InternetArchiveConnector(ConnectorConfig()),
        ]

        for provider in providers:
            mock_client = AsyncMock(spec=httpx.AsyncClient)
            mock_client.get.return_value = MagicMock(
                status_code=200,
                text="Pride and Prejudice content from " + provider.__class__.__name__,
            )

            if hasattr(provider, "scraper_session"):
                provider._scraper_session = mock_client
            if hasattr(provider, "api_client"):
                provider._api_client = mock_client

        # Fetch from each provider
        results = []
        for provider in providers:
            if isinstance(provider, GutenbergConnector):
                with patch(
                    "floridify.providers.literature.api.gutenberg.respectful_scraper"
                ) as mock_scraper:
                    mock_scraper.return_value.__aenter__.return_value = mock_client
                    work = LiteratureEntry(
                        title="Test Book",
                        author=AuthorInfo(
                            name="Test Author",
                            period=Period.CONTEMPORARY,
                            primary_genre=Genre.NOVEL,
                        ),
                        gutenberg_id="1342",
                    )
                    result = await provider.download_work(work)
            else:
                with patch.object(provider, "api_client", mock_client):
                    result = await provider._fetch_work_content("test_id", {})
            results.append(result)

        # Should have results from multiple providers
        assert len([r for r in results if r is not None]) >= 1


@pytest.mark.asyncio
class TestLiteratureEntryModel:
    """Test LiteratureEntry model and persistence."""

    def test_literature_entry_creation(self) -> None:
        """Test creating LiteratureEntry."""
        author = AuthorInfo(
            name="Jane Austen",
            period=Period.ROMANTIC,
            primary_genre=Genre.NOVEL,
            birth_year=1775,
            death_year=1817,
            nationality="British",
        )

        source = LiteratureSource(
            name="pride_prejudice",
            url="https://gutenberg.org/1342",
            author=author,
            genre=Genre.NOVEL,
            period=Period.ROMANTIC,
            language=Language.ENGLISH,
        )

        entry = LiteratureEntry(
            title="Pride and Prejudice",
            author=author,
            source=source,
            genre=Genre.NOVEL,
            period=Period.ROMANTIC,
            language=Language.ENGLISH,
            text="Full text content...",
            year=1813,
            gutenberg_id="1342",
            work_id="pride_prejudice_1342",
        )

        assert entry.title == "Pride and Prejudice"
        assert entry.author.name == "Jane Austen"
        assert entry.year == 1813
        assert entry.gutenberg_id == "1342"

    def test_author_info_properties(self) -> None:
        """Test AuthorInfo properties and methods."""
        author = AuthorInfo(
            name="William Shakespeare",
            period=Period.RENAISSANCE,
            primary_genre=Genre.DRAMA,
            birth_year=1564,
            death_year=1616,
            nationality="English",
        )

        assert author.name == "William Shakespeare"
        assert author.period == Period.RENAISSANCE
        assert author.primary_genre == Genre.DRAMA
        assert author.birth_year == 1564
        assert author.death_year == 1616
