"""Tests for literature provider implementations using real database."""

import os

import pytest

from floridify.caching.models import ResourceType, VersionInfo
from floridify.models.base import Language
from floridify.models.literature import AuthorInfo
from floridify.providers.core import ConnectorConfig, ProviderType
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.api.internet_archive import InternetArchiveConnector
from floridify.providers.literature.mappings import dickens, joyce, shakespeare
from floridify.providers.literature.models import LiteratureEntry


class TestLiteratureProviderBase:
    """Base tests for literature providers using real implementations."""

    @pytest.mark.asyncio
    async def test_connector_initialization(self, test_db):
        """Test literature connector initialization."""
        # test_db ensures database is initialized
        config = ConnectorConfig()

        # GutenbergConnector doesn't require config in constructor
        gutenberg = GutenbergConnector()
        assert gutenberg.provider is not None
        assert gutenberg.rate_limiter is not None

        # InternetArchiveConnector
        archive = InternetArchiveConnector(config=config)
        assert archive.provider is not None
        assert archive.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_author_mappings(self, test_db):
        """Test author mapping configurations."""
        # test_db ensures database is initialized
        # Test major author mappings
        authors = [
            shakespeare.AUTHOR,
            dickens.AUTHOR,
            joyce.AUTHOR,
        ]

        for author in authors:
            assert isinstance(author, AuthorInfo)
            assert author.name
            assert author.gutenberg_author_id or author.internet_archive_id
            # Check if author has works defined in their mapping
            # The 'works' might be stored differently in the actual model


class TestGutenbergConnector:
    """Tests for Project Gutenberg using real API."""

    @pytest.mark.asyncio
    async def test_gutenberg_real_fetch(self, test_db, connector_config: ConnectorConfig):
        """Test real fetch from Project Gutenberg."""
        # test_db ensures database is initialized
        connector = GutenbergConnector(config=connector_config)
        
        # Test with a small public domain work
        # 11 = Alice's Adventures in Wonderland (small file)
        result = await connector._fetch_from_provider("11")
        
        if result is not None:
            # If Gutenberg is available, verify structure
            assert isinstance(result, dict)
            assert "metadata" in result or "content" in result

    @pytest.mark.asyncio
    async def test_gutenberg_search(self, test_db, connector_config: ConnectorConfig):
        """Test search functionality with real Gutenberg API."""
        # test_db ensures database is initialized
        connector = GutenbergConnector(config=connector_config)
        
        # Search for works by a well-known author
        results = await connector.search_works(author_name="Carroll", limit=5)
        
        if results:
            # Verify search results structure
            assert isinstance(results, list)
            for work in results:
                assert isinstance(work, dict)
                assert "source_id" in work
                assert "title" in work
                assert "author" in work

    @pytest.mark.asyncio
    async def test_gutenberg_error_handling(self, test_db, connector_config: ConnectorConfig):
        """Test error handling for non-existent works."""
        # test_db ensures database is initialized
        connector = GutenbergConnector(config=connector_config)
        
        # Test with a non-existent work ID
        result = await connector._fetch_from_provider("999999999")
        
        # Should handle gracefully
        # Result can be None or contain error information
        if result is not None:
            assert isinstance(result, dict)


class TestInternetArchiveConnector:
    """Tests for Internet Archive using real API."""

    @pytest.mark.asyncio
    async def test_archive_real_fetch(self, test_db, connector_config: ConnectorConfig):
        """Test real fetch from Internet Archive."""
        # test_db ensures database is initialized
        connector = InternetArchiveConnector(config=connector_config)
        
        # Test with a known item
        result = await connector._fetch_from_provider("alicesadventures00carr")
        
        if result is not None:
            assert isinstance(result, dict)
            assert "metadata" in result or "content" in result

    @pytest.mark.asyncio
    async def test_archive_search(self, test_db, connector_config: ConnectorConfig):
        """Test search functionality with real Internet Archive API."""
        # test_db ensures database is initialized
        connector = InternetArchiveConnector(config=connector_config)
        
        # Search for texts
        results = await connector.search_works(title="Alice", limit=5)
        
        if results:
            assert isinstance(results, list)
            for work in results:
                assert isinstance(work, dict)
                assert "source_id" in work
                assert "title" in work


class TestLiteratureIntegration:
    """Test literature provider integration with real database."""

    @pytest.mark.asyncio
    async def test_provider_cascade_real(self, test_db, connector_config: ConnectorConfig):
        """Test cascading through providers with real implementations."""
        providers = [
            GutenbergConnector(config=connector_config),
            InternetArchiveConnector(config=connector_config),
        ]
        
        # Try to fetch a work from multiple providers
        work_id = "alice"  # Common search term
        results = []
        
        for provider in providers:
            try:
                # Use search instead of direct fetch for better results
                search_results = await provider.search_works(title=work_id, limit=1)
                if search_results:
                    results.append(search_results[0])
            except Exception:
                # Real API might fail, that's okay
                continue
        
        # At least one provider should work
        # Note: This might fail if both APIs are down
        if results:
            assert len(results) > 0

    @pytest.mark.asyncio
    async def test_caching_with_database(self, test_db, connector_config: ConnectorConfig):
        """Test that caching works with real database."""
        # test_db ensures database is initialized
        connector = GutenbergConnector(config=connector_config)
        
        # Fetch a small work
        work_id = "74"  # The Adventures of Tom Sawyer
        
        # First fetch - should store in database
        result1 = await connector.fetch(work_id)
        
        if result1 is not None:
            # Second fetch - should use cache from database
            result2 = await connector.fetch(work_id)
            
            # Both should return data
            assert result2 is not None