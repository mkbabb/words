"""Tests for Free Dictionary API provider."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector


@pytest_asyncio.fixture
async def free_dictionary_connector() -> FreeDictionaryConnector:
    """Create Free Dictionary connector for testing."""
    return FreeDictionaryConnector()




class TestFreeDictionaryConnector:
    """Test Free Dictionary connector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, free_dictionary_connector: FreeDictionaryConnector) -> None:
        """Test connector initialization."""
        assert free_dictionary_connector.provider == DictionaryProvider.FREE_DICTIONARY
        assert (
            free_dictionary_connector.base_url == "https://api.dictionaryapi.dev/api/v2/entries/en"
        )
        assert free_dictionary_connector.config.rate_limit_config is not None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(
        self,
        free_dictionary_connector: FreeDictionaryConnector,
        test_db,
    ) -> None:
        """Test successful fetch from provider using real API."""
        # Test with a common word using real API
        result = await free_dictionary_connector._fetch_from_provider("test")

        assert result is not None
        assert isinstance(result, dict)
        assert result["word"] == "test"
        assert "entries" in result
        assert isinstance(result["entries"], list)
        assert len(result["entries"]) > 0
        assert result["provider"] == DictionaryProvider.FREE_DICTIONARY.value
        
        # Verify the entries have expected structure
        first_entry = result["entries"][0]
        assert "word" in first_entry
        assert "meanings" in first_entry

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(
        self, free_dictionary_connector: FreeDictionaryConnector, test_db
    ) -> None:
        """Test handling of word not found using real API."""
        # Test with a definitely non-existent word
        result = await free_dictionary_connector._fetch_from_provider("xyznonexistentword123456")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_common_words(
        self, free_dictionary_connector: FreeDictionaryConnector, test_db
    ) -> None:
        """Test fetching common words using real API."""
        words = ["hello", "world", "computer"]
        
        for word in words:
            result = await free_dictionary_connector._fetch_from_provider(word)
            assert result is not None
            assert result["word"] == word
            assert result["provider"] == DictionaryProvider.FREE_DICTIONARY.value
            assert "entries" in result
            assert len(result["entries"]) > 0

    @pytest.mark.asyncio
    async def test_fetch_with_special_characters(
        self, free_dictionary_connector: FreeDictionaryConnector, test_db
    ) -> None:
        """Test handling words with special characters using real API."""
        # Test word with hyphen
        result = await free_dictionary_connector._fetch_from_provider("well-being")
        
        if result is not None:
            assert result["word"] == "well-being"
            assert result["provider"] == DictionaryProvider.FREE_DICTIONARY.value

    @pytest.mark.asyncio
    async def test_rate_limiting(self, free_dictionary_connector: FreeDictionaryConnector) -> None:
        """Test rate limiting behavior."""
        # Verify rate limiter is configured
        assert free_dictionary_connector.rate_limiter is not None

        # Check rate limit configuration
        config = free_dictionary_connector.config.rate_limit_config
        assert config is not None
        assert config.base_requests_per_second == 10.0  # API_FAST preset

    @pytest.mark.asyncio
    async def test_fetch_definitions_structure(
        self, free_dictionary_connector: FreeDictionaryConnector, test_db
    ) -> None:
        """Test that fetched data has proper definition structure."""
        result = await free_dictionary_connector._fetch_from_provider("book")
        
        assert result is not None
        assert "entries" in result
        
        # Check the structure of entries
        for entry in result["entries"]:
            assert "word" in entry
            assert "meanings" in entry
            
            # Check meanings structure
            for meaning in entry["meanings"]:
                assert "partOfSpeech" in meaning
                assert "definitions" in meaning
                
                # Check definitions structure
                for definition in meaning["definitions"]:
                    assert "definition" in definition

    @pytest.mark.asyncio  
    async def test_fetch_and_save_integration(
        self,
        free_dictionary_connector: FreeDictionaryConnector,
        test_db,
    ) -> None:
        """Test the full fetch and save flow using real API."""
        # Use the public fetch method which handles caching/saving
        result = await free_dictionary_connector.fetch("language")

        assert result is not None
        assert isinstance(result, dict)  # fetch() returns dict for now
        assert result["word"] == "language"
        assert result["provider"] == DictionaryProvider.FREE_DICTIONARY.value
        
        # Verify it can be retrieved from cache
        cached_result = await free_dictionary_connector.get("language")
        assert cached_result is not None
        assert cached_result["word"] == "language"
        assert cached_result["provider"] == DictionaryProvider.FREE_DICTIONARY.value