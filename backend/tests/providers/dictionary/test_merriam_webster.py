"""MerriamWebsterConnector parsing behaviour tests."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
import pytest_asyncio

from floridify.caching.models import VersionConfig
from floridify.providers.dictionary.api.merriam_webster import MerriamWebsterConnector
from floridify.providers.dictionary.models import DictionaryProviderEntry

MW_RESPONSE = [
    {
        "meta": {"id": "test:1"},
        "hwi": {"hw": "test"},
        "fl": "noun",
        "def": [
            {
                "sseq": [
                    [
                        [
                            "sense",
                            {
                                "sn": "1 a",
                                "dt": [
                                    ["text", "{bc} an act of putting to proof"],
                                    ["vis", [{"t": "the {it}test{/it} was difficult"}]],
                                ],
                            },
                        ],
                    ],
                ],
            },
        ],
        "et": [["text", "Latin testum"]],
    },
]


@pytest.mark.asyncio
async def test_missing_api_key_raises() -> None:
    with pytest.raises(ValueError):
        MerriamWebsterConnector(api_key=None)


@pytest_asyncio.fixture
async def connector() -> tuple[MerriamWebsterConnector, Callable[[], int]]:
    """Connector backed by a mock transport for deterministic results."""
    call_count = {"value": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["value"] += 1
        if request.url.path.endswith("/test"):
            return httpx.Response(200, text=json.dumps(MW_RESPONSE))
        return httpx.Response(200, text="[]")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    instance = MerriamWebsterConnector(api_key="dummy-key")
    instance._api_client = client
    try:
        yield instance, lambda: call_count["value"]
    finally:
        await instance.close()


@pytest.mark.asyncio
async def test_fetch_parses_entry(
    connector: tuple[MerriamWebsterConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    entry = await instance.fetch("test", config=VersionConfig(force_rebuild=True))

    assert isinstance(entry, DictionaryProviderEntry)
    assert entry.word == "test"
    definition_text = entry.definitions[0]["text"]
    assert definition_text.endswith("putting to proof")
    assert definition_text.lstrip(": ") == "an act of putting to proof"
    assert entry.examples == ["the test was difficult"]
    assert entry.etymology == "Latin testum"
    assert counter() == 1


@pytest.mark.asyncio
async def test_fetch_returns_none_for_missing_word(
    connector: tuple[MerriamWebsterConnector, Callable[[], int]],
    test_db,
) -> None:
    instance, counter = connector
    assert await instance.fetch("absent", config=VersionConfig(force_rebuild=True)) is None
    assert counter() == 1  # Only the missing-word request was made


@pytest.mark.asyncio
async def test_fetch_handles_http_error(test_db) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    instance = MerriamWebsterConnector(api_key="dummy-key")
    instance._api_client = client
    try:
        assert await instance.fetch("test", config=VersionConfig(force_rebuild=True)) is None
    finally:
        await instance.close()
