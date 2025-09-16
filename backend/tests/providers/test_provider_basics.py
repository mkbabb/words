"""Basic tests for provider functionality."""

import pytest

from floridify.models.dictionary import DictionaryProvider
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.dictionary.api.merriam_webster import MerriamWebsterConnector
from floridify.providers.dictionary.api.oxford import OxfordConnector


class TestProviderInitialization:
    """Test provider initialization."""

    def test_free_dictionary_init(self):
        """Test FreeDictionary connector initialization."""
        config = ConnectorConfig()
        connector = FreeDictionaryConnector(config)

        assert connector.provider == DictionaryProvider.FREE_DICTIONARY
        assert connector.base_url == "https://api.dictionaryapi.dev/api/v2/entries/en"
        assert connector.config == config

    @pytest.mark.skip("Requires API key")
    def test_merriam_webster_init(self):
        """Test MerriamWebster connector initialization."""
        config = ConnectorConfig()
        connector = MerriamWebsterConnector(config)

        assert connector.provider == DictionaryProvider.MERRIAM_WEBSTER
        # MerriamWebster overrides config with different rate limits
        assert connector.config is not None

    @pytest.mark.skip("Requires API key")
    def test_oxford_init(self):
        """Test Oxford connector initialization."""
        config = ConnectorConfig()
        # Oxford requires app_id and api_key as first arguments
        connector = OxfordConnector(app_id="test_app", api_key="test_key", config=config)

        assert connector.provider == DictionaryProvider.OXFORD
        assert connector.config is not None
        assert connector.app_id == "test_app"
        assert connector.api_key == "test_key"


class TestProviderMethods:
    """Test provider method signatures."""

    @pytest.mark.asyncio
    @pytest.mark.skip("Requires external API")
    async def test_free_dictionary_fetch(self):
        """Test FreeDictionary fetch method."""
        config = ConnectorConfig()
        connector = FreeDictionaryConnector(config)

        # Test with a word that likely doesn't exist
        result = await connector._fetch_from_api("xyznonexistentwordxyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_provider_method_behavior(self, test_db):
        """Test that provider methods work correctly with MongoDB."""
        config = ConnectorConfig(force_fetch=False)
        connector = FreeDictionaryConnector(config)

        # Test fetch stores data in MongoDB
        result = await connector.fetch("test")
        if result:
            # Verify data was saved to MongoDB
            saved = await connector.get("test")
            assert saved is not None
            assert saved["word"] == "test"

            # Test that subsequent fetch uses cache
            cached_result = await connector.fetch("test")
            assert cached_result is not None
            # Should have same content
            assert cached_result["word"] == result["word"]

        # Test force fetch bypasses cache
        config_force = ConnectorConfig(force_fetch=True)
        connector_force = FreeDictionaryConnector(config_force)
        await connector_force.fetch("test")
        # Should make new API call (might fail if API is down, that's ok)


class TestProviderConfig:
    """Test provider configuration."""

    def test_connector_config_defaults(self):
        """Test ConnectorConfig default values."""
        config = ConnectorConfig()

        assert config.timeout == 30.0
        assert config.max_connections == 5
        assert config.max_retries == 3
        assert config.use_cache is True
        assert config.save_versioned is True

    def test_rate_limit_config(self):
        """Test rate limit configuration."""
        from floridify.providers.utils import RateLimitConfig

        rate_config = RateLimitConfig()

        assert rate_config.base_requests_per_second == 2.0
        assert rate_config.min_delay == 0.5
        assert rate_config.max_delay == 10.0
        assert rate_config.backoff_multiplier == 2.0
