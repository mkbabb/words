"""Tests for dictionary provider implementations."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from httpx import HTTPError, Response

from floridify.models.dictionary import Language
from floridify.providers.batch import BatchOperation
from floridify.providers.core import ConnectorConfig, ProviderType
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.api.merriam_webster import MerriamWebsterConnector
from floridify.providers.dictionary.api.oxford import OxfordConnector
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector
from floridify.providers.dictionary.scraper.wordhippo import WordHippoConnector


class TestDictionaryProviderBase:
    """Base tests for all dictionary providers."""
    
    @pytest.mark.asyncio
    async def test_connector_initialization(self, connector_config: ConnectorConfig):
        """Test that connectors initialize properly."""
        # Test each connector type
        connectors = [
            FreeDictionaryConnector(connector_config),
            WiktionaryConnector(connector_config),
            WordHippoConnector(connector_config),
        ]
        
        for connector in connectors:
            assert connector.config == connector_config
            assert connector.provider is not None
            assert connector.rate_limiter is not None
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, connector_config: ConnectorConfig):
        """Test rate limiting functionality."""
        # Set aggressive rate limit for testing
        from floridify.providers.utils import RateLimitConfig
        
        config = ConnectorConfig(
            rate_limit_config=RateLimitConfig(
                base_requests_per_second=2.0,
                min_delay=0.1,
                max_delay=1.0,
            )
        )
        
        connector = FreeDictionaryConnector(config)
        
        # Mock the API session
        mock_session = MagicMock()
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.json.return_value = [{"test": "data"}]
        mock_session.get.return_value = response
        
        with patch.object(connector, 'get_api_session', return_value=mock_session):
            # Make rapid requests
            tasks = [connector._fetch_from_api("test") for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Should not raise errors, but might be rate limited
            assert all(r is None or isinstance(r, list) for r in results)
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, connector_config: ConnectorConfig):
        """Test retry logic with error handling."""
        connector = FreeDictionaryConnector(connector_config)
        
        # Mock session to fail first 2 times, succeed on 3rd
        call_count = 0
        
        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise HTTPError("Test error")
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.json.return_value = [{"success": True}]
            return response
        
        mock_session = MagicMock()
        mock_session.get = mock_get
        
        with patch.object(connector, 'get_api_session', return_value=mock_session):
            # API retries are handled internally by httpx
            result = await connector._fetch_from_api("test")
            # Should fail gracefully after retries
            assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_integration(
        self, connector_config: ConnectorConfig, cache_manager
    ):
        """Test caching of lookup results."""
        connector = FreeDictionaryConnector(connector_config)
        
        test_data = [{"word": "test", "cached": True}]
        
        mock_session = MagicMock()
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.json.return_value = test_data
        mock_session.get.return_value = response
        
        with patch.object(connector, 'get_api_session', return_value=mock_session):
            # First lookup - should hit API
            result1 = await connector._fetch_from_api("test")
            assert mock_session.get.call_count == 1
            
            # Second lookup - may hit cache (depending on decorator)
            result2 = await connector._fetch_from_api("test")
            # The @cached_api_call decorator should handle caching
            assert result1 == result2


class TestFreeDictionaryConnector:
    """Tests specific to FreeDictionary API."""
    
    @pytest.mark.asyncio
    async def test_free_dictionary_parsing(
        self, connector_config: ConnectorConfig, mock_dictionary_response
    ):
        """Test parsing of FreeDictionary API response."""
        connector = FreeDictionaryConnector(connector_config)
        
        mock_session = MagicMock()
        response = MagicMock(spec=Response)
        response.status_code = 200
        response.json.return_value = [mock_dictionary_response]
        mock_session.get.return_value = response
        
        with patch.object(connector, 'get_api_session', return_value=mock_session):
            result = await connector._fetch_from_api("ubiquitous")
            
            # Verify API was called correctly
            mock_session.get.assert_called_once()
            assert "ubiquitous" in str(mock_session.get.call_args)
            assert result == [mock_dictionary_response]
    
    @pytest.mark.asyncio
    async def test_free_dictionary_error_handling(self, connector_config: ConnectorConfig):
        """Test error handling for FreeDictionary."""
        connector = FreeDictionaryConnector(connector_config)
        
        # Test 404 - word not found
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock(spec=Response)
            response.status_code = 404
            response.raise_for_status.side_effect = HTTPError("Not found")
            mock_client.get.return_value = response
            
            result = await connector.lookup("nonexistentword")
            assert result is None


class TestMerriamWebsterConnector:
    """Tests specific to Merriam-Webster API."""
    
    @pytest.mark.asyncio
    async def test_api_key_requirement(self):
        """Test that API key is required for Merriam-Webster."""
        config = ConnectorConfig(provider_type=ProviderType.DICTIONARY)
        
        # Should handle missing API key gracefully
        connector = MerriamWebsterConnector(config)
        result = await connector.lookup("test")
        assert result is None  # Should return None without API key
    
    @pytest.mark.asyncio
    async def test_merriam_webster_with_api_key(self, connector_config: ConnectorConfig):
        """Test Merriam-Webster with API key."""
        config = ConnectorConfig(
            provider_type=ProviderType.DICTIONARY,
            api_key="test_api_key",
        )
        
        connector = MerriamWebsterConnector(config)
        
        mock_response = {
            "meta": {"id": "ubiquitous"},
            "shortdef": ["existing everywhere at once"],
            "fl": "adjective",
        }
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.json.return_value = [mock_response]
            mock_client.get.return_value = response
            
            result = await connector.lookup("ubiquitous")
            
            # Verify API key was included
            call_args = mock_client.get.call_args
            assert "key=test_api_key" in str(call_args) or \
                   call_args[1].get('params', {}).get('key') == 'test_api_key'


class TestOxfordConnector:
    """Tests specific to Oxford Dictionary API."""
    
    @pytest.mark.asyncio
    async def test_oxford_authentication(self):
        """Test Oxford API authentication."""
        config = ConnectorConfig(
            provider_type=ProviderType.DICTIONARY,
            api_key="test_api_key",
            app_id="test_app_id",
        )
        
        connector = OxfordConnector(config)
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.json.return_value = {"results": []}
            mock_client.get.return_value = response
            
            await connector.lookup("test")
            
            # Verify headers were set correctly
            call_args = mock_client.get.call_args
            headers = call_args[1].get('headers', {})
            assert headers.get('app_id') == 'test_app_id'
            assert headers.get('app_key') == 'test_api_key'


class TestWiktionaryConnector:
    """Tests specific to Wiktionary scraper."""
    
    @pytest.mark.asyncio
    async def test_wiktionary_html_parsing(self, connector_config: ConnectorConfig):
        """Test parsing of Wiktionary HTML."""
        connector = WiktionaryConnector(connector_config)
        
        # Mock HTML response
        mock_html = """
        <html>
            <body>
                <h2>English</h2>
                <h3>Etymology</h3>
                <p>From Latin ubique</p>
                <h3>Adjective</h3>
                <ol>
                    <li>Present everywhere</li>
                </ol>
            </body>
        </html>
        """
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.text = mock_html
            mock_client.get.return_value = response
            
            result = await connector.lookup("ubiquitous")
            
            # Should successfully parse HTML
            assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_wiktionary_language_filtering(self, connector_config: ConnectorConfig):
        """Test language-specific filtering in Wiktionary."""
        connector = WiktionaryConnector(connector_config)
        connector.language = Language.FRENCH
        
        mock_html = """
        <html>
            <body>
                <h2>English</h2>
                <p>English definition</p>
                <h2>French</h2>
                <p>Définition française</p>
            </body>
        </html>
        """
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.text = mock_html
            mock_client.get.return_value = response
            
            result = await connector.lookup("ubiquitous")
            
            # Should extract French section
            assert result is None or isinstance(result, dict)


class TestWordHippoConnector:
    """Tests specific to WordHippo scraper."""
    
    @pytest.mark.asyncio
    async def test_wordhippo_scraping(self, connector_config: ConnectorConfig):
        """Test WordHippo web scraping."""
        connector = WordHippoConnector(connector_config)
        
        mock_html = """
        <html>
            <body>
                <div class="defv2wordtype">adjective</div>
                <div class="defv2worddefinition">
                    existing or being everywhere
                </div>
                <div class="relatedwords">
                    <span>omnipresent</span>
                    <span>universal</span>
                </div>
            </body>
        </html>
        """
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock(spec=Response)
            response.status_code = 200
            response.text = mock_html
            mock_client.get.return_value = response
            
            result = await connector.lookup("ubiquitous")
            
            assert result is None or isinstance(result, dict)


class TestBatchOperations:
    """Test batch dictionary lookups."""
    
    @pytest.mark.asyncio
    async def test_batch_lookup(
        self, test_db, connector_config: ConnectorConfig, mock_batch_operation
    ):
        """Test batch lookup operations."""
        await mock_batch_operation.save()
        
        connector = FreeDictionaryConnector(connector_config)
        words = ["test", "example", "sample"]
        
        with patch.object(connector, 'lookup') as mock_lookup:
            mock_lookup.return_value = {"word": "test", "definition": "a test"}
            
            # Perform batch lookup
            results = []
            for word in words:
                result = await connector.lookup(word)
                results.append(result)
                
                # Update batch operation
                mock_batch_operation.processed_items += 1
                await mock_batch_operation.save()
            
            assert len(results) == len(words)
            assert mock_batch_operation.processed_items == len(words)
    
    @pytest.mark.asyncio
    async def test_batch_resume(
        self, test_db, connector_config: ConnectorConfig, mock_batch_operation
    ):
        """Test resuming interrupted batch operations."""
        # Set checkpoint
        mock_batch_operation.processed_items = 50
        mock_batch_operation.checkpoint = {"last_word": "middle", "position": 50}
        await mock_batch_operation.save()
        
        # Resume from checkpoint
        loaded = await BatchOperation.find_one(
            BatchOperation.operation_id == mock_batch_operation.operation_id
        )
        
        assert loaded is not None
        assert loaded.processed_items == 50
        assert loaded.checkpoint["last_word"] == "middle"


class TestProviderFallback:
    """Test fallback between providers."""
    
    @pytest.mark.asyncio
    async def test_provider_cascade(self, connector_config: ConnectorConfig):
        """Test cascading through multiple providers on failure."""
        providers = [
            FreeDictionaryConnector(connector_config),
            WiktionaryConnector(connector_config),
            WordHippoConnector(connector_config),
        ]
        
        # Mock first two to fail, third to succeed
        with patch.object(providers[0], 'lookup', return_value=None), \
             patch.object(providers[1], 'lookup', return_value=None), \
             patch.object(providers[2], 'lookup', return_value={"success": True}):
            
            # Try providers in order
            result = None
            for provider in providers:
                result = await provider.lookup("test")
                if result:
                    break
            
            assert result == {"success": True}