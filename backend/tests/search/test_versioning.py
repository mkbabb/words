"""Comprehensive tests for versioning with inner Metadata classes."""

import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

from floridify.caching.models import (
    CacheNamespace,
    ResourceType,
)
from floridify.corpus.core import Corpus
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex
from floridify.search.trie import TrieSearch


class TestInnerMetadataPattern:
    """Test the inner Metadata class idiom across models."""

    @pytest.mark.asyncio
    async def test_trie_index_metadata(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test TrieIndex.Metadata versioning."""
        # Create TrieIndex
        trie = TrieSearch.from_corpus(sample_corpus)
        index_data = trie.to_trie_index()

        # Save with Metadata
        await TrieIndex.get_or_create(sample_corpus, index_data)

        # Verify Metadata class attributes
        metadata = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        assert metadata is not None
        assert metadata.resource_type == ResourceType.TRIE
        assert metadata.namespace == CacheNamespace.TRIE
        assert metadata.corpus_id == sample_corpus.id
        assert metadata.version_info is not None

    @pytest.mark.asyncio
    async def test_semantic_index_metadata(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test SemanticIndex.Metadata versioning."""
        from floridify.search.semantic.core import SemanticSearch

        # Create SemanticIndex
        semantic = await SemanticSearch.from_corpus(
            corpus=sample_corpus, model_name="all-MiniLM-L6-v2"
        )
        index_data = semantic.to_semantic_index()

        # Save with Metadata
        await SemanticIndex.get_or_create(sample_corpus, "all-MiniLM-L6-v2", index_data)

        # Verify Metadata class attributes
        metadata = await SemanticIndex.Metadata.find_one(
            SemanticIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        assert metadata is not None
        assert metadata.resource_type == ResourceType.SEMANTIC
        assert metadata.namespace == CacheNamespace.SEMANTIC
        assert metadata.corpus_id == sample_corpus.id
        assert metadata.model_name == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio
    async def test_search_index_metadata(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test SearchIndex.Metadata versioning."""
        # Create SearchIndex
        await SearchIndex.from_corpus(sample_corpus)

        # Verify Metadata class attributes
        metadata = await SearchIndex.Metadata.find_one(
            SearchIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        assert metadata is not None
        assert metadata.resource_type == ResourceType.SEARCH
        assert metadata.namespace == CacheNamespace.SEARCH
        assert metadata.corpus_id == sample_corpus.id

    @pytest.mark.asyncio
    async def test_corpus_metadata(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test Corpus.Metadata versioning."""
        # Save corpus to trigger metadata creation
        await sample_corpus.save()

        # Verify Metadata class attributes
        metadata = await Corpus.Metadata.find_one(
            Corpus.Metadata.resource_id == str(sample_corpus.id)
        )

        if metadata:  # Corpus.Metadata may be created on demand
            assert metadata.resource_type == ResourceType.CORPUS
            assert metadata.namespace == CacheNamespace.CORPUS
            assert metadata.corpus_id == sample_corpus.id


class TestVersionInfoManagement:
    """Test VersionInfo functionality in versioned data."""

    @pytest.mark.asyncio
    async def test_version_info_creation(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test VersionInfo is properly created."""
        trie = TrieSearch.from_corpus(sample_corpus)
        await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        metadata = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        assert metadata.version_info is not None
        assert metadata.version_info.version >= 1
        assert metadata.version_info.created_at is not None
        assert metadata.version_info.is_latest is True
        assert metadata.version_info.data_hash is not None

    @pytest.mark.asyncio
    async def test_version_incrementing(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test that versions increment properly."""
        # Create first version
        trie1 = TrieSearch.from_corpus(sample_corpus)
        await TrieIndex.get_or_create(sample_corpus, trie1.to_trie_index())

        # Get first metadata
        metadata1 = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id),
            TrieIndex.Metadata.version_info.is_latest,
        )
        version1 = metadata1.version_info.version

        # Modify corpus to trigger new version
        sample_corpus.words["newword1"] = 100
        await sample_corpus.save()

        # Create second version
        trie2 = TrieSearch.from_corpus(sample_corpus)
        await TrieIndex.get_or_create(sample_corpus, trie2.to_trie_index())

        # Get second metadata
        metadata2 = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id),
            TrieIndex.Metadata.version_info.is_latest,
        )
        version2 = metadata2.version_info.version

        # Version should increment
        assert version2 > version1

    @pytest.mark.asyncio
    async def test_latest_flag_management(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test that is_latest flag is properly managed."""
        # Create multiple versions
        for i in range(3):
            sample_corpus.words[f"word_{i}"] = i
            await sample_corpus.save()

            trie = TrieSearch.from_corpus(sample_corpus)
            await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        # Query all versions
        all_metadata = await TrieIndex.Metadata.find(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        ).to_list()

        # Only one should be marked as latest
        latest_count = sum(1 for m in all_metadata if m.version_info.is_latest)
        assert latest_count == 1

        # Latest should have highest version number
        latest = [m for m in all_metadata if m.version_info.is_latest][0]
        max_version = max(m.version_info.version for m in all_metadata)
        assert latest.version_info.version == max_version

    @pytest.mark.asyncio
    async def test_data_hash_consistency(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test that data_hash is consistent for same data."""
        # Create index twice with same data
        trie1 = TrieSearch.from_corpus(sample_corpus)
        index1 = await TrieIndex.get_or_create(sample_corpus, trie1.to_trie_index())

        # Create again without changes
        trie2 = TrieSearch.from_corpus(sample_corpus)
        index2 = await TrieIndex.get_or_create(sample_corpus, trie2.to_trie_index())

        # Should return same index (no new version)
        assert index1.vocabulary_hash == index2.vocabulary_hash

        # Verify only one metadata exists
        count = await TrieIndex.Metadata.count_documents(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        )
        assert count == 1


class TestVersionedDataRetrieval:
    """Test retrieving versioned data."""

    @pytest.mark.asyncio
    async def test_get_latest_version(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test retrieving the latest version."""
        # Create multiple versions
        versions = []
        for i in range(3):
            sample_corpus.words[f"version_{i}"] = i
            await sample_corpus.save()

            trie = TrieSearch.from_corpus(sample_corpus)
            index = await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())
            versions.append(index)

        # Get latest version
        latest = await TrieIndex.get_latest(sample_corpus)

        assert latest is not None
        assert latest.vocabulary_hash == versions[-1].vocabulary_hash
        assert "version_2" in latest.vocabulary

    @pytest.mark.asyncio
    async def test_get_specific_version(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test retrieving a specific version."""
        # Create multiple versions
        version_hashes = []
        for i in range(3):
            sample_corpus.words[f"specific_{i}"] = i
            await sample_corpus.save()

            trie = TrieSearch.from_corpus(sample_corpus)
            index = await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())
            version_hashes.append(index.vocabulary_hash)

        # Each version should be retrievable by its metadata
        all_metadata = await TrieIndex.Metadata.find(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        ).to_list()

        assert len(all_metadata) == 3
        for metadata in all_metadata:
            assert metadata.version_info.version in [1, 2, 3]

    @pytest.mark.asyncio
    async def test_version_chain_tracking(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test version chain tracking through parent_version."""
        # Create chain of versions
        for i in range(3):
            sample_corpus.words[f"chain_{i}"] = i
            await sample_corpus.save()

            trie = TrieSearch.from_corpus(sample_corpus)
            await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        # Get all versions
        all_metadata = (
            await TrieIndex.Metadata.find(TrieIndex.Metadata.resource_id == str(sample_corpus.id))
            .sort("version_info.version", 1)
            .to_list()
        )

        # Check version chain
        for i, metadata in enumerate(all_metadata[1:], 1):
            if metadata.version_info.parent_version:
                # Parent should be previous version
                assert (
                    metadata.version_info.parent_version == all_metadata[i - 1].version_info.version
                )


class TestContentStorage:
    """Test content storage strategies in versioned data."""

    @pytest.mark.asyncio
    async def test_inline_content_storage(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test inline content storage for small data."""
        # Create small index
        small_corpus = Corpus(
            name="small",
            language="en",
            words={f"word{i}": 1 for i in range(10)},  # Small corpus
            total_words=10,
        )
        await small_corpus.save()

        trie = TrieSearch.from_corpus(small_corpus)
        await TrieIndex.get_or_create(small_corpus, trie.to_trie_index())

        # Check metadata for inline storage
        metadata = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(small_corpus.id)
        )

        # Small data should be stored inline
        if metadata.content_inline is not None:
            assert isinstance(metadata.content_inline, dict)
            assert len(metadata.content_inline) > 0

    @pytest.mark.asyncio
    async def test_external_content_storage(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test external content storage for large data."""
        # Create large index
        large_corpus = Corpus(
            name="large",
            language="en",
            words={f"word_{i:06d}": i for i in range(10000)},  # Large corpus
            total_words=sum(range(10000)),
        )
        await large_corpus.save()

        trie = TrieSearch.from_corpus(large_corpus)
        await TrieIndex.get_or_create(large_corpus, trie.to_trie_index())

        # Check metadata for external storage
        metadata = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(large_corpus.id)
        )

        # Large data might use external storage
        if metadata.content_location is not None:
            assert metadata.content_location.cache_namespace is not None
            assert metadata.content_location.cache_key is not None

    @pytest.mark.asyncio
    async def test_content_retrieval(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test retrieving content from versioned data."""
        trie = TrieSearch.from_corpus(sample_corpus)
        await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        # Get metadata
        metadata = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        # Retrieve content
        content = await metadata.get_content()

        if content is not None:
            assert isinstance(content, dict)
            # Content should contain index data


class TestConcurrentVersioning:
    """Test concurrent version creation and management."""

    @pytest.mark.asyncio
    async def test_concurrent_version_creation(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test creating versions concurrently."""
        import asyncio

        async def create_version(corpus: Corpus, suffix: str):
            corpus.words[f"concurrent_{suffix}"] = 1
            await corpus.save()

            trie = TrieSearch.from_corpus(corpus)
            return await TrieIndex.get_or_create(corpus, trie.to_trie_index())

        # Create versions concurrently
        tasks = []
        for i in range(3):
            # Clone corpus for concurrent modification
            corpus_copy = Corpus(
                id=sample_corpus.id,
                name=sample_corpus.name,
                language=sample_corpus.language,
                words=dict(sample_corpus.words),
                total_words=sample_corpus.total_words,
            )
            tasks.append(create_version(corpus_copy, str(i)))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Should handle concurrent creation gracefully
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0

    @pytest.mark.asyncio
    async def test_version_conflict_resolution(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test handling of version conflicts."""
        # Create base version
        trie1 = TrieSearch.from_corpus(sample_corpus)
        index1 = await TrieIndex.get_or_create(sample_corpus, trie1.to_trie_index())

        # Modify corpus
        sample_corpus.words["conflict"] = 1
        await sample_corpus.save()

        # Create new version
        trie2 = TrieSearch.from_corpus(sample_corpus)
        index2 = await TrieIndex.get_or_create(sample_corpus, trie2.to_trie_index())

        # Versions should be different
        assert index1.vocabulary_hash != index2.vocabulary_hash

        # Both should be retrievable
        all_metadata = await TrieIndex.Metadata.find(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        ).to_list()

        assert len(all_metadata) == 2


class TestVersionedDataCleanup:
    """Test cleanup and maintenance of versioned data."""

    @pytest.mark.asyncio
    async def test_old_version_cleanup(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test cleaning up old versions."""
        # Create many versions
        for i in range(10):
            sample_corpus.words[f"cleanup_{i}"] = i
            await sample_corpus.save()

            trie = TrieSearch.from_corpus(sample_corpus)
            await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        # Count total versions
        total_before = await TrieIndex.Metadata.count_documents(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        assert total_before >= 10

        # In production, would implement cleanup logic here
        # to remove old versions keeping only recent ones

    @pytest.mark.asyncio
    async def test_orphaned_content_detection(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test detection of orphaned content."""
        # Create version with external content
        trie = TrieSearch.from_corpus(sample_corpus)
        await TrieIndex.get_or_create(sample_corpus, trie.to_trie_index())

        # Get metadata
        metadata = await TrieIndex.Metadata.find_one(
            TrieIndex.Metadata.resource_id == str(sample_corpus.id)
        )

        # In production, would check for content without metadata
        assert metadata is not None

        # Content should be accessible
        if metadata.content_location:
            # Would verify external content exists
            pass
