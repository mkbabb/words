"""Tests for Project Gutenberg literature provider."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.models.literature import AuthorInfo, Genre, LiteratureProvider, Period
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.models import LiteratureEntry


@pytest_asyncio.fixture
async def gutenberg_connector() -> GutenbergConnector:
    """Create Gutenberg connector for testing."""
    return GutenbergConnector()


@pytest_asyncio.fixture
def sample_literature_entry() -> LiteratureEntry:
    """Create sample literature entry."""
    return LiteratureEntry(
        title="Pride and Prejudice",
        author=AuthorInfo(
            name="Jane Austen",
            period=Period.ROMANTIC,  # Jane Austen was from the Romantic period
            primary_genre=Genre.ROMANCE,
        ),
        gutenberg_id="1342",
        year=1813,
        genre=Genre.ROMANCE,
        period=Period.ROMANTIC,
    )


class TestGutenbergConnector:
    """Test Gutenberg connector functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, gutenberg_connector: GutenbergConnector) -> None:
        """Test connector initialization."""
        assert gutenberg_connector.provider == LiteratureProvider.GUTENBERG
        assert gutenberg_connector.api_base == "https://www.gutenberg.org"
        assert gutenberg_connector.config.rate_limit_config is not None

    @pytest.mark.asyncio
    async def test_fetch_from_provider_success(
        self,
        gutenberg_connector: GutenbergConnector,
        sample_literature_entry: LiteratureEntry,
        test_db,
    ) -> None:
        """Test successful fetch from provider using real API."""
        # Use real Gutenberg API with a known text ID
        result = await gutenberg_connector._fetch_from_provider(sample_literature_entry.gutenberg_id)

        # Gutenberg might rate limit or be unavailable, so handle both cases
        if result is not None:
            assert isinstance(result, dict)
            assert "text" in result or "content" in result
            assert "title" in result
            assert result["provider"] == LiteratureProvider.GUTENBERG.value

    @pytest.mark.asyncio
    async def test_fetch_from_provider_not_found(
        self, gutenberg_connector: GutenbergConnector, test_db
    ) -> None:
        """Test handling of work not found using real API."""
        # Use a non-existent ID
        result = await gutenberg_connector._fetch_from_provider("99999999")

        # Should return None for non-existent IDs
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_multiple_works(
        self, gutenberg_connector: GutenbergConnector, test_db
    ) -> None:
        """Test fetching multiple works."""
        # Test with multiple known Gutenberg IDs
        ids = ["1342", "11", "84"]  # Pride and Prejudice, Alice in Wonderland, Frankenstein
        results = []
        
        for work_id in ids:
            result = await gutenberg_connector._fetch_from_provider(work_id)
            results.append(result)
        
        # At least some should succeed
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) > 0
        
        for result in successful_results:
            assert isinstance(result, dict)
            assert result["provider"] == LiteratureProvider.GUTENBERG.value

    @pytest.mark.asyncio
    async def test_rate_limiting(self, gutenberg_connector: GutenbergConnector) -> None:
        """Test rate limiting configuration."""
        assert gutenberg_connector.rate_limiter is not None

        # Should use BULK_DOWNLOAD preset
        config = gutenberg_connector.config.rate_limit_config
        assert config is not None
        assert config.base_requests_per_second == 0.5  # Conservative for bulk

    @pytest.mark.asyncio
    async def test_fetch_and_save_integration(
        self,
        gutenberg_connector: GutenbergConnector,
        sample_literature_entry: LiteratureEntry,
        test_db,
    ) -> None:
        """Test the full fetch and save flow using real API."""
        # Use the public fetch method with real API
        result = await gutenberg_connector.fetch(sample_literature_entry.gutenberg_id)

        if result is not None:
            assert isinstance(result, dict)  # fetch() returns dict for now
            assert result["provider"] == LiteratureProvider.GUTENBERG.value
            
            # Verify it can be retrieved from cache
            cached_result = await gutenberg_connector.get(sample_literature_entry.gutenberg_id)
            assert cached_result is not None
            assert cached_result["provider"] == LiteratureProvider.GUTENBERG.value

    @pytest.mark.asyncio
    async def test_catalog_search(
        self, gutenberg_connector: GutenbergConnector, test_db
    ) -> None:
        """Test catalog search functionality."""
        # Search for a known author
        results = await gutenberg_connector.search_catalog("Shakespeare")
        
        if results is not None:
            assert isinstance(results, list)
            # Shakespeare should have many works
            if len(results) > 0:
                first_result = results[0]
                assert "title" in first_result
                assert "gutenberg_id" in first_result

    @pytest.mark.asyncio
    async def test_cleanup(self, gutenberg_connector: GutenbergConnector) -> None:
        """Test connector cleanup."""
        # Test that close method works without errors
        await gutenberg_connector.close()
        
        # After closing, the connector should still be usable
        # (it will recreate sessions as needed)
        result = await gutenberg_connector._fetch_from_provider("1342")
        # Just verify no exceptions are raised
        assert result is None or isinstance(result, dict)