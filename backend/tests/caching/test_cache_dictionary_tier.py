"""Tests for caching and versioning of DictionaryEntry objects.

Tests the complete caching and versioning workflow for DictionaryEntry
without mocking, using real storage and version management operations.
"""

import hashlib
import json

import pytest
import pytest_asyncio

from floridify.caching.core import get_global_cache, get_versioned_content, set_versioned_content
from floridify.caching.models import CacheNamespace, VersionInfo
from floridify.models.base import Language
from floridify.models.dictionary import DictionaryProvider, Word
from floridify.providers.dictionary.models import DictionaryProviderEntry


class TestDictionaryEntryCaching:
    """Test caching functionality for DictionaryEntry objects."""

    @pytest_asyncio.fixture
    async def sample_word(self, test_db):
        """Create a sample word for testing."""
        word = Word(text="cache_test", languages=[Language.ENGLISH])
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
                    "examples": ["This is a cache test example."],
                },
            ],
            "pronunciation": "/keɪʃ tɛst/",
            "etymology": "From test + cache",
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
            "source": "initial_provider",
        }

        data_hash_v1 = hashlib.sha256(json.dumps(content_v1, sort_keys=True).encode()).hexdigest()

        version_info_v1 = VersionInfo(version="1.0.0", data_hash=data_hash_v1, is_latest=True)

        entry_v1 = DictionaryProviderEntry.Metadata(
            resource_id=sample_word.text,
            word=sample_word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.languages[0],
            version_info=version_info_v1,
        )

        await set_versioned_content(entry_v1, content_v1)
        await entry_v1.save()

        # Verify v1 is saved and marked as latest
        assert entry_v1.version_info.is_latest is True
        retrieved_content_v1 = await get_versioned_content(entry_v1)
        assert retrieved_content_v1 == content_v1

        # Create version 2
        content_v2 = {
            "definitions": [
                {"text": "First version definition", "part_of_speech": "noun"},
                {"text": "Second version additional definition", "part_of_speech": "verb"},
            ],
            "source": "updated_provider",
            "etymology": "Added etymology in version 2",
        }

        data_hash_v2 = hashlib.sha256(json.dumps(content_v2, sort_keys=True).encode()).hexdigest()

        version_info_v2 = VersionInfo(
            version="2.0.0",
            data_hash=data_hash_v2,
            is_latest=True,
            supersedes=entry_v1.id,
        )

        entry_v2 = DictionaryProviderEntry.Metadata(
            resource_id=sample_word.text,
            word=sample_word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.languages[0],
            version_info=version_info_v2,
        )

        await set_versioned_content(entry_v2, content_v2)
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
        retrieved_content_v2 = await get_versioned_content(entry_v2)
        assert retrieved_content_v2 == content_v2
        assert len(retrieved_content_v2["definitions"]) == 2

    @pytest.mark.asyncio
    async def test_large_content_external_storage(self, test_db, sample_word):
        """Test automatic GridFS-backed external storage for large dictionary content."""
        # Create large content (> 16KB threshold)
        large_definitions = []
        for i in range(1000):
            large_definitions.append(
                {
                    "text": f"Definition {i}: " + "A" * 1000,  # 1KB per definition
                    "part_of_speech": "noun",
                    "examples": [f"Example {i}: " + "B" * 500 for _ in range(5)],
                },
            )

        large_content = {
            "definitions": large_definitions,
            "etymology": "C" * 10000,  # 10KB etymology
            "usage_notes": ["D" * 5000 for _ in range(10)],  # 50KB usage notes
        }

        data_hash = hashlib.sha256(json.dumps(large_content, sort_keys=True).encode()).hexdigest()

        version_info = VersionInfo(version="1.0.0", data_hash=data_hash, is_latest=True)

        entry = DictionaryProviderEntry.Metadata(
            resource_id=sample_word.text + "_large",
            word=sample_word.text + "_large",
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.languages[0],
            version_info=version_info,
        )

        # Large content goes to GridFS with L1/L2 cache warmed
        await set_versioned_content(entry, large_content)
        await entry.save()

        # Content should be stored externally in GridFS (not inline)
        assert entry.content_inline is None
        assert entry.content_location is not None
        assert entry.content_location.storage_type == "database"
        assert entry.content_location.path is not None
        # path should be a valid ObjectId string
        from bson import ObjectId

        ObjectId(entry.content_location.path)  # Raises if invalid

        # Verify content can be retrieved via get_versioned_content (from L1/L2 cache)
        retrieved_content = await get_versioned_content(entry)
        assert retrieved_content is not None
        assert len(retrieved_content["definitions"]) == 1000
        assert retrieved_content["etymology"] == large_content["etymology"]

    @pytest.mark.asyncio
    async def test_large_content_gridfs_recovery(self, test_db, sample_word):
        """Test that large content survives L1/L2 cache eviction via GridFS fallback."""
        large_content = {
            "definitions": [{"text": f"Def {i}: " + "X" * 500} for i in range(100)],
            "notes": "Y" * 20000,
        }

        data_hash = hashlib.sha256(json.dumps(large_content, sort_keys=True).encode()).hexdigest()
        version_info = VersionInfo(version="1.0.0", data_hash=data_hash, is_latest=True)

        entry = DictionaryProviderEntry.Metadata(
            resource_id=sample_word.text + "_recovery",
            word=sample_word.text + "_recovery",
            provider=DictionaryProvider.WIKTIONARY.value,
            language=sample_word.languages[0],
            version_info=version_info,
        )

        await set_versioned_content(entry, large_content)
        await entry.save()

        assert entry.content_location is not None
        assert entry.content_location.storage_type == "database"

        # Clear L1/L2 cache to simulate restart / cache expiry
        cache = await get_global_cache()
        await cache.clear_all()

        # Content should still be recoverable from GridFS
        recovered = await get_versioned_content(entry)
        assert recovered is not None
        assert len(recovered["definitions"]) == 100
        assert recovered["notes"] == large_content["notes"]

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
            definitions.append(
                {
                    "text": f"This is definition number {i} with repeated words and patterns that should compress well. "
                    * 10,
                    "part_of_speech": "noun" if i % 2 == 0 else "verb",
                    "examples": [f"Example sentence {i} with repeated patterns and words. " * 5],
                },
            )

        compressible_data = {
            "definitions": definitions,
            "etymology": "Etymology with many repeated words and phrases. " * 100,
            "notes": "Usage notes with repetitive content. " * 200,
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
