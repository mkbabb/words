"""Wikipedia provider tests — mocked HTTP, no network required."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from floridify.providers.dictionary.api.wikipedia_provider import WikipediaConnector, _WIKI_API


MOCK_EXTRACT_RESPONSE = {
    "query": {
        "pages": {
            "12345": {
                "pageid": 12345,
                "title": "Bank",
                "extract": (
                    "A bank is a financial institution that accepts deposits "
                    "from the public and creates a demand deposit while simultaneously "
                    "making loans. Lending activities can be directly performed by the bank "
                    "or indirectly through capital markets. Banks are important players "
                    "in financial markets and offer financial services such as investment funds."
                ),
            }
        }
    }
}

MOCK_CATEGORIES_RESPONSE = {
    "query": {
        "pages": {
            "12345": {
                "categories": [
                    {"title": "Category:Financial institutions"},
                    {"title": "Category:Banking"},
                    {"title": "Category:Financial services"},
                ]
            }
        }
    }
}

MOCK_NOT_FOUND_RESPONSE = {
    "query": {
        "pages": {
            "-1": {"title": "Xyzzyplugh", "missing": ""}
        }
    }
}


@pytest.fixture
def connector() -> WikipediaConnector:
    return WikipediaConnector()


class TestWikipediaExtractFacts:
    def test_extracts_facts_from_text(self, connector: WikipediaConnector) -> None:
        text = (
            "A bank is a financial institution. "
            "It accepts deposits from the public. "
            "Banks create demand deposits."
        )
        facts = connector._extract_facts(text, "bank")
        assert len(facts) >= 2
        assert any("financial" in f.lower() for f in facts)

    def test_returns_empty_for_no_text(self, connector: WikipediaConnector) -> None:
        assert connector._extract_facts("", "bank") == []

    def test_limits_to_3_facts(self, connector: WikipediaConnector) -> None:
        text = ". ".join([f"Fact number {i} about the word" for i in range(10)])
        facts = connector._extract_facts(text, "test")
        assert len(facts) <= 3


class TestWikipediaDomainInference:
    def test_infers_finance_domain(self, connector: WikipediaConnector) -> None:
        categories = ["Financial institutions", "Banking", "Financial services"]
        assert connector._infer_domain(categories) == "finance"

    def test_infers_biology_domain(self, connector: WikipediaConnector) -> None:
        categories = ["Species described in 1758", "Biology", "Organisms"]
        assert connector._infer_domain(categories) == "biology"

    def test_returns_none_for_generic(self, connector: WikipediaConnector) -> None:
        categories = ["Articles with short description", "Use dmy dates"]
        assert connector._infer_domain(categories) is None


class TestWikipediaFetchMocked:
    @pytest.mark.asyncio
    async def test_fetch_returns_entry_with_metadata(
        self, connector: WikipediaConnector, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test full fetch pipeline with mocked HTTP."""
        import httpx

        def _mock_response(data: dict) -> httpx.Response:
            request = httpx.Request("GET", _WIKI_API)
            return httpx.Response(200, json=data, request=request)

        async def mock_get(self_client, url, **kwargs):
            params = kwargs.get("params", {})
            prop = params.get("prop", "")

            if "extracts" in prop:
                return _mock_response(MOCK_EXTRACT_RESPONSE)
            elif "categories" in prop:
                return _mock_response(MOCK_CATEGORIES_RESPONSE)
            return _mock_response(MOCK_NOT_FOUND_RESPONSE)

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        entry = await connector._fetch_from_provider("bank")
        assert entry is not None
        assert entry.word == "bank"
        assert entry.provider_metadata.get("wikipedia_title") == "Bank"
        assert len(entry.provider_metadata.get("facts", [])) > 0
        assert len(entry.provider_metadata.get("categories", [])) > 0

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_page(
        self, connector: WikipediaConnector, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import httpx

        async def mock_get(self_client, url, **kwargs):
            request = httpx.Request("GET", _WIKI_API)
            return httpx.Response(200, json=MOCK_NOT_FOUND_RESPONSE, request=request)

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        entry = await connector._fetch_from_provider("xyzzyplugh")
        assert entry is None
