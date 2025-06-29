"""Tests for Beanie-based MongoDB storage layer."""

import pytest
from datetime import datetime

from src.floridify.models import (
    Word, 
    DictionaryEntry, 
    ProviderData, 
    Definition, 
    Pronunciation, 
    WordType,
    APIResponseCache
)
from src.floridify.storage import MongoDBStorage


class TestMongoDBStorage:
    """Tests for MongoDBStorage with Beanie ODM."""
    
    @pytest.fixture
    def storage(self) -> MongoDBStorage:
        """Create a MongoDBStorage instance for testing."""
        return MongoDBStorage(
            connection_string="mongodb://localhost:27017",
            database_name="test_floridify"
        )
    
    @pytest.fixture
    async def connected_storage(self, storage: MongoDBStorage) -> MongoDBStorage:
        """Create and connect MongoDBStorage for tests requiring DB connection."""
        await storage.connect()
        yield storage
        await storage.disconnect()
    
    @pytest.fixture
    def sample_entry(self) -> DictionaryEntry:
        """Create a sample dictionary entry for testing."""
        word = Word(text="test_word")
        pronunciation = Pronunciation(phonetic="test-word")
        definition = Definition(
            word_type=WordType.NOUN,
            definition="A sample definition for testing"
        )
        provider_data = ProviderData(
            provider_name="test_provider",
            definitions=[definition]
        )
        
        entry = DictionaryEntry(word=word, pronunciation=pronunciation)
        entry.add_provider_data(provider_data)
        return entry
    
    def test_storage_initialization(self, storage: MongoDBStorage) -> None:
        """Test storage initialization."""
        assert storage.connection_string == "mongodb://localhost:27017"
        assert storage.database_name == "test_floridify"
        assert storage.client is None
        assert storage._initialized is False
    
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, storage: MongoDBStorage) -> None:
        """Test connecting and disconnecting from MongoDB with Beanie."""
        await storage.connect()
        assert storage.client is not None
        assert storage._initialized is True
        
        await storage.disconnect()
        assert storage.client is None
        assert storage._initialized is False
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_entry(
        self, 
        connected_storage: MongoDBStorage, 
        sample_entry: DictionaryEntry
    ) -> None:
        """Test saving and retrieving a dictionary entry."""
        # Test save
        success = await connected_storage.save_entry(sample_entry)
        assert success is True
        
        # Test retrieve
        retrieved = await connected_storage.get_entry("test_word")
        assert retrieved is not None
        assert retrieved.word.text == "test_word"
        assert retrieved.pronunciation.phonetic == "test-word"
        assert "test_provider" in retrieved.providers
        assert len(retrieved.providers["test_provider"].definitions) == 1
    
    @pytest.mark.asyncio
    async def test_entry_exists(
        self, 
        connected_storage: MongoDBStorage,
        sample_entry: DictionaryEntry
    ) -> None:
        """Test checking if an entry exists."""
        # Initially should not exist
        exists = await connected_storage.entry_exists("test_word")
        assert exists is False
        
        # Save entry
        await connected_storage.save_entry(sample_entry)
        
        # Now should exist
        exists = await connected_storage.entry_exists("test_word")
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_update_existing_entry(
        self,
        connected_storage: MongoDBStorage,
        sample_entry: DictionaryEntry
    ) -> None:
        """Test updating an existing entry."""
        # Save initial entry
        await connected_storage.save_entry(sample_entry)
        
        # Create updated entry with additional provider
        new_definition = Definition(
            word_type=WordType.VERB,
            definition="A verb definition for testing"
        )
        new_provider_data = ProviderData(
            provider_name="another_provider",
            definitions=[new_definition]
        )
        
        updated_entry = DictionaryEntry(
            word=Word(text="test_word"),
            pronunciation=Pronunciation(phonetic="updated-test")
        )
        updated_entry.add_provider_data(new_provider_data)
        
        # Save updated entry
        success = await connected_storage.save_entry(updated_entry)
        assert success is True
        
        # Retrieve and verify update
        retrieved = await connected_storage.get_entry("test_word")
        assert retrieved is not None
        assert retrieved.pronunciation.phonetic == "updated-test"
        assert "another_provider" in retrieved.providers
    
    @pytest.mark.asyncio
    async def test_cache_operations(self, connected_storage: MongoDBStorage) -> None:
        """Test API response caching operations."""
        test_data = {"key": "value", "test": True}
        
        # Test caching
        success = await connected_storage.cache_api_response(
            "test_word", "test_provider", test_data
        )
        assert success is True
        
        # Test retrieval
        cached_data = await connected_storage.get_cached_response(
            "test_word", "test_provider"
        )
        assert cached_data == test_data
        
        # Test cache miss
        missing_data = await connected_storage.get_cached_response(
            "nonexistent", "provider"
        )
        assert missing_data is None
    
    @pytest.mark.asyncio
    async def test_cache_age_filtering(self, connected_storage: MongoDBStorage) -> None:
        """Test cache age filtering."""
        test_data = {"key": "value"}
        
        # Cache some data
        await connected_storage.cache_api_response(
            "test_word", "test_provider", test_data
        )
        
        # Should retrieve with default max age
        cached_data = await connected_storage.get_cached_response(
            "test_word", "test_provider", max_age_hours=24
        )
        assert cached_data == test_data
        
        # Should not retrieve with very small max age
        cached_data = await connected_storage.get_cached_response(
            "test_word", "test_provider", max_age_hours=0
        )
        assert cached_data is None
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, connected_storage: MongoDBStorage) -> None:
        """Test cleaning up old cache entries."""
        # This is a basic test - in practice would need to manipulate timestamps
        # to properly test TTL functionality
        deleted_count = await connected_storage.cleanup_old_cache(max_age_hours=0)
        assert isinstance(deleted_count, int)
        assert deleted_count >= 0
    
    @pytest.mark.asyncio 
    async def test_operations_without_connection(self, storage: MongoDBStorage) -> None:
        """Test that operations fail gracefully without connection."""
        word = Word(text="test")
        pronunciation = Pronunciation(phonetic="test")
        entry = DictionaryEntry(word=word, pronunciation=pronunciation)
        
        # All operations should return False/None when not connected
        assert await storage.save_entry(entry) is False
        assert await storage.get_entry("test") is None
        assert await storage.entry_exists("test") is False
        assert await storage.cache_api_response("test", "provider", {}) is False
        assert await storage.get_cached_response("test", "provider") is None
        assert await storage.cleanup_old_cache() == 0


@pytest.mark.asyncio
async def test_beanie_document_operations() -> None:
    """Test direct Beanie document operations."""
    # These tests ensure our Pydantic models work correctly with Beanie
    word = Word(text="beanie_test")
    pronunciation = Pronunciation(phonetic="bee-nee")
    
    entry = DictionaryEntry(word=word, pronunciation=pronunciation)
    
    # Test model validation
    assert entry.word.text == "beanie_test"
    assert entry.pronunciation.phonetic == "bee-nee"
    assert entry.providers == {}
    assert isinstance(entry.last_updated, datetime)
    
    # Test adding provider data
    definition = Definition(
        word_type=WordType.NOUN,
        definition="A testing framework"
    )
    provider_data = ProviderData(
        provider_name="test",
        definitions=[definition]
    )
    
    entry.add_provider_data(provider_data)
    assert "test" in entry.providers
    assert len(entry.providers["test"].definitions) == 1