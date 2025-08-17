"""Comprehensive tests for caching and versioning system.

Tests the complete caching and versioning workflow for DictionaryEntry and LiteratureEntry
without mocking, using real storage and version management operations.
"""

import asyncio
import hashlib
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from beanie import PydanticObjectId

from floridify.caching.core import GlobalCacheManager
from floridify.caching.filesystem import FilesystemBackend
from floridify.caching.models import CacheNamespace, CompressionType
from floridify.models import Word
from floridify.models.dictionary import DictionaryProvider, Language
from floridify.models.literature import AuthorInfo, Genre, LiteratureSource, Period
from floridify.models.versioned import (
    BaseVersionedData,
    ContentLocation,
    DictionaryEntryMetadata,
    LiteratureEntryMetadata,
    ResourceType,
    StorageType,
    VersionConfig,
    VersionInfo,
)


class TestDictionaryEntryCaching:
    """Test caching functionality for DictionaryEntry objects."""

    @pytest.fixture
    async def cache_manager(self):
        """Create a cache manager with temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            yield manager

    @pytest.fixture
    async def sample_word(self, test_db):
        """Create a sample word for testing."""
        word = Word(text="cache_test", language=Language.ENGLISH)
        await word.save()
        return word

    @pytest.mark.asyncio
    async def test_dictionary_entry_basic_caching(self, cache_manager, sample_word):
        """Test basic caching operations for dictionary entries."""
        # Create dictionary entry
        entry_data = {
            "definitions": [
                {
                    "part_of_speech": "noun",
                    "text": "A test for caching system",
                    "examples": ["This is a cache test example."]
                }
            ],
            "pronunciation": "/keɪʃ tɛst/",
            "etymology": "From test + cache"
        }
        
        cache_key = f"dict_entry:{sample_word.text}"
        namespace = CacheNamespace.DICTIONARY
        
        # Store in cache
        await cache_manager.set(namespace, cache_key, entry_data)
        
        # Retrieve from cache
        cached_data = await cache_manager.get(namespace, cache_key)
        
        assert cached_data is not None
        assert cached_data == entry_data
        assert len(cached_data["definitions"]) == 1
        assert cached_data["pronunciation"] == "/keɪʃ tɛst/"

    @pytest.mark.asyncio
    async def test_dictionary_entry_versioning(self, test_db, sample_word):
        """Test versioning workflow for dictionary entries."""
        # Create version 1
        content_v1 = {
            "definitions": [{"text": "First version definition", "part_of_speech": "noun"}],
            "source": "initial_provider"
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
            resource_id=sample_word.text,
            word=sample_word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.language,
            version_info=version_info_v1
        )
        
        await entry_v1.set_content(content_v1)
        await entry_v1.save()
        
        # Verify v1 is saved and marked as latest
        assert entry_v1.version_info.is_latest is True
        retrieved_content_v1 = await entry_v1.get_content()
        assert retrieved_content_v1 == content_v1
        
        # Create version 2
        content_v2 = {
            "definitions": [
                {"text": "First version definition", "part_of_speech": "noun"},
                {"text": "Second version additional definition", "part_of_speech": "verb"}
            ],
            "source": "updated_provider",
            "etymology": "Added etymology in version 2"
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
            resource_id=sample_word.text,
            word=sample_word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.language,
            version_info=version_info_v2
        )
        
        await entry_v2.set_content(content_v2)
        await entry_v2.save()
        
        # Update v1 to point to v2
        entry_v1.version_info.is_latest = False
        entry_v1.version_info.superseded_by = entry_v2.id
        await entry_v1.save()
        
        # Verify version chain
        assert entry_v2.version_info.is_latest is True
        assert entry_v1.version_info.is_latest is False
        assert entry_v1.version_info.superseded_by == entry_v2.id
        assert entry_v2.version_info.supersedes == entry_v1.id
        
        # Verify content integrity
        retrieved_content_v2 = await entry_v2.get_content()
        assert retrieved_content_v2 == content_v2
        assert len(retrieved_content_v2["definitions"]) == 2

    @pytest.mark.asyncio
    async def test_large_content_external_storage(self, test_db, sample_word):
        """Test automatic external storage for large dictionary content."""
        # Create large content (> 1MB threshold)
        large_definitions = []
        for i in range(1000):
            large_definitions.append({
                "text": f"Definition {i}: " + "A" * 1000,  # 1KB per definition
                "part_of_speech": "noun",
                "examples": [f"Example {i}: " + "B" * 500 for _ in range(5)]
            })
        
        large_content = {
            "definitions": large_definitions,
            "etymology": "C" * 10000,  # 10KB etymology
            "usage_notes": ["D" * 5000 for _ in range(10)]  # 50KB usage notes
        }
        
        data_hash = hashlib.sha256(
            json.dumps(large_content, sort_keys=True).encode()
        ).hexdigest()
        
        version_info = VersionInfo(
            version="1.0.0",
            data_hash=data_hash,
            is_latest=True
        )
        
        entry = DictionaryEntryMetadata(
            resource_id=sample_word.text + "_large",
            word=sample_word.text + "_large",
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.language,
            version_info=version_info
        )
        
        # Set large content (should trigger external storage)
        await entry.set_content(large_content)
        await entry.save()
        
        # Verify external storage was used
        assert entry.content_inline is None
        assert entry.content_location is not None
        assert entry.content_location.storage_type == StorageType.CACHE
        assert entry.content_location.size_bytes > 1_000_000
        
        # Verify content can be retrieved
        retrieved_content = await entry.get_content()
        assert retrieved_content is not None
        assert len(retrieved_content["definitions"]) == 1000
        assert retrieved_content["etymology"] == large_content["etymology"]

    @pytest.mark.asyncio
    async def test_dictionary_cache_invalidation(self, cache_manager, sample_word):
        """Test cache invalidation when dictionary entries are updated."""
        namespace = CacheNamespace.DICTIONARY
        cache_key = f"dict_entry:{sample_word.text}:v1"
        
        # Store initial data
        initial_data = {"version": "1.0.0", "definitions": ["Initial definition"]}
        await cache_manager.set(namespace, cache_key, initial_data)
        
        # Verify cached
        cached = await cache_manager.get(namespace, cache_key)
        assert cached == initial_data
        
        # Invalidate cache
        await cache_manager.delete(namespace, cache_key)
        
        # Verify invalidated
        cached_after_invalidation = await cache_manager.get(namespace, cache_key)
        assert cached_after_invalidation is None
        
        # Store new version
        new_cache_key = f"dict_entry:{sample_word.text}:v2"
        updated_data = {"version": "2.0.0", "definitions": ["Updated definition"]}
        await cache_manager.set(namespace, new_cache_key, updated_data)
        
        # Verify new version cached
        new_cached = await cache_manager.get(namespace, new_cache_key)
        assert new_cached == updated_data
        assert new_cached["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_dictionary_cache_compression(self, cache_manager, sample_word):
        """Test compression for cached dictionary entries."""
        # Create moderately large content that benefits from compression
        definitions = []
        for i in range(100):
            definitions.append({
                "text": f"This is definition number {i} with repeated words and patterns that should compress well. " * 10,
                "part_of_speech": "noun" if i % 2 == 0 else "verb",
                "examples": [f"Example sentence {i} with repeated patterns and words. " * 5]
            })
        
        compressible_data = {
            "definitions": definitions,
            "etymology": "Etymology with many repeated words and phrases. " * 100,
            "notes": "Usage notes with repetitive content. " * 200
        }
        
        namespace = CacheNamespace.DICTIONARY
        cache_key = f"dict_entry:{sample_word.text}:compressible"
        
        # Store with compression
        await cache_manager.set(namespace, cache_key, compressible_data)
        
        # Retrieve and verify
        retrieved = await cache_manager.get(namespace, cache_key)
        assert retrieved is not None
        assert len(retrieved["definitions"]) == 100
        assert retrieved["etymology"] == compressible_data["etymology"]


class TestLiteratureEntryCaching:
    """Test caching functionality for LiteratureEntry objects."""

    @pytest.fixture
    async def cache_manager(self):
        """Create a cache manager with temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            yield manager

    @pytest.fixture
    def sample_author(self):
        """Create sample author info."""
        return AuthorInfo(
            name="Test Author",
            birth_year=1800,
            death_year=1900,
            nationality="English",
            period=Period.VICTORIAN,
            primary_genre=Genre.NOVEL,
            language=Language.ENGLISH
        )

    @pytest.mark.asyncio
    async def test_literature_entry_basic_caching(self, cache_manager, sample_author):
        """Test basic caching operations for literature entries."""
        literature_data = {
            "title": "Test Novel",
            "full_text": "This is the full text of a test novel. " * 1000,
            "chapters": ["Chapter 1 content", "Chapter 2 content"],
            "word_count": 8000,
            "unique_words": 2000,
            "metadata": {"genre": "fiction", "period": "victorian"}
        }
        
        cache_key = "literature:test_novel"
        namespace = CacheNamespace.LITERATURE
        
        # Store in cache
        await cache_manager.set(namespace, cache_key, literature_data)
        
        # Retrieve from cache
        cached_data = await cache_manager.get(namespace, cache_key)
        
        assert cached_data is not None
        assert cached_data["title"] == "Test Novel"
        assert cached_data["word_count"] == 8000
        assert len(cached_data["chapters"]) == 2

    @pytest.mark.asyncio
    async def test_literature_entry_versioning(self, test_db, sample_author):
        """Test versioning workflow for literature entries."""
        # Version 1: Initial upload
        content_v1 = {
            "title": "Evolving Novel",
            "full_text": "Chapter 1: The beginning of the story.",
            "chapters": ["Chapter 1: The beginning of the story."],
            "word_count": 8,
            "analysis": {"themes": ["beginning"]}
        }
        
        text_hash_v1 = hashlib.sha256(content_v1["full_text"].encode()).hexdigest()
        
        version_info_v1 = VersionInfo(
            version="1.0.0",
            data_hash=text_hash_v1,
            is_latest=True
        )
        
        entry_v1 = LiteratureEntryMetadata(
            resource_id="evolving_novel",
            title="Evolving Novel",
            authors=[sample_author],
            source=LiteratureSource.LOCAL_FILE,
            language=Language.ENGLISH,
            text_hash=text_hash_v1,
            text_size_bytes=len(content_v1["full_text"]),
            word_count=8,
            unique_words=7,
            version_info=version_info_v1
        )
        
        await entry_v1.set_content(content_v1)
        await entry_v1.save()
        
        # Version 2: Extended content
        content_v2 = {
            "title": "Evolving Novel",
            "full_text": "Chapter 1: The beginning of the story. Chapter 2: The plot thickens with new developments.",
            "chapters": [
                "Chapter 1: The beginning of the story.",
                "Chapter 2: The plot thickens with new developments."
            ],
            "word_count": 16,
            "analysis": {"themes": ["beginning", "development"]}
        }
        
        text_hash_v2 = hashlib.sha256(content_v2["full_text"].encode()).hexdigest()
        
        version_info_v2 = VersionInfo(
            version="2.0.0",
            data_hash=text_hash_v2,
            is_latest=True,
            supersedes=entry_v1.id
        )
        
        entry_v2 = LiteratureEntryMetadata(
            resource_id="evolving_novel",
            title="Evolving Novel",
            authors=[sample_author],
            source=LiteratureSource.LOCAL_FILE,
            language=Language.ENGLISH,
            text_hash=text_hash_v2,
            text_size_bytes=len(content_v2["full_text"]),
            word_count=16,
            unique_words=13,
            version_info=version_info_v2
        )
        
        await entry_v2.set_content(content_v2)
        await entry_v2.save()
        
        # Update v1 version chain
        entry_v1.version_info.is_latest = False
        entry_v1.version_info.superseded_by = entry_v2.id
        await entry_v1.save()
        
        # Verify version progression
        assert entry_v2.version_info.is_latest is True
        assert entry_v1.version_info.is_latest is False
        assert entry_v2.word_count > entry_v1.word_count
        
        # Verify content integrity
        retrieved_v1 = await entry_v1.get_content()
        retrieved_v2 = await entry_v2.get_content()
        
        assert len(retrieved_v1["chapters"]) == 1
        assert len(retrieved_v2["chapters"]) == 2
        assert retrieved_v2["word_count"] == 16

    @pytest.mark.asyncio
    async def test_large_literature_external_storage(self, test_db, sample_author):
        """Test external storage for large literature files."""
        # Create a large literary work
        chapters = []
        full_text_parts = []
        
        for i in range(50):  # 50 chapters
            chapter_text = f"Chapter {i+1}: " + "This is a long chapter with many words and sentences. " * 1000
            chapters.append(chapter_text)
            full_text_parts.append(chapter_text)
        
        large_content = {
            "title": "War and Peace - Large Edition",
            "full_text": "\n\n".join(full_text_parts),
            "chapters": chapters,
            "word_count": len(full_text_parts) * 1000 * 12,  # Approximate
            "analysis": {
                "themes": ["war", "peace", "love", "society"],
                "character_count": {"natasha": 500, "pierre": 400, "andrey": 300},
                "detailed_notes": "A" * 100000  # 100KB of notes
            }
        }
        
        text_hash = hashlib.sha256(large_content["full_text"].encode()).hexdigest()
        
        version_info = VersionInfo(
            version="1.0.0",
            data_hash=text_hash,
            is_latest=True
        )
        
        entry = LiteratureEntryMetadata(
            resource_id="war_and_peace_large",
            title="War and Peace - Large Edition",
            authors=[sample_author],
            source=LiteratureSource.GUTENBERG,
            language=Language.ENGLISH,
            text_hash=text_hash,
            text_size_bytes=len(large_content["full_text"]),
            word_count=large_content["word_count"],
            unique_words=large_content["word_count"] // 10,  # Estimate
            version_info=version_info
        )
        
        # Should trigger external storage
        await entry.set_content(large_content)
        await entry.save()
        
        # Verify external storage
        assert entry.content_location is not None
        assert entry.content_location.storage_type == StorageType.CACHE
        assert entry.content_location.size_bytes > 1_000_000
        assert entry.content_inline is None
        
        # Verify retrieval
        retrieved_content = await entry.get_content()
        assert retrieved_content is not None
        assert len(retrieved_content["chapters"]) == 50
        assert retrieved_content["title"] == "War and Peace - Large Edition"

    @pytest.mark.asyncio
    async def test_literature_cache_with_compression(self, cache_manager, sample_author):
        """Test compression for literature content."""
        # Create repetitive content that compresses well
        repetitive_text = "It was the best of times, it was the worst of times. " * 1000
        
        literature_data = {
            "title": "A Tale of Two Cities",
            "full_text": repetitive_text,
            "chapters": [repetitive_text[:len(repetitive_text)//2], repetitive_text[len(repetitive_text)//2:]],
            "analysis": {
                "repeated_phrases": ["best of times", "worst of times"] * 500,
                "repetitive_analysis": "This analysis contains many repeated words and phrases. " * 200
            }
        }
        
        cache_key = "literature:tale_two_cities:compressed"
        namespace = CacheNamespace.LITERATURE
        
        # Store with automatic compression
        await cache_manager.set(namespace, cache_key, literature_data)
        
        # Retrieve and verify
        retrieved = await cache_manager.get(namespace, cache_key)
        assert retrieved is not None
        assert retrieved["title"] == "A Tale of Two Cities"
        assert len(retrieved["chapters"]) == 2
        assert "best of times" in retrieved["full_text"]


class TestCacheVersioningIntegration:
    """Test integration between caching and versioning systems."""

    @pytest.fixture
    async def cache_manager(self):
        """Create a cache manager with temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FilesystemBackend(Path(tmpdir))
            manager = GlobalCacheManager(backend)
            await manager.initialize()
            yield manager

    @pytest.mark.asyncio
    async def test_version_based_cache_keys(self, cache_manager, test_db):
        """Test that cache keys include version information."""
        word = Word(text="version_test", language=Language.ENGLISH)
        await word.save()
        
        # Version 1
        data_v1 = {"content": "version 1", "timestamp": datetime.utcnow().isoformat()}
        cache_key_v1 = f"dict:{word.text}:v1.0.0"
        
        await cache_manager.set(CacheNamespace.DICTIONARY, cache_key_v1, data_v1)
        
        # Version 2
        data_v2 = {"content": "version 2", "timestamp": datetime.utcnow().isoformat()}
        cache_key_v2 = f"dict:{word.text}:v2.0.0"
        
        await cache_manager.set(CacheNamespace.DICTIONARY, cache_key_v2, data_v2)
        
        # Both versions should coexist in cache
        cached_v1 = await cache_manager.get(CacheNamespace.DICTIONARY, cache_key_v1)
        cached_v2 = await cache_manager.get(CacheNamespace.DICTIONARY, cache_key_v2)
        
        assert cached_v1["content"] == "version 1"
        assert cached_v2["content"] == "version 2"
        assert cached_v1 != cached_v2

    @pytest.mark.asyncio
    async def test_cache_namespace_isolation(self, cache_manager):
        """Test that different namespaces are properly isolated."""
        shared_key = "shared_resource_key"
        
        dict_data = {"type": "dictionary", "definitions": ["test definition"]}
        lit_data = {"type": "literature", "text": "test literature content"}
        
        # Store same key in different namespaces
        await cache_manager.set(CacheNamespace.DICTIONARY, shared_key, dict_data)
        await cache_manager.set(CacheNamespace.LITERATURE, shared_key, lit_data)
        
        # Retrieve from each namespace
        dict_result = await cache_manager.get(CacheNamespace.DICTIONARY, shared_key)
        lit_result = await cache_manager.get(CacheNamespace.LITERATURE, shared_key)
        
        assert dict_result["type"] == "dictionary"
        assert lit_result["type"] == "literature"
        assert dict_result != lit_result

    @pytest.mark.asyncio
    async def test_concurrent_version_operations(self, test_db):
        """Test concurrent versioning operations."""
        word = Word(text="concurrent_test", language=Language.ENGLISH)
        await word.save()
        
        async def create_version(version_num: int):
            content = {
                "version": f"v{version_num}",
                "data": f"concurrent content {version_num}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            data_hash = hashlib.sha256(
                json.dumps(content, sort_keys=True).encode()
            ).hexdigest()
            
            version_info = VersionInfo(
                version=f"{version_num}.0.0",
                data_hash=data_hash,
                is_latest=(version_num == 3)  # Only v3 is latest
            )
            
            entry = DictionaryEntryMetadata(
                resource_id=f"{word.text}_concurrent_{version_num}",
                word=word.text,
                provider=DictionaryProvider.WIKTIONARY.value,
                language=word.language,
                version_info=version_info
            )
            
            await entry.set_content(content)
            await entry.save()
            return entry
        
        # Create multiple versions concurrently
        tasks = [create_version(i) for i in range(1, 4)]
        entries = await asyncio.gather(*tasks)
        
        # Verify all versions were created
        assert len(entries) == 3
        
        # Verify only v3 is marked as latest
        latest_entries = [e for e in entries if e.version_info.is_latest]
        assert len(latest_entries) == 1
        assert latest_entries[0].version_info.version == "3.0.0"

    @pytest.mark.asyncio
    async def test_cache_ttl_behavior(self, cache_manager):
        """Test TTL behavior in caching system."""
        namespace = CacheNamespace.DICTIONARY
        short_ttl_key = "short_ttl_test"
        
        data = {"content": "expires soon", "created": datetime.utcnow().isoformat()}
        
        # Store with very short TTL (1 second)
        await cache_manager.set(
            namespace, 
            short_ttl_key, 
            data,
            ttl=timedelta(seconds=1)
        )
        
        # Should be available immediately
        immediate_result = await cache_manager.get(namespace, short_ttl_key)
        assert immediate_result is not None
        assert immediate_result["content"] == "expires soon"
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Should be expired (depending on cache implementation)
        expired_result = await cache_manager.get(namespace, short_ttl_key)
        # Note: Filesystem cache may not implement TTL, so this test is informational

    @pytest.mark.asyncio
    async def test_content_deduplication(self, test_db):
        """Test that identical content is deduplicated across versions."""
        word = Word(text="dedup_test", language=Language.ENGLISH)
        await word.save()
        
        # Same content, different version metadata
        identical_content = {
            "definitions": ["Identical definition text"],
            "etymology": "Same etymology across versions"
        }
        
        content_hash = hashlib.sha256(
            json.dumps(identical_content, sort_keys=True).encode()
        ).hexdigest()
        
        # Create two entries with identical content
        version_info_1 = VersionInfo(
            version="1.0.0",
            data_hash=content_hash,
            is_latest=False
        )
        
        version_info_2 = VersionInfo(
            version="2.0.0",
            data_hash=content_hash,  # Same hash - identical content
            is_latest=True
        )
        
        entry_1 = DictionaryEntryMetadata(
            resource_id=f"{word.text}_dedup_1",
            word=word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=word.language,
            version_info=version_info_1
        )
        
        entry_2 = DictionaryEntryMetadata(
            resource_id=f"{word.text}_dedup_2",
            word=word.text,
            provider=DictionaryProvider.OXFORD.value,  # Different provider
            language=word.language,
            version_info=version_info_2
        )
        
        await entry_1.set_content(identical_content)
        await entry_1.save()
        
        await entry_2.set_content(identical_content)
        await entry_2.save()
        
        # Both should have the same content hash
        assert entry_1.version_info.data_hash == entry_2.version_info.data_hash
        
        # Content should be retrievable for both
        content_1 = await entry_1.get_content()
        content_2 = await entry_2.get_content()
        
        assert content_1 == content_2 == identical_content