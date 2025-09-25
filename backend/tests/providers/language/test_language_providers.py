"""Language provider parser and connector tests without external network calls."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
import pytest_asyncio

from floridify.models.base import Language
from floridify.providers.language.models import (
    LanguageEntry,
    LanguageProvider,
    LanguageSource,
    ParserType,
)
from floridify.providers.language.parsers import (
    parse_csv_words,
    parse_json_vocabulary,
    parse_text_lines,
)
from floridify.providers.language.scraper.url import URLLanguageConnector


class TestLanguageParsers:
    """Parser behaviour remains deterministic."""

    def test_parse_text_lines(self) -> None:
        content = """
        # Comment line
        hello
        world
        foo bar
        # Another comment
        python
        """
        words, phrases = parse_text_lines(content, Language.ENGLISH)
        assert sorted(words) == ["hello", "python", "world"]
        assert phrases == ["foo bar"]

    def test_parse_json_vocabulary(self) -> None:
        payload = {
            "words": ["alpha", "beta"],
            "phrases": ["alpha beta"],
            "vocabulary": ["gamma"],
        }
        words, phrases = parse_json_vocabulary(payload, Language.ENGLISH)
        assert sorted(words) == ["alpha", "beta", "gamma"]
        assert phrases == ["alpha beta"]

    def test_parse_json_string_input(self) -> None:
        payload = json.dumps({"words": ["one"], "phrases": []})
        words, phrases = parse_json_vocabulary(payload, Language.ENGLISH)
        assert words == ["one"]
        assert phrases == []

    def test_parse_csv_words(self) -> None:
        csv_content = """word,frequency,type
apple,1,noun
"golden apple",2,phrase
"""
        words, phrases = parse_csv_words(csv_content, Language.ENGLISH)
        assert words == ["apple"]
        assert phrases == ["golden apple"]


@pytest_asyncio.fixture
async def connector() -> tuple[URLLanguageConnector, Callable[[], int]]:
    """URLLanguageConnector backed by a mock transport."""
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        if request.url.path.endswith("/text"):
            return httpx.Response(200, text="alpha\nbeta\nalpha beta")
        if request.url.path.endswith("/json"):
            payload = {"vocabulary": ["gamma"], "phrases": ["gamma ray"]}
            return httpx.Response(200, text=json.dumps(payload))
        return httpx.Response(404, text="")

    session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = URLLanguageConnector()
    connector._scraper_session = session
    try:
        yield connector, lambda: call_count["value"]
    finally:
        await connector.close()


@pytest.mark.asyncio
async def test_fetch_source_returns_entry(
    connector: tuple[URLLanguageConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    source = LanguageSource(
        name="test_source",
        url="https://example.com/text",
        parser=ParserType.TEXT_LINES,
        language=Language.ENGLISH,
    )

    entry = await instance.fetch_source(source)
    assert isinstance(entry, LanguageEntry)
    assert sorted(entry.vocabulary) == ["alpha", "alpha beta", "beta"]
    assert entry.provider == LanguageProvider.CUSTOM_URL
    assert counter() == 1


@pytest.mark.asyncio
async def test_fetch_source_uses_cache(
    connector: tuple[URLLanguageConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    source = LanguageSource(
        name="cached_source",
        url="https://example.com/json",
        parser=ParserType.JSON_VOCABULARY,
        language=Language.ENGLISH,
    )

    first = await instance.fetch_source(source)
    second = await instance.fetch_source(source)

    assert first is not None and second is not None
    assert counter() == 1
