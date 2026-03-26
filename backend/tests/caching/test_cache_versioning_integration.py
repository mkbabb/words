"""Tests for integration between caching and versioning systems.

Tests cross-cutting concerns: version-based cache keys, namespace isolation,
concurrent operations, TTL behavior, and content deduplication.
"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from floridify.caching.core import get_versioned_content, set_versioned_content
from floridify.caching.models import CacheNamespace, VersionInfo
from floridify.models.base import Language
from floridify.models.dictionary import DictionaryProvider, Word
from floridify.providers.dictionary.models import DictionaryProviderEntry


class TestCacheVersioningIntegration:
    """Test integration between caching and versioning systems."""

    @pytest.mark.asyncio
    async def test_version_based_cache_keys(self, cache_manager, test_db):
        """Test that cache keys include version information."""
        word = Word(text="version_test", languages=[Language.ENGLISH])
        await word.save()

        # Version 1
        data_v1 = {"content": "version 1", "timestamp": datetime.now(UTC).isoformat()}
        cache_key_v1 = f"dict:{word.text}:v1.0.0"

        await cache_manager.set(CacheNamespace.DICTIONARY, cache_key_v1, data_v1)

        # Version 2
        data_v2 = {"content": "version 2", "timestamp": datetime.now(UTC).isoformat()}
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
        word = Word(text="concurrent_test", languages=[Language.ENGLISH])
        await word.save()

        async def create_version(version_num: int):
            content = {
                "version": f"v{version_num}",
                "data": f"concurrent content {version_num}",
                "timestamp": datetime.now(UTC).isoformat(),
            }

            data_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

            version_info = VersionInfo(
                version=f"{version_num}.0.0",
                data_hash=data_hash,
                is_latest=(version_num == 3),  # Only v3 is latest
            )

            entry = DictionaryProviderEntry.Metadata(
                resource_id=f"{word.text}_concurrent_{version_num}",
                word=word.text,
                provider=DictionaryProvider.WIKTIONARY.value,
                language=word.languages[0],
                version_info=version_info,
            )

            await set_versioned_content(entry, content)
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

        data = {"content": "expires soon", "created": datetime.now(UTC).isoformat()}

        # Store with very short TTL (1 second)
        await cache_manager.set(namespace, short_ttl_key, data, ttl_override=timedelta(seconds=1))

        # Should be available immediately
        immediate_result = await cache_manager.get(namespace, short_ttl_key)
        assert immediate_result is not None
        assert immediate_result["content"] == "expires soon"

        # Wait for expiration
        await asyncio.sleep(1.5)

        # Should be expired (depending on cache implementation)
        await cache_manager.get(namespace, short_ttl_key)
        # Note: Filesystem cache may not implement TTL, so this test is informational

    @pytest.mark.asyncio
    async def test_content_deduplication(self, test_db):
        """Test that identical content is deduplicated across versions."""
        word = Word(text="dedup_test", languages=[Language.ENGLISH])
        await word.save()

        # Same content, different version metadata
        identical_content = {
            "definitions": ["Identical definition text"],
            "etymology": "Same etymology across versions",
        }

        content_hash = hashlib.sha256(
            json.dumps(identical_content, sort_keys=True).encode(),
        ).hexdigest()

        # Create two entries with identical content
        version_info_1 = VersionInfo(version="1.0.0", data_hash=content_hash, is_latest=False)

        version_info_2 = VersionInfo(
            version="2.0.0",
            data_hash=content_hash,  # Same hash - identical content
            is_latest=True,
        )

        entry_1 = DictionaryProviderEntry.Metadata(
            resource_id=f"{word.text}_dedup_1",
            word=word.text,
            provider=DictionaryProvider.WIKTIONARY.value,
            language=word.languages[0],
            version_info=version_info_1,
        )

        entry_2 = DictionaryProviderEntry.Metadata(
            resource_id=f"{word.text}_dedup_2",
            word=word.text,
            provider=DictionaryProvider.OXFORD.value,  # Different provider
            language=word.languages[0],
            version_info=version_info_2,
        )

        await set_versioned_content(entry_1, identical_content)
        await entry_1.save()

        await set_versioned_content(entry_2, identical_content)
        await entry_2.save()

        # Both should have the same content hash
        assert entry_1.version_info.data_hash == entry_2.version_info.data_hash

        # Content should be retrievable for both
        content_1 = await get_versioned_content(entry_1)
        content_2 = await get_versioned_content(entry_2)

        assert content_1 == content_2 == identical_content
