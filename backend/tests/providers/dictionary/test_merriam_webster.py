"""Tests for Merriam-Webster API provider."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.dictionary.api.merriam_webster import MerriamWebsterConnector


@pytest_asyncio.fixture
async def merriam_webster_connector() -> MerriamWebsterConnector:
    """Create Merriam-Webster connector for testing."""
    # Use test API key or skip if not available
    api_key = os.getenv("MERRIAM_WEBSTER_API_KEY", "test_api_key")
    return MerriamWebsterConnector(api_key=api_key)


@pytest_asyncio.fixture
def mock_merriam_webster_response() -> list[dict[str, Any]]:
    """Mock Merriam-Webster API response."""
    return [
        {
            "meta": {
                "id": "test:1",
                "uuid": "123e4567-e89b-12d3-a456-426614174000",
                "sort": "200100",
                "src": "collegiate",
                "section": "alpha",
                "stems": ["test", "tests", "testing", "tested"],
                "offensive": False,
            },
            "hwi": {
                "hw": "test",
                "prs": [
                    {
                        "mw": "ˈtest",
                        "sound": {
                            "audio": "test00001",
                            "ref": "c",
                            "stat": "1",
                        },
                    }
                ],
            },
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
                                        ["text", "a means of testing: such as"],
                                        [
                                            "vis",
                                            [
                                                {
                                                    "t": "a {it}test{/it} of your knowledge",
                                                }
                                            ],
                                        ],
                                    ],
                                },
                            ]
                        ],
                        [
                            [
                                "sense",
                                {
                                    "sn": "1 b",
                                    "dt": [
                                        ["text", "a procedure for critical evaluation"],
                                        [
                                            "vis",
                                            [
                                                {
                                                    "t": "a {it}test{/it} of the new vaccine",
                                                }
                                            ],
                                        ],
                                    ],
                                },
                            ]
                        ],
                    ]
                }
            ],
            "et": [
                [
                    "text",
                    "Middle English, vessel in which metals were assayed, from Anglo-French {it}test{/it}, from Latin {it}testum{/it} earthen pot",
                ]
            ],
            "date": "14th century{ds||1|a|}",
            "shortdef": [
                "a means of testing",
                "a procedure for critical evaluation",
                "a positive result in such a test",
            ],
        }
    ]


class TestMerriamWebsterConnector:
    """Test Merriam-Webster connector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, merriam_webster_connector: MerriamWebsterConnector) -> None:
        """Test connector initialization."""
        assert merriam_webster_connector.provider == DictionaryProvider.MERRIAM_WEBSTER
        assert merriam_webster_connector.api_key is not None
        assert merriam_webster_connector.config.rate_limit_config is not None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(
        self,
        merriam_webster_connector: MerriamWebsterConnector,
        mock_merriam_webster_response: list[dict[str, Any]],
        test_db,
    ) -> None:
        """Test successful fetch from provider."""
        # Mock the API client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json = lambda: mock_merriam_webster_response  # json() is a method
        mock_response.raise_for_status = lambda: None  # raise_for_status is synchronous
        mock_client.get.return_value = mock_response

        merriam_webster_connector._api_client = mock_client

        # Bypass the cache decorator by calling the wrapped function directly
        if hasattr(merriam_webster_connector._fetch_from_provider, "__wrapped__"):
            result = await merriam_webster_connector._fetch_from_provider.__wrapped__(
                merriam_webster_connector, "test"
            )
        else:
            result = await merriam_webster_connector._fetch_from_provider("test")

        assert result is not None
        assert isinstance(result, dict)
        assert result["provider"] == DictionaryProvider.MERRIAM_WEBSTER.value
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(
        self, merriam_webster_connector: MerriamWebsterConnector
    ) -> None:
        """Test handling of word not found."""
        # Mock API response for non-existent word
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json = lambda: []  # Empty response for not found
        mock_response.raise_for_status = lambda: None
        mock_client.get.return_value = mock_response

        merriam_webster_connector._api_client = mock_client

        # Bypass the cache decorator
        if hasattr(merriam_webster_connector._fetch_from_provider, "__wrapped__"):
            result = await merriam_webster_connector._fetch_from_provider.__wrapped__(
                merriam_webster_connector, "xyznonexistent"
            )
        else:
            result = await merriam_webster_connector._fetch_from_provider("xyznonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_error(
        self, merriam_webster_connector: MerriamWebsterConnector
    ) -> None:
        """Test error handling."""
        # Mock the API client to raise an exception
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.RequestError("Network error")

        merriam_webster_connector._api_client = mock_client

        # Bypass the cache decorator
        if hasattr(merriam_webster_connector._fetch_from_provider, "__wrapped__"):
            result = await merriam_webster_connector._fetch_from_provider.__wrapped__(
                merriam_webster_connector, "test"
            )
        else:
            result = await merriam_webster_connector._fetch_from_provider("test")

        assert result is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_fetch_from_provider_http_error(
        self, merriam_webster_connector: MerriamWebsterConnector
    ) -> None:
        """Test handling of HTTP errors."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.INTERNAL_SERVER_ERROR
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=None, response=mock_response
        )
        mock_client.get.return_value = mock_response

        merriam_webster_connector._api_client = mock_client

        if hasattr(merriam_webster_connector._fetch_from_provider, "__wrapped__"):
            result = await merriam_webster_connector._fetch_from_provider.__wrapped__(
                merriam_webster_connector, "test"
            )
        else:
            result = await merriam_webster_connector._fetch_from_provider("test")

        assert result is None

    @pytest.mark.asyncio
    async def test_rate_limiting(self, merriam_webster_connector: MerriamWebsterConnector) -> None:
        """Test rate limiting configuration."""
        assert merriam_webster_connector.rate_limiter is not None

        # Check rate limit configuration
        config = merriam_webster_connector.config.rate_limit_config
        assert config is not None
        assert config.base_requests_per_second == 5.0  # API_STANDARD preset

    @pytest.mark.asyncio
    async def test_fetch_and_save_integration(
        self,
        merriam_webster_connector: MerriamWebsterConnector,
        mock_merriam_webster_response: list[dict[str, Any]],
        test_db,
    ) -> None:
        """Test the full fetch and save flow."""
        # Mock successful API response
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = AsyncMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json = lambda: mock_merriam_webster_response
        mock_response.raise_for_status = lambda: None
        mock_client.get.return_value = mock_response

        merriam_webster_connector._api_client = mock_client

        # Use the public fetch method which handles caching/saving
        result = await merriam_webster_connector.fetch("test")

        assert result is not None
        assert result["provider"] == DictionaryProvider.MERRIAM_WEBSTER.value
        
        # Verify it can be retrieved from cache
        cached_result = await merriam_webster_connector.get("test")
        assert cached_result is not None
        assert cached_result["provider"] == DictionaryProvider.MERRIAM_WEBSTER.value
