"""Comprehensive provider tests with MongoDB and versioning.

Tests the complete provider functionality including:
- MongoDB persistence of provider data
- Version management for provider responses
- Caching and deduplication
- Batch operations
- Rate limiting
- Provider-specific metadata
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace, ResourceType, VersionConfig
from floridify.models.dictionary import DictionaryProvider


@pytest.mark.asyncio
class TestProviderMongoDBIntegration:
    """Test provider MongoDB persistence and operations."""

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    @pytest_asyncio.fixture
    async def mock_http_client(self):
        """Create mock HTTP client for provider testing."""
        client = AsyncMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "word": "test",
            "meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "a test"}]}],
        }
        client.get.return_value = response
        return client

    async def test_dictionary_provider_persistence(
        self, test_db, versioned_manager, mock_http_client
    ):
        """Test saving and loading dictionary provider data."""
        # Create provider response
        provider_data = {
            "word": "example",
            "provider": DictionaryProvider.FREE_DICTIONARY,
            "meanings": [
                {
                    "partOfSpeech": "noun",
                    "definitions": [
                        {"definition": "a thing characteristic of its kind"},
                        {"definition": "a person or thing regarded as typical"},
                    ],
                }
            ],
            "phonetics": [{"text": "/ɪɡˈzæmpəl/", "audio": "https://example.com/audio.mp3"}],
            "retrieved_at": datetime.now(UTC).isoformat(),
        }

        # Save as versioned data
        saved = await versioned_manager.save(
            resource_id=f"dict-{provider_data['word']}-{provider_data['provider']}",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content=provider_data,
            metadata={"provider": provider_data["provider"], "word": provider_data["word"]},
        )

        assert saved.id is not None
        assert saved.resource_type == ResourceType.DICTIONARY

        # Load from MongoDB
        loaded = await versioned_manager.get_latest(
            resource_id=f"dict-{provider_data['word']}-{provider_data['provider']}",
            resource_type=ResourceType.DICTIONARY,
        )

        assert loaded is not None
        from floridify.caching.core import get_versioned_content

        content = await get_versioned_content(loaded)
        assert content["word"] == "example"
        assert len(content["meanings"][0]["definitions"]) == 2

    async def test_language_provider_persistence(self, test_db, versioned_manager):
        """Test saving and loading language provider data."""
        # Create language corpus data
        language_data = {
            "corpus_name": "english-wiki",
            "language": "en",
            "source": "wikipedia",
            "vocabulary": ["the", "be", "to", "of", "and"],
            "word_frequencies": {"the": 1000, "be": 800, "to": 700, "of": 600, "and": 500},
            "total_words": 100000,
            "unique_words": 50000,
            "scraped_at": datetime.now(UTC).isoformat(),
        }

        # Save as versioned data
        saved = await versioned_manager.save(
            resource_id=f"lang-{language_data['corpus_name']}",
            resource_type=ResourceType.LANGUAGE,
            namespace=CacheNamespace.CORPUS,
            content=language_data,
            metadata={"source": language_data["source"], "language": language_data["language"]},
        )

        assert saved.resource_type == ResourceType.LANGUAGE

        # Load and verify
        loaded = await versioned_manager.get_latest(
            resource_id=f"lang-{language_data['corpus_name']}",
            resource_type=ResourceType.LANGUAGE,
        )

        assert loaded.content["corpus_name"] == "english-wiki"
        assert loaded.content["unique_words"] == 50000

    async def test_literature_provider_persistence(self, test_db, versioned_manager):
        """Test saving and loading literature provider data."""
        # Create literature text data
        literature_data = {
            "title": "Pride and Prejudice",
            "author": "Jane Austen",
            "source": "gutenberg",
            "text_id": "pg1342",
            "content": "It is a truth universally acknowledged...",
            "metadata": {
                "year": 1813,
                "genre": "romance",
                "language": "en",
                "word_count": 120000,
            },
            "processed_at": datetime.now(UTC).isoformat(),
        }

        # Save as versioned data
        saved = await versioned_manager.save(
            resource_id=f"lit-{literature_data['text_id']}",
            resource_type=ResourceType.LITERATURE,
            namespace=CacheNamespace.CORPUS,
            content=literature_data,
            metadata=literature_data["metadata"],
        )

        assert saved.resource_type == ResourceType.LITERATURE

        # Load and verify
        loaded = await versioned_manager.get_latest(
            resource_id=f"lit-{literature_data['text_id']}",
            resource_type=ResourceType.LITERATURE,
        )

        assert loaded.content["title"] == "Pride and Prejudice"
        assert loaded.metadata["year"] == 1813

    async def test_provider_versioning(self, test_db, versioned_manager):
        """Test version management for provider data."""
        resource_id = "provider-version-test"

        # V1: Initial API response
        v1_data = {
            "word": "test",
            "definitions": ["a procedure for critical evaluation"],
            "version": "1.0.0",
        }

        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content=v1_data,
            config=VersionConfig(version="1.0.0"),
        )

        # V2: Updated with more definitions
        v2_data = {
            "word": "test",
            "definitions": [
                "a procedure for critical evaluation",
                "a basis for evaluation",
                "an examination",
            ],
            "version": "2.0.0",
        }

        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content=v2_data,
            config=VersionConfig(version="2.0.0"),
        )

        # Verify version chain
        assert v2.version_info.supersedes == v1.id

        # V1 should no longer be latest
        v1_refreshed = await versioned_manager.get_by_id(v1.id)
        assert not v1_refreshed.version_info.is_latest
        assert v1_refreshed.version_info.superseded_by == v2.id

    async def test_provider_deduplication(self, test_db, versioned_manager):
        """Test that identical provider responses are deduplicated."""
        resource_id = "dedup-test"

        # Same content fetched multiple times
        identical_content = {
            "word": "duplicate",
            "definition": "exactly like something else",
            "provider": "test_provider",
        }

        # Save same content 3 times
        saves = []
        for _ in range(3):
            saved = await versioned_manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.PROVIDER,
                content=identical_content,
            )
            saves.append(saved)

        # All should have same content hash and ID
        hashes = [s.content_hash for s in saves]
        ids = [s.id for s in saves]

        assert len(set(hashes)) == 1  # Same hash
        assert len(set(ids)) == 1  # Same document

    async def test_batch_provider_operations(self, test_db, versioned_manager):
        """Test batch operations for multiple provider requests."""
        words = ["apple", "banana", "cherry", "date", "elderberry"]

        # Batch save provider responses
        save_tasks = []
        for word in words:
            task = versioned_manager.save(
                resource_id=f"batch-{word}",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.PROVIDER,
                content={
                    "word": word,
                    "definition": f"Definition of {word}",
                    "provider": "batch_test",
                },
            )
            save_tasks.append(task)

        saved = await asyncio.gather(*save_tasks)
        assert len(saved) == len(words)

        # Batch load
        load_tasks = [
            versioned_manager.get_latest(
                resource_id=f"batch-{word}",
                resource_type=ResourceType.DICTIONARY,
            )
            for word in words
        ]

        loaded = await asyncio.gather(*load_tasks)
        assert len(loaded) == len(words)
        assert all(entry.content["word"] in words for entry in loaded)

    async def test_provider_rate_limiting(self, test_db, versioned_manager):
        """Test rate limiting tracking in provider metadata."""
        resource_id = "rate-limit-test"

        # Simulate rate-limited response
        rate_limit_data = {
            "word": "limited",
            "error": "rate_limit_exceeded",
            "retry_after": 60,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        saved = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content=rate_limit_data,
            metadata={
                "rate_limited": True,
                "retry_after_seconds": 60,
                "provider": "test_provider",
            },
        )

        # Check rate limit metadata
        assert saved.metadata["rate_limited"] is True
        assert saved.metadata["retry_after_seconds"] == 60

    async def test_provider_error_handling(self, test_db, versioned_manager):
        """Test storing provider error responses."""
        resource_id = "error-test"

        # Store error response
        error_data = {
            "word": "nonexistent",
            "error": "word_not_found",
            "provider": "test_provider",
            "status_code": 404,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content=error_data,
            metadata={"error": True, "status_code": 404},
        )

        # Verify error is stored
        loaded = await versioned_manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
        )

        assert loaded.content["error"] == "word_not_found"
        assert loaded.metadata["error"] is True

    async def test_provider_cache_expiry(self, test_db, versioned_manager):
        """Test provider cache expiry and refresh."""
        resource_id = "expiry-test"

        # Save initial response with TTL metadata
        initial = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": "expire", "definition": "to come to an end"},
            metadata={
                "cached_at": datetime.now(UTC).isoformat(),
                "ttl_seconds": 3600,
                "provider": "test_provider",
            },
        )

        # Simulate cache refresh after expiry
        refreshed = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": "expire", "definition": "to come to an end; to die"},
            config=VersionConfig(force_rebuild=True),
            metadata={
                "cached_at": datetime.now(UTC).isoformat(),
                "ttl_seconds": 3600,
                "provider": "test_provider",
                "refreshed": True,
            },
        )

        # Should create new version despite similar content
        assert refreshed.id != initial.id
        assert refreshed.metadata["refreshed"] is True


@pytest.mark.asyncio
class TestProviderIntegration:
    """Test integration between different provider types."""

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_cross_provider_aggregation(self, test_db, versioned_manager):
        """Test aggregating data from multiple providers."""
        word = "example"

        # Save data from multiple dictionary providers
        providers = [
            ("free_dictionary", {"definition": "a representative form"}),
            ("merriam_webster", {"definition": "one that serves as a pattern"}),
            ("oxford", {"definition": "a thing characteristic of its kind"}),
        ]

        saved_ids = []
        for provider_name, data in providers:
            saved = await versioned_manager.save(
                resource_id=f"multi-{word}-{provider_name}",
                resource_type=ResourceType.DICTIONARY,
                namespace=CacheNamespace.PROVIDER,
                content={
                    "word": word,
                    "provider": provider_name,
                    **data,
                },
                metadata={"provider": provider_name, "word": word},
            )
            saved_ids.append(saved.id)

        # Load all provider data for the word
        loaded = []
        for provider_name, _ in providers:
            data = await versioned_manager.get_latest(
                resource_id=f"multi-{word}-{provider_name}",
                resource_type=ResourceType.DICTIONARY,
            )
            loaded.append(data)

        # Verify all providers contributed
        assert len(loaded) == 3
        providers_found = [entry.metadata["provider"] for entry in loaded]
        assert set(providers_found) == {"free_dictionary", "merriam_webster", "oxford"}

    async def test_provider_dependency_tracking(self, test_db, versioned_manager):
        """Test tracking dependencies between provider data."""
        # Save dictionary entry
        dict_entry = await versioned_manager.save(
            resource_id="dep-dict-entry",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": "dependency", "definition": "the state of relying on"},
        )

        # Save pronunciation that depends on dictionary entry
        pronunciation = await versioned_manager.save(
            resource_id="dep-pronunciation",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": "dependency", "ipa": "/dɪˈpɛndənsi/"},
            metadata={"depends_on": str(dict_entry.id)},
        )

        # Save etymology that depends on both
        etymology = await versioned_manager.save(
            resource_id="dep-etymology",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": "dependency", "origin": "from Latin dependere"},
            metadata={
                "depends_on": [str(dict_entry.id), str(pronunciation.id)],
            },
        )

        # Verify dependency chain
        assert etymology.metadata["depends_on"] == [str(dict_entry.id), str(pronunciation.id)]

    async def test_provider_fallback_chain(self, test_db, versioned_manager):
        """Test fallback chain when primary provider fails."""
        word = "fallback"

        # Primary provider fails
        primary_fail = await versioned_manager.save(
            resource_id=f"fallback-{word}-primary",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": word, "error": "service_unavailable"},
            metadata={"provider": "primary", "failed": True},
        )

        # Secondary provider succeeds
        secondary_success = await versioned_manager.save(
            resource_id=f"fallback-{word}-secondary",
            resource_type=ResourceType.DICTIONARY,
            namespace=CacheNamespace.PROVIDER,
            content={"word": word, "definition": "an alternative plan"},
            metadata={"provider": "secondary", "fallback_from": "primary"},
        )

        # Verify fallback was used
        assert secondary_success.metadata["fallback_from"] == "primary"
        assert primary_fail.metadata["failed"] is True
