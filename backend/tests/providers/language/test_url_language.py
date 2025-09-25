"""URL language connector tests without external network access."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from floridify.models.base import Language
from floridify.providers.language.models import LanguageEntry, LanguageSource, ParserType
from floridify.providers.language.scraper.url import URLLanguageConnector


@pytest_asyncio.fixture
async def connector() -> URLLanguageConnector:
    """Connector backed by a mock transport returning deterministic payloads."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/text"):
            return httpx.Response(200, text="apple\nbanana\nred apple\n# comment")
        if path.endswith("/json"):
            payload = {
                "vocabulary": ["pear", "peach"],
                "phrases": ["golden pear"],
                "idioms": ["peach of a job"],
            }
            return httpx.Response(200, text=json.dumps(payload))
        if path.endswith("/csv"):
            csv_data = "word,frequency\napple,10\nbanana,5\nyellow banana,2"
            return httpx.Response(200, text=csv_data)
        return httpx.Response(404, text="")

    transport = httpx.MockTransport(handler)
    session = httpx.AsyncClient(transport=transport)

    connector = URLLanguageConnector()
    connector._scraper_session = session
    try:
        yield connector
    finally:
        await connector.close()


@pytest.mark.asyncio
async def test_fetch_source_text(connector: URLLanguageConnector, test_db) -> None:
    """Text parser sources return words and phrases."""
    source = LanguageSource(
        name="text_source",
        url="https://example.com/text",
        language=Language.ENGLISH,
        parser=ParserType.TEXT_LINES,
        description="Sample text source",
    )

    entry = await connector.fetch_source(source)
    assert isinstance(entry, LanguageEntry)
    assert set(entry.vocabulary) == {"apple", "banana", "red apple"}
    assert entry.phrases == ["red apple"]
    assert entry.source.parser is ParserType.TEXT_LINES

    cached = await connector.get(source.name)
    assert cached is not None
    assert cached.vocabulary_count == 3


@pytest.mark.asyncio
async def test_fetch_source_json(connector: URLLanguageConnector, test_db) -> None:
    """JSON parser sources merge vocabulary buckets."""
    source = LanguageSource(
        name="json_source",
        url="https://example.com/json",
        parser=ParserType.JSON_VOCABULARY,
        language=Language.ENGLISH,
    )

    entry = await connector.fetch_source(source)
    assert isinstance(entry, LanguageEntry)
    assert set(entry.vocabulary) == {"pear", "peach", "golden pear", "peach of a job"}
    assert entry.phrases == ["golden pear"]
    assert entry.idiom_count == 1


@pytest.mark.asyncio
async def test_fetch_source_csv(connector: URLLanguageConnector, test_db) -> None:
    """CSV parser recognises phrases from quoted rows."""
    source = LanguageSource(
        name="csv_source",
        url="https://example.com/csv",
        parser=ParserType.CSV_WORDS,
        language=Language.ENGLISH,
    )

    entry = await connector.fetch_source(source)
    assert isinstance(entry, LanguageEntry)
    assert "apple" in entry.vocabulary
    assert "yellow banana" in entry.phrases


@pytest.mark.asyncio
async def test_fetch_source_not_found(connector: URLLanguageConnector, test_db) -> None:
    """Missing resources return None and do not raise."""
    source = LanguageSource(
        name="missing",
        url="https://example.com/missing",
        language=Language.ENGLISH,
    )

    entry = await connector.fetch_source(source)
    assert entry is None
