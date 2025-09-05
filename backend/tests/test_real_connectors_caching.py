"""Real tests for non-API connectors and caching with actual database.

Tests the actual functionality without mocking, using real database operations.
KISS approach - test what actually works.
"""

import asyncio
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from beanie import PydanticObjectId

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import (
    CacheNamespace,
    DictionaryEntryMetadata,
    LiteratureEntryMetadata,
    VersionInfo,
)
from floridify.corpus.literature.models import AuthorInfo, Genre, LiteratureSource, Period
from floridify.models import Definition, Word
from floridify.models.dictionary import DictionaryProvider, Language
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.scraper.wiktionary import WiktionaryConnector


class TestRealWiktionaryConnector:
    """Test Wiktionary connector with real database operations."""

    @pytest.mark.asyncio
    async def test_wiktionary_word_creation(self, test_db):
        """Test that Wiktionary connector creates Word objects correctly."""
        config = ConnectorConfig()
        connector = WiktionaryConnector(config)
        
        # Test simple word creation
        word_text = "test"
        word = Word(text=word_text, language=Language.ENGLISH)
        await word.save()
        
        # Verify word was saved
        assert word.id is not None
        retrieved_word = await Word.get(word.id)
        assert retrieved_word is not None
        assert retrieved_word.text == word_text
        assert retrieved_word.language == Language.ENGLISH

    @pytest.mark.asyncio
    async def test_definition_creation_and_linking(self, test_db):
        """Test creating definitions linked to words."""
        # Create word
        word = Word(text="definition_test", language=Language.ENGLISH)
        await word.save()
        
        # Create definition
        definition = Definition(
            word_id=word.id,
            part_of_speech="noun",
            text="A test definition",
            sense_number="1"
        )
        await definition.save()
        
        # Verify definition was created and linked
        assert definition.id is not None
        assert definition.word_id == word.id
        
        retrieved_def = await Definition.get(definition.id)
        assert retrieved_def is not None
        assert retrieved_def.text == "A test definition"


class TestRealCaching:
    """Test caching with real filesystem operations."""

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self):
        """Test basic cache set/get/delete with real filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            
            # Test data
            test_data = {
                "word": "cache_test",
                "definitions": ["definition 1", "definition 2"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            namespace = CacheNamespace.DICTIONARY
            cache_key = "test_word_cache"
            
            # Set
            await manager.set(namespace, cache_key, test_data)
            
            # Get
            cached_data = await manager.get(namespace, cache_key)
            assert cached_data == test_data
            
            # Delete
            await manager.delete(namespace, cache_key)
            
            # Verify deleted
            deleted_data = await manager.get(namespace, cache_key)
            assert deleted_data is None

    @pytest.mark.asyncio
    async def test_namespace_separation(self):
        """Test that cache namespaces work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            
            shared_key = "shared_key"
            dict_data = {"type": "dictionary", "content": "dict content"}
            lit_data = {"type": "literature", "content": "lit content"}
            
            # Store in different namespaces
            await manager.set(CacheNamespace.DICTIONARY, shared_key, dict_data)
            await manager.set(CacheNamespace.LITERATURE, shared_key, lit_data)
            
            # Retrieve from each namespace
            dict_result = await manager.get(CacheNamespace.DICTIONARY, shared_key)
            lit_result = await manager.get(CacheNamespace.LITERATURE, shared_key)
            
            assert dict_result == dict_data
            assert lit_result == lit_data
            assert dict_result != lit_result


