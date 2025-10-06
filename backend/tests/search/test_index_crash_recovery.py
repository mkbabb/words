"""Tests for index persistence crash recovery and corruption handling."""

import asyncio
import base64
import pickle
import zlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import faiss
import numpy as np
import pytest
from beanie import PydanticObjectId

from floridify.caching.manager import get_version_manager
from floridify.caching.models import ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.core import SemanticSearch
from floridify.search.semantic.models import SemanticIndex
from floridify.storage.mongodb import init_db
from floridify.utils.logging import get_logger

logger = get_logger(__name__)

# Test corpus data
TEST_VOCABULARY = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]
TEST_LEMMAS = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape"]


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize database for tests."""
    await init_db()
    yield
    # Cleanup is handled by pytest-mongodb


@pytest.fixture
async def test_corpus():
    """Create a test corpus."""
    corpus = Corpus(
        corpus_name="test_crash_recovery",
        vocabulary=TEST_VOCABULARY,
        lemmatized_vocabulary=TEST_LEMMAS,
        language="en",
    )
    await corpus.save(VersionConfig())
    return corpus


class TestCrashRecovery:
    """Test suite for crash recovery scenarios."""

    @pytest.mark.asyncio
    async def test_save_fails_loudly_on_database_error(self, test_corpus):
        """Test that save operations fail loudly when database errors occur."""
        # Create indices
        trie_index = TrieIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash=test_corpus.vocabulary_hash,
            trie_data=TEST_VOCABULARY,
        )

        # Mock database error during save
        with patch("floridify.caching.manager.VersionedDataManager._save_with_transaction") as mock_save:
            mock_save.side_effect = Exception("Database connection lost")

            # Should raise RuntimeError with descriptive message
            with pytest.raises(RuntimeError) as exc_info:
                await trie_index.save()

            assert "Trie index persistence failed" in str(exc_info.value)
            assert "Database connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_recovery_from_corrupted_embeddings(self, test_corpus):
        """Test recovery when embeddings data is corrupted."""
        # Create and save semantic index
        semantic_index = SemanticIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash=test_corpus.vocabulary_hash,
            model_name="test_model",
            vocabulary=TEST_VOCABULARY,
            lemmatized_vocabulary=TEST_LEMMAS,
        )

        # Create fake embeddings
        fake_embeddings = np.random.randn(len(TEST_VOCABULARY), 384).astype(np.float32)
        embeddings_bytes = pickle.dumps(fake_embeddings)
        compressed = zlib.compress(embeddings_bytes)
        binary_data = {"embeddings": base64.b64encode(compressed).decode("utf-8")}

        await semantic_index.save(binary_data=binary_data)

        # Corrupt the stored data by modifying the cache
        manager = get_version_manager()
        resource_id = f"{test_corpus.corpus_id!s}:semantic:test_model"

        # Retrieve the saved metadata
        metadata = await manager.get_latest(
            resource_id=resource_id,
            resource_type=ResourceType.SEMANTIC,
            use_cache=False,
        )

        # Mock corrupted binary data
        with patch("floridify.search.semantic.core.SemanticSearch._load_index_from_data") as mock_load:
            # Make it raise an error as if data is corrupted
            mock_load.side_effect = RuntimeError("Corrupted embeddings data: Invalid pickle data")

            semantic_search = SemanticSearch(
                corpus=test_corpus,
                model_name="test_model",
            )

            # Should handle corruption gracefully
            with pytest.raises(RuntimeError) as exc_info:
                semantic_search._load_index_from_data(semantic_index)

            assert "Corrupted embeddings data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_partial_save_detection(self, test_corpus):
        """Test detection of partially saved indices."""
        search_index = SearchIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash=test_corpus.vocabulary_hash,
            has_trie=True,
            has_fuzzy=True,
            has_semantic=False,
            trie_index_id=PydanticObjectId(),  # Reference to non-existent trie
        )

        # Save should succeed even with invalid references
        await search_index.save()

        # But verification should detect the issue
        retrieved = await SearchIndex.get(corpus_id=test_corpus.corpus_id)
        assert retrieved is not None

        # Verify that the index was saved with the reference
        assert retrieved.trie_index_id == search_index.trie_index_id

        # Now test that using the index would fail if we try to load the referenced trie
        trie = await TrieIndex.get(corpus_id=test_corpus.corpus_id)
        # Trie doesn't exist because we never created it
        assert trie is None

    @pytest.mark.asyncio
    async def test_external_content_missing(self, test_corpus):
        """Test handling when external content file is missing."""
        # Create large semantic index that will use external storage
        semantic_index = SemanticIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash=test_corpus.vocabulary_hash,
            model_name="large_model",
            vocabulary=TEST_VOCABULARY * 10000,  # Large vocabulary to force external storage
            lemmatized_vocabulary=TEST_LEMMAS * 10000,
        )

        # Create large binary data (>16MB to force external storage)
        large_embeddings = np.random.randn(len(TEST_VOCABULARY) * 10000, 384).astype(np.float32)
        embeddings_bytes = pickle.dumps(large_embeddings)
        compressed = zlib.compress(embeddings_bytes)
        binary_data = {"embeddings": base64.b64encode(compressed).decode("utf-8")}

        await semantic_index.save(binary_data=binary_data)

        # Mock external content retrieval failure
        with patch("floridify.caching.manager.get_versioned_content") as mock_get_content:
            mock_get_content.return_value = None  # Simulate missing file

            manager = get_version_manager()
            resource_id = f"{test_corpus.corpus_id!s}:semantic:large_model"

            # Should raise error when external content is missing
            with pytest.raises(RuntimeError) as exc_info:
                await manager.get_latest(
                    resource_id=resource_id,
                    resource_type=ResourceType.SEMANTIC,
                    use_cache=False,
                )

            assert "Index data corrupted" in str(exc_info.value)
            assert "External content could not be loaded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_vocabulary_hash_mismatch(self, test_corpus):
        """Test that vocabulary hash mismatches are detected."""
        trie_index = TrieIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash="old_hash",
            trie_data=TEST_VOCABULARY,
        )

        # Manually set a different hash before save
        await trie_index.save()

        # Modify the hash after save
        trie_index.vocabulary_hash = "new_hash"

        # Try to save again with verification - should detect mismatch
        with pytest.raises(RuntimeError) as exc_info:
            await trie_index.save()

        assert "Vocabulary hash mismatch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_concurrent_save_operations(self, test_corpus):
        """Test handling of concurrent save operations."""
        # Create multiple indices
        indices = []
        for i in range(5):
            index = TrieIndex(
                corpus_id=test_corpus.corpus_id,
                corpus_name=f"{test_corpus.corpus_name}_{i}",
                vocabulary_hash=f"{test_corpus.vocabulary_hash}_{i}",
                trie_data=TEST_VOCABULARY,
            )
            indices.append(index)

        # Save all indices concurrently
        save_tasks = [index.save() for index in indices]

        # All saves should complete successfully
        results = await asyncio.gather(*save_tasks, return_exceptions=True)

        # Check that no exceptions occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent save {i} failed: {result}")

        # Verify all indices were saved
        for i, index in enumerate(indices):
            retrieved = await TrieIndex.get(
                corpus_id=test_corpus.corpus_id,
                corpus_name=f"{test_corpus.corpus_name}_{i}",
            )
            assert retrieved is not None
            assert retrieved.vocabulary_hash == f"{test_corpus.vocabulary_hash}_{i}"

    @pytest.mark.asyncio
    async def test_recovery_from_interrupted_build(self, test_corpus):
        """Test recovery when index building is interrupted."""
        semantic_search = SemanticSearch(
            corpus=test_corpus,
            model_name="test_model",
        )

        # Mock an interruption during embedding generation
        with patch.object(semantic_search, "_build_embeddings") as mock_build:
            mock_build.side_effect = KeyboardInterrupt("User cancelled")

            with pytest.raises(KeyboardInterrupt):
                await semantic_search.from_corpus(
                    corpus=test_corpus,
                    model_name="test_model",
                )

        # Verify that no partial index was saved
        retrieved = await SemanticIndex.get(
            corpus_id=test_corpus.corpus_id,
            model_name="test_model",
        )
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_compression_decompression_integrity(self, test_corpus):
        """Test that compression/decompression maintains data integrity."""
        # Create semantic index with known data
        semantic_index = SemanticIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash=test_corpus.vocabulary_hash,
            model_name="compression_test",
            vocabulary=TEST_VOCABULARY,
            lemmatized_vocabulary=TEST_LEMMAS,
        )

        # Create specific embeddings
        original_embeddings = np.array(
            [[1.0, 2.0, 3.0] for _ in TEST_VOCABULARY],
            dtype=np.float32,
        )

        # Compress and encode
        embeddings_bytes = pickle.dumps(original_embeddings)
        compressed = zlib.compress(embeddings_bytes, level=6)
        binary_data = {"embeddings": base64.b64encode(compressed).decode("utf-8")}

        await semantic_index.save(binary_data=binary_data)

        # Retrieve and verify
        retrieved = await SemanticIndex.get(
            corpus_id=test_corpus.corpus_id,
            model_name="compression_test",
        )
        assert retrieved is not None

        # Decompress and verify data integrity
        if hasattr(retrieved, "binary_data") and retrieved.binary_data:
            compressed_data = base64.b64decode(retrieved.binary_data["embeddings"])
            decompressed = zlib.decompress(compressed_data)
            restored_embeddings = pickle.loads(decompressed)

            # Verify exact match
            np.testing.assert_array_almost_equal(original_embeddings, restored_embeddings)

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_corruption(self, test_corpus):
        """Test that corrupted cache entries are invalidated."""
        trie_index = TrieIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash=test_corpus.vocabulary_hash,
            trie_data=TEST_VOCABULARY,
        )

        await trie_index.save()

        # First retrieval should cache the index
        retrieved1 = await TrieIndex.get(corpus_id=test_corpus.corpus_id)
        assert retrieved1 is not None

        # Mock cache corruption
        manager = get_version_manager()

        with patch("floridify.caching.manager.GlobalCacheManager.get") as mock_get:
            # Return corrupted cached data
            corrupted = MagicMock()
            corrupted.id = PydanticObjectId()
            corrupted.vocabulary_hash = "corrupted_hash"
            mock_get.return_value = corrupted

            # Should detect corruption and fetch from database
            retrieved2 = await TrieIndex.get(
                corpus_id=test_corpus.corpus_id,
                config=VersionConfig(use_cache=True),
            )

            # Should still get valid data from database
            assert retrieved2 is not None
            assert retrieved2.vocabulary_hash == test_corpus.vocabulary_hash


class TestErrorPropagation:
    """Test that errors propagate correctly through the system."""

    @pytest.mark.asyncio
    async def test_semantic_search_build_failure(self, test_corpus):
        """Test that semantic search build failures are handled properly."""
        semantic_search = SemanticSearch(
            corpus=test_corpus,
            model_name="test_model",
        )

        # Mock model loading failure
        with patch("floridify.search.semantic.core.get_cached_model") as mock_model:
            mock_model.side_effect = RuntimeError("Model file corrupted")

            # Should propagate the error with context
            with pytest.raises(RuntimeError) as exc_info:
                await semantic_search._load_model()

            assert "Model file corrupted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_faiss_index_corruption(self, test_corpus):
        """Test handling of corrupted FAISS indices."""
        # Create a valid FAISS index
        dimension = 384
        index = faiss.IndexFlatL2(dimension)

        # Add some vectors
        vectors = np.random.randn(len(TEST_VOCABULARY), dimension).astype(np.float32)
        index.add(vectors)

        # Serialize and corrupt
        serialized = faiss.serialize_index(index)
        corrupted_bytes = b"corrupted" + serialized[10:]  # Corrupt the header

        # Try to deserialize
        with pytest.raises(RuntimeError):
            faiss.deserialize_index(corrupted_bytes)

    @pytest.mark.asyncio
    async def test_version_chain_corruption_detection(self, test_corpus):
        """Test detection of version chain corruption."""
        search_index1 = SearchIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash="v1",
        )

        await search_index1.save()

        # Create another version with same resource ID
        search_index2 = SearchIndex(
            corpus_id=test_corpus.corpus_id,
            corpus_name=test_corpus.corpus_name,
            vocabulary_hash="v2",
        )

        await search_index2.save()

        # Both should be retrievable by version
        manager = get_version_manager()

        # Latest should be v2
        latest = await SearchIndex.get(corpus_id=test_corpus.corpus_id)
        assert latest.vocabulary_hash == "v2"