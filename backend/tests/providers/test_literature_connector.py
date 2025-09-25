"""Literature connector tests using a mock transport."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from floridify.models.base import Language
from floridify.models.literature import AuthorInfo, Genre, Period
from floridify.providers.literature.models import LiteratureSource, ParserType
from floridify.providers.literature.scraper.url import URLLiteratureConnector


@pytest_asyncio.fixture
async def connector() -> URLLiteratureConnector:
    """Provide connector with deterministic HTTP responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/text"):
            return httpx.Response(200, text="Sample text for testing literature connector.")
        return httpx.Response(404, text="")

    session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = URLLiteratureConnector()
    connector._scraper_session = session
    try:
        yield connector
    finally:
        await connector.close()


@pytest.mark.asyncio
async def test_fetch_source_returns_entry(connector: URLLiteratureConnector, test_db) -> None:
    source = LiteratureSource(
        name="test_work",
        url="https://example.com/text",
        parser=ParserType.PLAIN_TEXT,
        author=AuthorInfo(
            name="Test Author",
            period=Period.CONTEMPORARY,
            primary_genre=Genre.NOVEL,
            language=Language.ENGLISH,
        ),
    )

    entry = await connector.fetch_source(source)
    assert entry is not None
    assert entry.title == "test_work"
    assert entry.author.name == "Test Author"
    assert "sample" in entry.text.lower()
    assert len(entry.extracted_vocabulary) >= 1 or entry.metadata