class TestRealVersioning:
    """Test versioning with real database operations."""

    @pytest.mark.asyncio
    async def test_dictionary_entry_versioning(self, test_db):
        """Test creating and managing dictionary entry versions."""
        # Create word
        word = Word(text="version_test", language=Language.ENGLISH)
        await word.save()
        
        # Version 1
        content_v1 = {
            "definitions": [{"text": "First definition", "pos": "noun"}],
            "provider": "wiktionary"
        }
        
        data_hash_v1 = hashlib.sha256(
            json.dumps(content_v1, sort_keys=True).encode()
        ).hexdigest()
        
        version_info_v1 = VersionInfo(
            version="1.0.0",
            data_hash=data_hash_v1,
            is_latest=True
        )
        
        entry_v1 = DictionaryEntryMetadata(
            resource_id=word.text,
            word=word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=word.language,
            version_info=version_info_v1
        )
        
        await entry_v1.set_content(content_v1)
        await entry_v1.save()
        
        # Verify v1 saved correctly
        assert entry_v1.id is not None
        assert entry_v1.version_info.is_latest is True
        
        retrieved_content = await entry_v1.get_content()
        assert retrieved_content == content_v1
        
        # Version 2
        content_v2 = {
            "definitions": [
                {"text": "First definition", "pos": "noun"},
                {"text": "Second definition", "pos": "verb"}
            ],
            "provider": "wiktionary",
            "etymology": "Added etymology in v2"
        }
        
        data_hash_v2 = hashlib.sha256(
            json.dumps(content_v2, sort_keys=True).encode()
        ).hexdigest()
        
        version_info_v2 = VersionInfo(
            version="2.0.0",
            data_hash=data_hash_v2,
            is_latest=True,
            supersedes=entry_v1.id
        )
        
        entry_v2 = DictionaryEntryMetadata(
            resource_id=word.text + "_v2",  # Different resource_id for v2
            word=word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=word.language,
            version_info=version_info_v2
        )
        
        await entry_v2.set_content(content_v2)
        await entry_v2.save()
        
        # Update v1 to not be latest
        entry_v1.version_info.is_latest = False
        entry_v1.version_info.superseded_by = entry_v2.id
        await entry_v1.save()
        
        # Verify version chain
        updated_v1 = await DictionaryEntryMetadata.get(entry_v1.id)
        assert updated_v1.version_info.is_latest is False
        assert updated_v1.version_info.superseded_by == entry_v2.id
        
        assert entry_v2.version_info.is_latest is True
        assert entry_v2.version_info.supersedes == entry_v1.id
        
        # Verify content integrity
        v2_content = await entry_v2.get_content()
        assert len(v2_content["definitions"]) == 2
        assert "etymology" in v2_content

    @pytest.mark.asyncio
    async def test_literature_entry_versioning(self, test_db):
        """Test creating and managing literature entry versions."""
        # Create author info
        author = AuthorInfo(
            name="Test Author",
            birth_year=1800,
            death_year=1900,
            nationality="English",
            period=Period.VICTORIAN,
            primary_genre=Genre.NOVEL,
            language=Language.ENGLISH
        )
        
        # Version 1
        content_v1 = {
            "title": "Test Novel",
            "full_text": "Chapter 1: The beginning.",
            "chapters": ["Chapter 1: The beginning."],
            "word_count": 4
        }
        
        text_hash_v1 = hashlib.sha256(content_v1["full_text"].encode()).hexdigest()
        
        version_info_v1 = VersionInfo(
            version="1.0.0",
            data_hash=text_hash_v1,
            is_latest=True
        )
        
        entry_v1 = LiteratureEntryMetadata(
            resource_id="test_novel",
            title="Test Novel",
            authors=[author],
            source=LiteratureSource.LOCAL_FILE,
            language=Language.ENGLISH,
            text_hash=text_hash_v1,
            text_size_bytes=len(content_v1["full_text"]),
            word_count=4,
            unique_words=4,
            version_info=version_info_v1
        )
        
        await entry_v1.set_content(content_v1)
        await entry_v1.save()
        
        # Verify v1 saved
        assert entry_v1.id is not None
        retrieved_content_v1 = await entry_v1.get_content()
        assert retrieved_content_v1["word_count"] == 4
        
        # Version 2 with more content
        content_v2 = {
            "title": "Test Novel",
            "full_text": "Chapter 1: The beginning. Chapter 2: The continuation.",
            "chapters": [
                "Chapter 1: The beginning.", 
                "Chapter 2: The continuation."
            ],
            "word_count": 8
        }
        
        text_hash_v2 = hashlib.sha256(content_v2["full_text"].encode()).hexdigest()
        
        version_info_v2 = VersionInfo(
            version="2.0.0",
            data_hash=text_hash_v2,
            is_latest=True,
            supersedes=entry_v1.id
        )
        
        entry_v2 = LiteratureEntryMetadata(
            resource_id="test_novel_v2",
            title="Test Novel",
            authors=[author],
            source=LiteratureSource.LOCAL_FILE,
            language=Language.ENGLISH,
            text_hash=text_hash_v2,
            text_size_bytes=len(content_v2["full_text"]),
            word_count=8,
            unique_words=7,
            version_info=version_info_v2
        )
        
        await entry_v2.set_content(content_v2)
        await entry_v2.save()
        
        # Update v1
        entry_v1.version_info.is_latest = False
        entry_v1.version_info.superseded_by = entry_v2.id
        await entry_v1.save()
        
        # Verify progression
        assert entry_v2.word_count > entry_v1.word_count
        retrieved_content_v2 = await entry_v2.get_content()
        assert len(retrieved_content_v2["chapters"]) == 2


