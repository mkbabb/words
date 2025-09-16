"""MongoDB persistence tests for search components using real database."""

import pytest
from beanie import PydanticObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from floridify.caching.models import CacheNamespace, ResourceType, VersionInfo
from floridify.corpus.core import Corpus
from floridify.search.models import TrieIndex
from floridify.search.trie import TrieSearch


@pytest.mark.asyncio
class TestMongoDBPersistence:
    """Test search persistence with real MongoDB."""

    async def test_trie_index_save_and_retrieve(self, test_db: AsyncIOMotorDatabase):
        """Test saving and retrieving TrieIndex with MongoDB."""
        # Create a simple corpus
        vocabulary = ["apple", "banana", "cherry"]
        corpus = Corpus(
            corpus_name="mongo-test",
            language="en",
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            vocabulary_to_index={word: i for i, word in enumerate(vocabulary)},
            unique_word_count=len(vocabulary),
            total_word_count=len(vocabulary),
        )

        # Create and save metadata directly to test MongoDB persistence
        metadata = TrieIndex.Metadata(
            resource_id="mongo-test:trie",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.TRIE,
            corpus_id=PydanticObjectId(),
            version_info=VersionInfo(data_hash="test_hash_123"),
        )

        # Set some test content directly on content_inline
        test_content = {
            "corpus_name": "mongo-test",
            "vocabulary_hash": "test_hash",
            "trie_data": vocabulary,
            "word_count": len(vocabulary),
        }
        metadata.content_inline = test_content

        # Save to MongoDB
        await metadata.save()

        # Retrieve by ID
        retrieved_metadata = await TrieIndex.Metadata.get(metadata.id)

        assert retrieved_metadata is not None
        assert retrieved_metadata.resource_id == "mongo-test:trie"
        assert retrieved_metadata.resource_type == ResourceType.TRIE

        # Test content retrieval
        retrieved_content = await retrieved_metadata.get_content()
        assert retrieved_content is not None
        assert retrieved_content["corpus_name"] == "mongo-test"
        assert retrieved_content["word_count"] == len(vocabulary)

    async def test_versioning_with_mongodb(self, test_db: AsyncIOMotorDatabase):
        """Test version management with real MongoDB."""
        # Create first version metadata
        metadata_v1 = TrieIndex.Metadata(
            resource_id="version-test:trie",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.TRIE,
            corpus_id=PydanticObjectId(),
            version_info=VersionInfo(data_hash="hash_v1", version="1.0.0", is_latest=True),
        )

        # Set content for version 1
        content_v1 = {
            "corpus_name": "version-test",
            "vocabulary_hash": "hash_v1",
            "trie_data": ["one", "two", "three"],
            "word_count": 3,
        }
        metadata_v1.content_inline = content_v1
        await metadata_v1.save()

        # Create second version metadata
        metadata_v2 = TrieIndex.Metadata(
            resource_id="version-test:trie",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.TRIE,
            corpus_id=metadata_v1.corpus_id,
            version_info=VersionInfo(
                data_hash="hash_v2", version="1.0.1", is_latest=True, supersedes=metadata_v1.id
            ),
        )

        # Set content for version 2
        content_v2 = {
            "corpus_name": "version-test",
            "vocabulary_hash": "hash_v2",
            "trie_data": ["one", "two", "three", "four", "five"],
            "word_count": 5,
        }
        metadata_v2.content_inline = content_v2
        await metadata_v2.save()

        # Update first version to not be latest
        metadata_v1.version_info.is_latest = False
        metadata_v1.version_info.superseded_by = metadata_v2.id
        await metadata_v1.save()

        # Retrieve latest version
        latest = await TrieIndex.Metadata.find_one(
            {"resource_id": "version-test:trie", "version_info.is_latest": True}
        )

        assert latest is not None
        assert latest.version_info.version == "1.0.1"

        # Check content
        latest_content = await latest.get_content()
        assert latest_content is not None
        assert latest_content["word_count"] == 5

    async def test_trie_search_with_persistence(self, test_db: AsyncIOMotorDatabase):
        """Test TrieSearch with MongoDB persistence."""
        # Create and save trie index metadata
        vocabulary = ["persistent", "data", "test", "mongodb"]
        metadata = TrieIndex.Metadata(
            resource_id="search-persist-test:trie",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.TRIE,
            corpus_id=PydanticObjectId(),
            version_info=VersionInfo(data_hash="search_test_hash"),
        )

        # Create TrieIndex data structure
        index_data = {
            "corpus_id": str(metadata.corpus_id),
            "corpus_name": "search-persist-test",
            "vocabulary_hash": "test_hash",
            "trie_data": sorted(vocabulary),
            "word_frequencies": {word: 10 for word in vocabulary},
            "original_vocabulary": vocabulary,
            "normalized_to_original": {word: word for word in vocabulary},
            "word_count": len(vocabulary),
            "max_frequency": 10,
        }

        metadata.content_inline = index_data
        await metadata.save()

        # Retrieve and reconstruct TrieIndex
        retrieved_metadata = await TrieIndex.Metadata.get(metadata.id)
        assert retrieved_metadata is not None

        content = await retrieved_metadata.get_content()
        assert content is not None

        # Create TrieIndex from saved data
        index = TrieIndex(
            index_id=retrieved_metadata.id,
            corpus_id=PydanticObjectId(content["corpus_id"]),
            corpus_name=content["corpus_name"],
            vocabulary_hash=content["vocabulary_hash"],
            trie_data=content["trie_data"],
            word_frequencies=content["word_frequencies"],
            original_vocabulary=content["original_vocabulary"],
            normalized_to_original=content["normalized_to_original"],
            word_count=content["word_count"],
            max_frequency=content["max_frequency"],
        )

        # Create TrieSearch from reconstructed index
        trie = TrieSearch(index=index)

        # Test search functionality
        assert trie.search_exact("persistent") == "persistent"
        assert trie.search_exact("missing") is None

        results = trie.search_prefix("test")
        assert "test" in results
        assert len(results) == 1

    async def test_corpus_metadata_persistence(self, test_db: AsyncIOMotorDatabase):
        """Test Corpus.Metadata persistence with MongoDB."""
        # Create and save corpus metadata
        metadata = Corpus.Metadata(
            resource_id="corpus_metadata-test",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            corpus_name="metadata-test",
            language="en",
            version_info=VersionInfo(data_hash="corpus_test_hash"),
        )

        # Set corpus content
        corpus_content = {
            "corpus_name": "metadata-test",
            "language": "en",
            "vocabulary": ["meta", "data"],
            "original_vocabulary": ["meta", "data"],
            "unique_word_count": 2,
            "total_word_count": 2,
        }
        metadata.content_inline = corpus_content
        await metadata.save()

        # Retrieve metadata
        retrieved = await Corpus.Metadata.find_one({"resource_id": "corpus_metadata-test"})

        assert retrieved is not None
        assert retrieved.corpus_name == "metadata-test"
        assert retrieved.language.value == "en"

        # Check content
        content = await retrieved.get_content()
        assert content is not None
        assert content["vocabulary"] == ["meta", "data"]

    async def test_index_deduplication(self, test_db: AsyncIOMotorDatabase):
        """Test that identical indices are not duplicated."""
        # Create first metadata with specific content hash
        vocabulary = ["dedup", "test", "words"]
        content = {
            "corpus_name": "dedup-test",
            "vocabulary_hash": "fixed_hash",
            "trie_data": vocabulary,
            "word_count": len(vocabulary),
        }

        metadata1 = TrieIndex.Metadata(
            resource_id="dedup-test:trie",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.TRIE,
            corpus_id=PydanticObjectId(),
            version_info=VersionInfo(data_hash="dedup_test_hash"),
        )
        metadata1.content_inline = content
        await metadata1.save()

        # Try to find existing metadata with same resource_id
        existing = await TrieIndex.Metadata.find_one({"resource_id": "dedup-test:trie"})

        assert existing is not None
        assert existing.id == metadata1.id

        # Verify content is the same
        existing_content = await existing.get_content()
        assert existing_content is not None
        assert existing_content["vocabulary_hash"] == "fixed_hash"
        assert existing_content["word_count"] == len(vocabulary)
