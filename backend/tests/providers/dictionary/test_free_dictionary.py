"""FreeDictionaryConnector parsing and caching tests."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
import pytest_asyncio

from floridify.caching.models import VersionConfig
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.models import DictionaryProviderEntry


@pytest_asyncio.fixture
async def connector() -> tuple[FreeDictionaryConnector, Callable[[], int]]:
    """Connector wired to a mock transport that records request count."""
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/test"):
            call_count["value"] += 1
            payload = [
                {
                    "word": "test",
                    "phonetics": [{"text": "/tɛst/"}],
                    "meanings": [
                        {
                            "partOfSpeech": "noun",
                            "definitions": [
                                {
                                    "definition": "an act of testing",
                                    "example": "a spelling test",
                                    "synonyms": ["exam"],
                                    "antonyms": ["guess"],
                                },
                            ],
                        },
                    ],
                },
            ]
            return httpx.Response(200, text=json.dumps(payload))

        return httpx.Response(404, text="[]")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = FreeDictionaryConnector()
    connector._api_client = client
    try:
        yield connector, lambda: call_count["value"]
    finally:
        await connector.close()


@pytest.mark.asyncio
async def test_fetch_returns_entry(
    connector: tuple[FreeDictionaryConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, _ = connector
    entry = await instance.fetch("test", config=VersionConfig(force_rebuild=True))

    assert isinstance(entry, DictionaryProviderEntry)
    assert entry.word == "test"
    assert entry.pronunciation == "/tɛst/"
    assert entry.definitions[0]["definition"] == "an act of testing"
    assert entry.examples == ["a spelling test"]

    cached = await instance.get("test")
    assert cached is not None
    assert cached.word == "test"


@pytest.mark.asyncio
async def test_fetch_uses_cache(
    connector: tuple[FreeDictionaryConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector

    first = await instance.fetch("test", config=VersionConfig(force_rebuild=True))
    second = await instance.fetch("test")

    assert first is not None and second is not None
    assert counter() == 1


@pytest.mark.asyncio
async def test_missing_word_returns_none(
    connector: tuple[FreeDictionaryConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    assert await instance.fetch("absent", config=VersionConfig(force_rebuild=True)) is None
    assert counter() == 0