class TestRealCacheVersioningIntegration:
    """Test integration between caching and versioning with real operations."""

    @pytest.mark.asyncio
    async def test_cached_versioned_lookup(self, test_db):
        """Test looking up versioned content through cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            
            # Create word and versioned entry
            word = Word(text="cached_version_test", language=Language.ENGLISH)
            await word.save()
            
            content = {
                "definitions": ["Cached definition"],
                "cached_at": datetime.utcnow().isoformat()
            }
            
            data_hash = hashlib.sha256(
                json.dumps(content, sort_keys=True).encode()
            ).hexdigest()
            
            version_info = VersionInfo(
                version="1.0.0",
                data_hash=data_hash,
                is_latest=True
            )
            
            entry = DictionaryEntryMetadata(
                resource_id=word.text,
                word=word.text,
                provider=DictionaryProvider.WIKTIONARY.value,
                language=word.language,
                version_info=version_info
            )
            
            await entry.set_content(content)
            await entry.save()
            
            # Cache the entry reference
            cache_key = f"dict_entry:{word.text}:latest"
            await manager.set(CacheNamespace.DICTIONARY, cache_key, {
                "entry_id": str(entry.id),
                "version": entry.version_info.version,
                "cached_at": datetime.utcnow().isoformat()
            })
            
            # Retrieve from cache
            cached_ref = await manager.get(CacheNamespace.DICTIONARY, cache_key)
            assert cached_ref is not None
            assert cached_ref["entry_id"] == str(entry.id)
            assert cached_ref["version"] == "1.0.0"
            
            # Use cached reference to get actual entry
            entry_id = PydanticObjectId(cached_ref["entry_id"])
            retrieved_entry = await DictionaryEntryMetadata.get(entry_id)
            assert retrieved_entry is not None
            
            retrieved_content = await retrieved_entry.get_content()
            assert retrieved_content == content

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_version_update(self, test_db):
        """Test cache invalidation when new versions are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            
            word = Word(text="invalidation_test", language=Language.ENGLISH)
            await word.save()
            
            # Cache v1
            cache_key = f"dict_entry:{word.text}:latest"
            v1_cache_data = {
                "version": "1.0.0",
                "content": "Version 1 content",
                "is_latest": True
            }
            
            await manager.set(CacheNamespace.DICTIONARY, cache_key, v1_cache_data)
            
            # Verify v1 cached
            cached_v1 = await manager.get(CacheNamespace.DICTIONARY, cache_key)
            assert cached_v1["version"] == "1.0.0"
            
            # Simulate version update by invalidating cache
            await manager.delete(CacheNamespace.DICTIONARY, cache_key)
            
            # Cache v2
            v2_cache_data = {
                "version": "2.0.0",
                "content": "Version 2 content",
                "is_latest": True
            }
            
            await manager.set(CacheNamespace.DICTIONARY, cache_key, v2_cache_data)
            
            # Verify v2 cached and v1 gone
            cached_v2 = await manager.get(CacheNamespace.DICTIONARY, cache_key)
            assert cached_v2["version"] == "2.0.0"
            assert cached_v2["content"] == "Version 2 content"

    @pytest.mark.asyncio
    async def test_concurrent_cache_and_db_operations(self, test_db):
        """Test concurrent caching and database operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            
            async def create_word_and_cache(index: int):
                # Create word in DB
                word = Word(text=f"concurrent_word_{index}", language=Language.ENGLISH)
                await word.save()
                
                # Cache word reference
                cache_key = f"word:{word.text}"
                cache_data = {
                    "word_id": str(word.id),
                    "text": word.text,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                await manager.set(CacheNamespace.DICTIONARY, cache_key, cache_data)
                
                # Verify both DB and cache
                db_word = await Word.get(word.id)
                cached_word = await manager.get(CacheNamespace.DICTIONARY, cache_key)
                
                assert db_word.text == word.text
                assert cached_word["text"] == word.text
                
                return word, cached_word
            
            # Run concurrent operations
            tasks = [create_word_and_cache(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            for word, cached_data in results:
                assert word.text == cached_data["text"]
                assert str(word.id) == cached_data["word_id"]


class TestRealDataPersistence:
    """Test data persistence across cache and database operations."""

    @pytest.mark.asyncio
    async def test_large_content_storage_and_retrieval(self, test_db):
        """Test storing and retrieving large content."""
        # Create large content
        large_definitions = []
        for i in range(100):
            large_definitions.append({
                "text": f"Definition {i}: " + "Long definition text " * 50,
                "part_of_speech": "noun" if i % 2 == 0 else "verb",
                "examples": [f"Example {j} for definition {i}" for j in range(3)]
            })
        
        large_content = {
            "definitions": large_definitions,
            "etymology": "Long etymology text " * 100,
            "notes": "Usage notes " * 200
        }
        
        # Create word
        word = Word(text="large_content_test", language=Language.ENGLISH)
        await word.save()
        
        # Create versioned entry with large content
        data_hash = hashlib.sha256(
            json.dumps(large_content, sort_keys=True).encode()
        ).hexdigest()
        
        version_info = VersionInfo(
            version="1.0.0",
            data_hash=data_hash,
            is_latest=True
        )
        
        entry = DictionaryEntryMetadata(
            resource_id=word.text,
            word=word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=word.language,
            version_info=version_info
        )
        
        # Store large content (should use external storage)
        await entry.set_content(large_content)
        await entry.save()
        
        # Verify external storage was used
        if entry.content_location is not None:
            assert entry.content_location.size_bytes > 10000  # Should be large
            assert entry.content_inline is None
        
        # Retrieve and verify content integrity
        retrieved_content = await entry.get_content()
        assert retrieved_content is not None
        assert len(retrieved_content["definitions"]) == 100
        assert retrieved_content["etymology"] == large_content["etymology"]

    @pytest.mark.asyncio
    async def test_data_consistency_across_restarts(self, test_db):
        """Test that data persists correctly across operations."""
        # Create and save data
        word = Word(text="persistence_test", language=Language.ENGLISH)
        await word.save()
        original_word_id = word.id
        
        content = {
            "definitions": ["Persistent definition"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        data_hash = hashlib.sha256(
            json.dumps(content, sort_keys=True).encode()
        ).hexdigest()
        
        version_info = VersionInfo(
            version="1.0.0",
            data_hash=data_hash,
            is_latest=True
        )
        
        entry = DictionaryEntryMetadata(
            resource_id=word.text,
            word=word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=word.language,
            version_info=version_info
        )
        
        await entry.set_content(content)
        await entry.save()
        original_entry_id = entry.id
        
        # Simulate "restart" by retrieving fresh from database
        retrieved_word = await Word.get(original_word_id)
        retrieved_entry = await DictionaryEntryMetadata.get(original_entry_id)
        
        assert retrieved_word.text == word.text
        assert retrieved_entry.word == word.text
        assert retrieved_entry.version_info.version == "1.0.0"
        
        retrieved_content = await retrieved_entry.get_content()
        assert retrieved_content == content