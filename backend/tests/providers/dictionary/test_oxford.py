"""OxfordConnector parsing tests using mock transport."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
import pytest_asyncio

from floridify.caching.models import VersionConfig
from floridify.providers.dictionary.api.oxford import OxfordConnector
from floridify.providers.dictionary.models import DictionaryProviderEntry

OXFORD_RESPONSE = {
    "results": [
        {
            "lexicalEntries": [
                {
                    "lexicalCategory": {"id": "noun"},
                    "pronunciations": [{"phoneticSpelling": "tɛst", "dialects": ["British"]}],
                    "entries": [
                        {
                            "etymologies": ["Latin testum"],
                            "senses": [
                                {
                                    "definitions": ["a procedure for critical evaluation"],
                                    "examples": [{"text": "a driving test"}],
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ],
}


@pytest_asyncio.fixture
async def connector() -> tuple[OxfordConnector, Callable[[], int]]:
    """Provide an Oxford connector backed by a mock HTTP transport."""
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        if request.url.path.endswith("/test"):
            return httpx.Response(200, text=json.dumps(OXFORD_RESPONSE))
        return httpx.Response(404, text="")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    instance = OxfordConnector(app_id="dummy", api_key="dummy")
    instance._api_client = client
    try:
        yield instance, lambda: call_count["value"]
    finally:
        await instance.close()


@pytest.mark.asyncio
async def test_fetch_parses_entry(
    connector: tuple[OxfordConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    entry = await instance.fetch("test", config=VersionConfig(force_rebuild=True))

    assert isinstance(entry, DictionaryProviderEntry)
    assert entry.word == "test"
    assert entry.pronunciation == "tɛst"
    assert entry.etymology == "Latin testum"
    assert entry.definitions[0]["text"] == "a procedure for critical evaluation"
    assert entry.definitions[0]["example_ids"], "Definitions should reference saved examples"
    assert counter() == 1


@pytest.mark.asyncio
async def test_missing_word_returns_none(
    connector: tuple[OxfordConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    assert await instance.fetch("absent", config=VersionConfig(force_rebuild=True)) is None
    assert counter() == 1


@pytest.mark.asyncio
async def test_http_error_returns_none(test_db) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    instance = OxfordConnector(app_id="dummy", api_key="dummy")
    instance._api_client = client
    try:
        assert await instance.fetch("test", config=VersionConfig(force_rebuild=True)) is None
    finally:
        await instance.close()
