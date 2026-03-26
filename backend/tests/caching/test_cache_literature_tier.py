"""Tests for caching and versioning of LiteratureEntry objects.

Tests the complete caching and versioning workflow for LiteratureEntry
without mocking, using real storage and version management operations.
"""

import hashlib

import pytest
import pytest_asyncio

from floridify.caching.core import get_versioned_content, set_versioned_content
from floridify.caching.models import CacheNamespace, VersionInfo
from floridify.models.base import Language
from floridify.models.literature import AuthorInfo, Genre, LiteratureProvider, Period
from floridify.providers.literature.models import LiteratureEntry


class TestLiteratureEntryCaching:
    """Test caching functionality for LiteratureEntry objects."""

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
            language=Language.ENGLISH,
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
            "metadata": {"genre": "fiction", "period": "victorian"},
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
            "analysis": {"themes": ["beginning"]},
        }

        text_hash_v1 = hashlib.sha256(content_v1["full_text"].encode()).hexdigest()

        version_info_v1 = VersionInfo(version="1.0.0", data_hash=text_hash_v1, is_latest=True)

        entry_v1 = LiteratureEntry.Metadata(
            resource_id="evolving_novel",
            title="Evolving Novel",
            authors=[sample_author],
            source=LiteratureProvider.LOCAL_FILE,
            language=Language.ENGLISH,
            text_hash=text_hash_v1,
            text_size_bytes=len(content_v1["full_text"]),
            word_count=8,
            unique_words=7,
            version_info=version_info_v1,
        )

        await set_versioned_content(entry_v1, content_v1)
        await entry_v1.save()

        # Version 2: Extended content
        content_v2 = {
            "title": "Evolving Novel",
            "full_text": "Chapter 1: The beginning of the story. Chapter 2: The plot thickens with new developments.",
            "chapters": [
                "Chapter 1: The beginning of the story.",
                "Chapter 2: The plot thickens with new developments.",
            ],
            "word_count": 16,
            "analysis": {"themes": ["beginning", "development"]},
        }

        text_hash_v2 = hashlib.sha256(content_v2["full_text"].encode()).hexdigest()

        version_info_v2 = VersionInfo(
            version="2.0.0",
            data_hash=text_hash_v2,
            is_latest=True,
            supersedes=entry_v1.id,
        )

        entry_v2 = LiteratureEntry.Metadata(
            resource_id="evolving_novel",
            title="Evolving Novel",
            authors=[sample_author],
            source=LiteratureProvider.LOCAL_FILE,
            language=Language.ENGLISH,
            text_hash=text_hash_v2,
            text_size_bytes=len(content_v2["full_text"]),
            word_count=16,
            unique_words=13,
            version_info=version_info_v2,
        )

        await set_versioned_content(entry_v2, content_v2)
        await entry_v2.save()

        # Update v1 version chain
        entry_v1.version_info.is_latest = False
        entry_v1.version_info.superseded_by = entry_v2.id
        await entry_v1.save()

        # Verify version progression
        assert entry_v2.version_info.is_latest is True
        assert entry_v1.version_info.is_latest is False
        # Compare word counts from content, not metadata
        assert content_v2["word_count"] > content_v1["word_count"]

        # Verify content integrity
        retrieved_v1 = await get_versioned_content(entry_v1)
        retrieved_v2 = await get_versioned_content(entry_v2)

        assert len(retrieved_v1["chapters"]) == 1
        assert len(retrieved_v2["chapters"]) == 2
        assert retrieved_v2["word_count"] == 16

    @pytest.mark.asyncio
    async def test_large_literature_external_storage(self, test_db, sample_author):
        """Test GridFS-backed external storage for large literature files."""
        # Create a large literary work
        chapters = []
        full_text_parts = []

        for i in range(50):  # 50 chapters
            chapter_text = (
                f"Chapter {i + 1}: "
                + "This is a long chapter with many words and sentences. " * 1000
            )
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
                "detailed_notes": "A" * 100000,  # 100KB of notes
            },
        }

        text_hash = hashlib.sha256(large_content["full_text"].encode()).hexdigest()

        version_info = VersionInfo(version="1.0.0", data_hash=text_hash, is_latest=True)

        entry = LiteratureEntry.Metadata(
            resource_id="war_and_peace_large",
            title="War and Peace - Large Edition",
            authors=[sample_author],
            source=LiteratureProvider.GUTENBERG,
            language=Language.ENGLISH,
            text_hash=text_hash,
            text_size_bytes=len(large_content["full_text"]),
            word_count=large_content["word_count"],
            unique_words=large_content["word_count"] // 10,  # Estimate
            version_info=version_info,
        )

        # Large content goes to GridFS
        await set_versioned_content(entry, large_content)
        await entry.save()

        # Content should be stored externally via GridFS
        assert entry.content_inline is None
        assert entry.content_location is not None
        assert entry.content_location.storage_type == "database"
        assert entry.content_location.path is not None

        # Verify retrieval via get_versioned_content
        retrieved_content = await get_versioned_content(entry)
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
            "chapters": [
                repetitive_text[: len(repetitive_text) // 2],
                repetitive_text[len(repetitive_text) // 2 :],
            ],
            "analysis": {
                "repeated_phrases": ["best of times", "worst of times"] * 500,
                "repetitive_analysis": "This analysis contains many repeated words and phrases. "
                * 200,
            },
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
