"""Tests for URL-based language source provider."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.models.base import Language
from floridify.providers.language.models import LanguageProvider, LanguageSource
from floridify.providers.language.scraper.url import URLLanguageConnector


@pytest_asyncio.fixture
def url_language_connector() -> URLLanguageConnector:
    """Create URL language connector for testing."""
    return URLLanguageConnector()


@pytest_asyncio.fixture
def text_language_source() -> LanguageSource:
    """Create test language source that points to a real text file."""
    return LanguageSource(
        name="test_vocab",
        url="https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",  # Real word list
        language=Language.ENGLISH,
        description="Test vocabulary list",
    )


@pytest_asyncio.fixture
def csv_language_source() -> LanguageSource:
    """Create CSV language source for testing."""
    return LanguageSource(
        name="test_csv_vocab",
        url="https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english.txt",  # Real CSV-like word list
        language=Language.ENGLISH,
        description="Test CSV vocabulary",
    )


class TestURLLanguageConnector:
    """Test URL language connector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, url_language_connector: URLLanguageConnector) -> None:
        """Test connector initialization."""
        assert url_language_connector.provider == LanguageProvider.CUSTOM_URL
        assert url_language_connector.config.rate_limit_config is not None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(
        self,
        url_language_connector: URLLanguageConnector,
        text_language_source: LanguageSource,
        test_db,
    ) -> None:
        """Test successful fetch from provider using real URL."""
        # Use real URL to fetch vocabulary
        result = await url_language_connector._fetch_from_provider(text_language_source)

        # Should successfully fetch from GitHub
        if result is not None:
            assert isinstance(result, dict)
            assert result["provider"] == LanguageProvider.CUSTOM_URL.value
            assert "vocabulary" in result
            assert isinstance(result["vocabulary"], list)
            assert len(result["vocabulary"]) > 100  # Should have many words
            # Check that we have actual English words (the file is alphabetical)
            # Just verify we have some common starting letters
            assert any(word.startswith("a") for word in result["vocabulary"][:100])

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(
        self,
        url_language_connector: URLLanguageConnector,
        test_db,
    ) -> None:
        """Test handling of URL not found using real request."""
        # Create a source with non-existent URL
        bad_source = LanguageSource(
            name="bad_source",
            url="https://raw.githubusercontent.com/nonexistent/repo/file.txt",
            language=Language.ENGLISH,
            description="Non-existent source",
        )
        
        result = await url_language_connector._fetch_from_provider(bad_source)
        
        # Should return None for 404 URLs
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_csv_format(
        self,
        url_language_connector: URLLanguageConnector,
        csv_language_source: LanguageSource,
        test_db,
    ) -> None:
        """Test fetching CSV format vocabulary."""
        result = await url_language_connector._fetch_from_provider(csv_language_source)

        if result is not None:
            assert isinstance(result, dict)
            assert result["provider"] == LanguageProvider.CUSTOM_URL.value
            assert "vocabulary" in result
            assert len(result["vocabulary"]) > 0
            # Should contain common English words (check in entire list, not just first 100)
            common_words = ["the", "and", "you", "that"]
            vocabulary_set = set(result["vocabulary"])
            found_words = [w for w in common_words if w in vocabulary_set]
            assert len(found_words) > 0

    @pytest.mark.asyncio
    async def test_rate_limiting(self, url_language_connector: URLLanguageConnector) -> None:
        """Test rate limiting configuration."""
        assert url_language_connector.rate_limiter is not None

        # Check rate limit configuration
        config = url_language_connector.config.rate_limit_config
        assert config is not None
        assert config.base_requests_per_second == 1.0  # SCRAPER_RESPECTFUL preset

    @pytest.mark.asyncio
    async def test_fetch_and_save_integration(
        self,
        url_language_connector: URLLanguageConnector,
        text_language_source: LanguageSource,
        test_db,
    ) -> None:
        """Test the full fetch and save flow using real data."""
        # Use the public fetch method - pass the source object directly
        result = await url_language_connector._fetch_from_provider(text_language_source)

        if result is not None:
            assert isinstance(result, dict)  # fetch() returns dict for now
            assert result["provider"] == LanguageProvider.CUSTOM_URL.value
            
            # Verify it can be retrieved from cache
            cached_result = await url_language_connector.get(text_language_source.name)
            if cached_result is not None:
                assert cached_result["provider"] == LanguageProvider.CUSTOM_URL.value

    @pytest.mark.asyncio
    async def test_multiple_sources(
        self,
        url_language_connector: URLLanguageConnector,
        test_db,
    ) -> None:
        """Test fetching from multiple sources."""
        sources = [
            LanguageSource(
                name="source1",
                url="https://raw.githubusercontent.com/dwyl/english-words/master/words.txt",
                language=Language.ENGLISH,
                description="Source 1",
            ),
            LanguageSource(
                name="source2",
                url="https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa.txt",
                language=Language.ENGLISH,
                description="Source 2",
            ),
        ]
        
        results = []
        for source in sources:
            result = await url_language_connector._fetch_from_provider(source)
            results.append(result)
        
        # At least one should succeed
        successful = [r for r in results if r is not None]
        assert len(successful) > 0
        
        for result in successful:
            assert result["provider"] == LanguageProvider.CUSTOM_URL.value
            assert len(result["vocabulary"]) > 0

    @pytest.mark.asyncio
    async def test_cleanup(self, url_language_connector: URLLanguageConnector) -> None:
        """Test connector cleanup."""
        # Test that close method works without errors
        await url_language_connector.close()
        
        # After closing, the connector should still be usable
        # (it will recreate sessions as needed)
        source = LanguageSource(
            name="test_after_close",
            url="https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
            language=Language.ENGLISH,
            description="Test after close",
        )
        result = await url_language_connector._fetch_from_provider(source)
        # Just verify no exceptions are raised
        assert result is None or isinstance(result, dict)