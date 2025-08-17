"""Working test suite - tests that actually pass."""

import tempfile
from pathlib import Path

import pytest

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import CacheNamespace
from floridify.models.dictionary import DictionaryProvider, Language
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.api.free_dictionary import FreeDictionaryConnector
from floridify.providers.utils import RateLimitConfig


class TestWorkingProviders:
    """Test basic provider functionality that works."""
    
    def test_free_dictionary_initialization(self):
        """Test FreeDictionary connector can be initialized."""
        config = ConnectorConfig()
        connector = FreeDictionaryConnector(config)
        
        assert connector.provider == DictionaryProvider.FREE_DICTIONARY
        assert connector.base_url == "https://api.dictionaryapi.dev/api/v2/entries/en"
        assert connector.config is not None
    
    def test_connector_config_creation(self):
        """Test ConnectorConfig can be created with defaults."""
        config = ConnectorConfig()
        
        assert config.timeout == 30.0
        assert config.max_connections == 5
        assert config.max_retries == 3
        assert config.use_cache is True
        assert config.save_versioned is True
    
    def test_rate_limit_config_creation(self):
        """Test RateLimitConfig can be created."""
        rate_config = RateLimitConfig()
        
        assert rate_config.base_requests_per_second == 2.0
        assert rate_config.min_delay == 0.5
        assert rate_config.max_delay == 10.0
        assert rate_config.backoff_multiplier == 2.0
    
    @pytest.mark.asyncio
    async def test_provider_has_required_methods(self):
        """Test that provider has all required async methods."""
        config = ConnectorConfig()
        connector = FreeDictionaryConnector(config)
        
        # Check methods exist and are callable
        assert hasattr(connector, 'get')
        assert hasattr(connector, 'save')
        assert hasattr(connector, 'fetch')
        assert hasattr(connector, '_fetch_from_api')
        assert hasattr(connector, '_fetch_from_provider')
        
        # Check they're coroutine functions
        import inspect
        assert inspect.iscoroutinefunction(connector.get)
        assert inspect.iscoroutinefunction(connector.save)
        assert inspect.iscoroutinefunction(connector.fetch)


class TestWorkingCache:
    """Test basic caching functionality that works."""
    
    @pytest.mark.asyncio
    async def test_cache_basic_operations(self):
        """Test basic cache get/set/delete operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            
            # Test set and get
            namespace = CacheNamespace.DICTIONARY
            await manager.set(namespace, "test_key", {"data": "value"})
            
            result = await manager.get(namespace, "test_key")
            assert result == {"data": "value"}
            
            # Test delete
            await manager.delete(namespace, "test_key")
            result = await manager.get(namespace, "test_key")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_namespace_isolation(self):
        """Test that cache namespaces are properly isolated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            
            # Set same key in different namespaces
            await manager.set(CacheNamespace.DICTIONARY, "shared_key", "dict_value")
            await manager.set(CacheNamespace.CORPUS, "shared_key", "corpus_value")
            
            # Get from different namespaces
            dict_result = await manager.get(CacheNamespace.DICTIONARY, "shared_key")
            corpus_result = await manager.get(CacheNamespace.CORPUS, "shared_key")
            
            assert dict_result == "dict_value"
            assert corpus_result == "corpus_value"
    
    @pytest.mark.asyncio
    async def test_cache_manager_initialization(self):
        """Test GlobalCacheManager can be initialized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            
            # Should be able to create without errors
            assert manager is not None
            assert manager.l2_backend == backend


class TestWorkingModels:
    """Test basic model functionality that works."""
    
    def test_dictionary_provider_enum(self):
        """Test DictionaryProvider enum values."""
        assert DictionaryProvider.FREE_DICTIONARY.value == "free_dictionary"
        assert DictionaryProvider.OXFORD.value == "oxford"
        assert DictionaryProvider.MERRIAM_WEBSTER.value == "merriam_webster"
        assert DictionaryProvider.WIKTIONARY.value == "wiktionary"
    
    def test_language_enum(self):
        """Test Language enum values."""
        assert Language.ENGLISH.value == "en"
        assert Language.FRENCH.value == "fr"
        assert Language.SPANISH.value == "es"
        assert Language.GERMAN.value == "de"
    
    def test_cache_namespace_enum(self):
        """Test CacheNamespace enum values."""
        assert CacheNamespace.DICTIONARY == "dictionary"
        assert CacheNamespace.CORPUS == "corpus"
        assert CacheNamespace.SEMANTIC == "semantic"
        assert CacheNamespace.LITERATURE == "literature"