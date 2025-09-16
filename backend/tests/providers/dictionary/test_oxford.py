"""Tests for Oxford Dictionary API provider."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.dictionary.api.oxford import OxfordConnector


@pytest_asyncio.fixture
async def oxford_connector() -> OxfordConnector:
    """Create Oxford connector for testing."""
    app_id = os.getenv("OXFORD_APP_ID", "test_app_id")
    api_key = os.getenv("OXFORD_APP_KEY", "test_app_key")
    return OxfordConnector(app_id=app_id, api_key=api_key)


@pytest_asyncio.fixture
def mock_oxford_response() -> dict[str, Any]:
    """Mock Oxford API response."""
    return {
        "id": "test",
        "metadata": {
            "operation": "retrieve",
            "provider": "Oxford University Press",
            "schema": "RetrieveEntry",
        },
        "results": [
            {
                "id": "test",
                "language": "en-gb",
                "lexicalEntries": [
                    {
                        "entries": [
                            {
                                "etymologies": [
                                    "late Middle English: from Latin testum 'earthen pot', related to testa 'jug, shell'"
                                ],
                                "pronunciations": [
                                    {
                                        "audioFile": "https://audio.oxforddictionaries.com/en/mp3/test_gb_1.mp3",
                                        "dialects": ["British English"],
                                        "phoneticNotation": "IPA",
                                        "phoneticSpelling": "/tɛst/",
                                    }
                                ],
                                "senses": [
                                    {
                                        "definitions": [
                                            "a procedure intended to establish the quality, performance, or reliability of something"
                                        ],
                                        "examples": [
                                            {"text": "a spelling test"},
                                            {"text": "the test results were encouraging"},
                                        ],
                                        "id": "m_en_gbus1041510.006",
                                        "synonyms": [
                                            {"text": "trial"},
                                            {"text": "experiment"},
                                            {"text": "examination"},
                                        ],
                                        "subsenses": [
                                            {
                                                "definitions": [
                                                    "a short written or spoken examination"
                                                ],
                                                "examples": [{"text": "a driving test"}],
                                                "id": "m_en_gbus1041510.009",
                                            }
                                        ],
                                    },
                                    {
                                        "definitions": [
                                            "a movable hearth used for separating gold or silver from lead"
                                        ],
                                        "domains": [{"id": "metallurgy", "text": "Metallurgy"}],
                                        "id": "m_en_gbus1041510.017",
                                    },
                                ],
                            }
                        ],
                        "language": "en-gb",
                        "lexicalCategory": {"id": "noun", "text": "Noun"},
                        "text": "test",
                    },
                    {
                        "entries": [
                            {
                                "pronunciations": [
                                    {
                                        "phoneticNotation": "IPA",
                                        "phoneticSpelling": "/tɛst/",
                                    }
                                ],
                                "senses": [
                                    {
                                        "definitions": [
                                            "take measures to check the quality, performance, or reliability of something"
                                        ],
                                        "examples": [
                                            {"text": "this range has not been tested on animals"}
                                        ],
                                        "id": "m_en_gbus1041510.019",
                                    }
                                ],
                            }
                        ],
                        "language": "en-gb",
                        "lexicalCategory": {"id": "verb", "text": "Verb"},
                        "text": "test",
                    },
                ],
                "type": "headword",
                "word": "test",
            }
        ],
    }


class TestOxfordConnector:
    """Test Oxford connector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, oxford_connector: OxfordConnector) -> None:
        """Test connector initialization."""
        assert oxford_connector.provider == DictionaryProvider.OXFORD
        assert oxford_connector.app_id is not None
        assert oxford_connector.api_key is not None
        assert oxford_connector.config.rate_limit_config is not None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(
        self,
        oxford_connector: OxfordConnector,
        mock_oxford_response: dict[str, Any],
        test_db,
    ) -> None:
        """Test successful fetch from provider."""
        # Mock the API client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json = lambda: mock_oxford_response  # json() is a method
        mock_response.raise_for_status = lambda: None  # raise_for_status is synchronous
        mock_client.get.return_value = mock_response

        oxford_connector._api_client = mock_client

        result = await oxford_connector._fetch_from_provider("test")

        assert result is not None
        assert isinstance(result, dict)
        assert result["provider"] == DictionaryProvider.OXFORD.value
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(self, oxford_connector: OxfordConnector) -> None:
        """Test handling of word not found."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.NOT_FOUND
        mock_response.raise_for_status = lambda: None
        mock_client.get.return_value = mock_response

        oxford_connector._api_client = mock_client

        result = await oxford_connector._fetch_from_provider("xyznonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_error(
        self, oxford_connector: OxfordConnector
    ) -> None:
        """Test error handling."""
        # Mock the API client to raise an exception
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.RequestError("Network error")

        oxford_connector._api_client = mock_client

        result = await oxford_connector._fetch_from_provider("test")

        assert result is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_fetch_from_provider_http_error(
        self, oxford_connector: OxfordConnector
    ) -> None:
        """Test handling of HTTP errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.INTERNAL_SERVER_ERROR
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=None, response=mock_response
        )
        mock_client.get.return_value = mock_response

        oxford_connector._api_client = mock_client

        result = await oxford_connector._fetch_from_provider("test")

        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self, oxford_connector: OxfordConnector) -> None:
        """Test rate limiting configuration."""
        assert oxford_connector.rate_limiter is not None

        # Check rate limit configuration
        config = oxford_connector.config.rate_limit_config
        assert config is not None
        assert config.base_requests_per_second == 2.0  # API_CONSERVATIVE preset

    @pytest.mark.asyncio
    async def test_fetch_and_save_integration(
        self,
        oxford_connector: OxfordConnector,
        mock_oxford_response: dict[str, Any],
        test_db,
    ) -> None:
        """Test the full fetch and save flow."""
        # Mock successful API response
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json = lambda: mock_oxford_response
        mock_response.raise_for_status = lambda: None
        mock_client.get.return_value = mock_response

        oxford_connector._api_client = mock_client

        # Use the public fetch method which handles caching/saving
        result = await oxford_connector.fetch("test")

        assert result is not None
        assert result["provider"] == DictionaryProvider.OXFORD.value
        
        # Verify it can be retrieved from cache
        cached_result = await oxford_connector.get("test")
        assert cached_result is not None
        assert cached_result["provider"] == DictionaryProvider.OXFORD.value
