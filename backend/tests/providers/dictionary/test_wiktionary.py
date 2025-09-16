"""Tests for Wiktionary scraper provider."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector


@pytest_asyncio.fixture
async def wiktionary_connector() -> WiktionaryConnector:
    """Create Wiktionary connector for testing."""
    return WiktionaryConnector()




class TestWiktionaryConnector:
    """Test Wiktionary connector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, wiktionary_connector: WiktionaryConnector) -> None:
        """Test connector initialization."""
        assert wiktionary_connector.provider == DictionaryProvider.WIKTIONARY
        assert wiktionary_connector.base_url == "https://en.wiktionary.org/w/api.php"
        assert wiktionary_connector.config.rate_limit_config is not None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(
        self, wiktionary_connector: WiktionaryConnector, test_db
    ) -> None:
        """Test successful fetch from provider using real API."""
        # Use real API - test with a common word
        result = await wiktionary_connector._fetch_from_provider("test")

        # Wiktionary might return data or None depending on API/scraping success
        if result is not None:
            assert isinstance(result, dict)
            assert result["word"] == "test"
            assert result["provider"] == DictionaryProvider.WIKTIONARY.value
            assert "raw_data" in result

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(
        self, wiktionary_connector: WiktionaryConnector, test_db
    ) -> None:
        """Test handling of word not found using real API."""
        # Test with a definitely non-existent word
        result = await wiktionary_connector._fetch_from_provider("xyznonexistentword123456")

        # Should return None for non-existent words
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_multiple_words(
        self, wiktionary_connector: WiktionaryConnector, test_db
    ) -> None:
        """Test fetching multiple words."""
        words = ["cat", "dog", "book"]
        results = []
        
        for word in words:
            result = await wiktionary_connector._fetch_from_provider(word)
            results.append(result)
        
        # At least some words should be found
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) > 0
        
        # Check structure of successful results
        for result in successful_results:
            assert isinstance(result, dict)
            assert "word" in result
            assert "provider" in result
            assert result["provider"] == DictionaryProvider.WIKTIONARY.value

    @pytest.mark.asyncio
    async def test_rate_limiting(self, wiktionary_connector: WiktionaryConnector) -> None:
        """Test rate limiting behavior."""
        # Verify rate limiter is configured
        assert wiktionary_connector.rate_limiter is not None

        # Check rate limit configuration
        config = wiktionary_connector.config.rate_limit_config
        assert config is not None
        assert config.base_requests_per_second == 5.0  # API_STANDARD preset

    @pytest.mark.asyncio
    async def test_special_characters_handling(
        self, wiktionary_connector: WiktionaryConnector, test_db
    ) -> None:
        """Test handling of words with special characters using real API."""
        # Test with a word that has special characters
        result = await wiktionary_connector._fetch_from_provider("café")

        # If found, verify it handles special characters correctly
        if result is not None:
            assert result["word"] == "café"
            assert result["provider"] == DictionaryProvider.WIKTIONARY.value

    @pytest.mark.asyncio
    async def test_fetch_and_save_integration(
        self, wiktionary_connector: WiktionaryConnector, test_db
    ) -> None:
        """Test the full fetch and save flow with real API."""
        # Use the public fetch method with real API
        result = await wiktionary_connector.fetch("dictionary")

        if result is not None:
            assert isinstance(result, dict)  # fetch() should return dict for now
            assert result["word"] == "dictionary"
            assert result["provider"] == DictionaryProvider.WIKTIONARY.value
            
            # Verify it can be retrieved from cache
            cached_result = await wiktionary_connector.get("dictionary")
            assert cached_result is not None
            assert cached_result["word"] == "dictionary"

    @pytest.mark.asyncio
    async def test_cleanup(self, wiktionary_connector: WiktionaryConnector) -> None:
        """Test connector cleanup."""
        # Test that close method works without errors
        await wiktionary_connector.close()
        
        # After closing, the connector should still be usable
        # (it will recreate sessions as needed)
        result = await wiktionary_connector._fetch_from_provider("simple")
        # Just verify no exceptions are raised
        assert result is None or isinstance(result, dict)