"""Comprehensive corpus tests with MongoDB and versioning.

Tests the complete corpus functionality including:
- MongoDB persistence
- Version management
- Tree structure operations
- Vocabulary aggregation
- Concurrent updates
- Cache invalidation
"""

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from beanie import PydanticObjectId

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import CacheNamespace, ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager


@pytest.mark.asyncio
class TestCorpusMongoDBIntegration:
    """Test corpus MongoDB persistence and operations."""

    @pytest_asyncio.fixture
    async def corpus_manager(self, test_db):
        """Create corpus manager with test database."""
        manager = TreeCorpusManager()
        return manager

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_corpus_persistence(self, test_db, corpus_manager):
        """Test saving and loading corpus from MongoDB."""
        # Create corpus
        corpus = Corpus(
            corpus_name="test-corpus",
            language="en",
            vocabulary=["apple", "banana", "cherry"],
            original_vocabulary=["Apple", "Banana", "Cherry"],
            unique_word_count=3,
            total_word_count=3,
            metadata={"source": "test", "created": datetime.now(UTC).isoformat()},
        )

        # Save to MongoDB
        saved = await corpus_manager.save_corpus(corpus)
        assert saved is not None
        assert saved.corpus_id is not None
        assert isinstance(saved.corpus_id, PydanticObjectId)

        # Load from MongoDB
        loaded = await corpus_manager.get_corpus(corpus_id=saved.corpus_id)
        assert loaded is not None
        assert loaded.corpus_name == corpus.corpus_name
        assert loaded.vocabulary == corpus.vocabulary
        assert loaded.metadata == corpus.metadata

    async def test_corpus_versioning(self, test_db, versioned_manager):
        """Test corpus version management."""
        resource_id = "corpus-v-test"

        # Create v1
        v1_content = {
            "corpus_name": "version-test",
            "vocabulary": ["word1", "word2"],
            "version": "1.0.0",
        }

        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=v1_content,
            config=VersionConfig(version="1.0.0"),
        )

        assert v1.version_info.version == "1.0.0"
        assert v1.version_info.is_latest is True

        # Create v2 with updated vocabulary
        v2_content = {
            "corpus_name": "version-test",
            "vocabulary": ["word1", "word2", "word3"],
            "version": "2.0.0",
        }

        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content=v2_content,
            config=VersionConfig(version="2.0.0"),
        )

        assert v2.version_info.version == "2.0.0"
        assert v2.version_info.is_latest is True
        assert v2.version_info.supersedes == v1.id

        # Verify v1 is no longer latest
        v1_updated = await versioned_manager.get_by_version(
            resource_id, "1.0.0", ResourceType.CORPUS
        )
        assert v1_updated.version_info.is_latest is False
        assert v1_updated.version_info.superseded_by == v2.id

    async def test_corpus_tree_structure(self, test_db, corpus_manager):
        """Test hierarchical corpus tree operations."""
        # Create parent corpus
        parent = Corpus(
            corpus_name="parent-corpus",
            language="en",
            vocabulary=["parent1", "parent2"],
            original_vocabulary=["Parent1", "Parent2"],
            unique_word_count=2,
            total_word_count=2,
        )
        saved_parent = await corpus_manager.save_corpus(parent)

        # Create child corpora
        child1 = Corpus(
            corpus_name="child-corpus-1",
            language="en",
            vocabulary=["child1", "child2"],
            original_vocabulary=["Child1", "Child2"],
            unique_word_count=2,
            total_word_count=2,
            parent_corpus_id=saved_parent.corpus_id,
        )

        child2 = Corpus(
            corpus_name="child-corpus-2",
            language="en",
            vocabulary=["child3", "child4"],
            original_vocabulary=["Child3", "Child4"],
            unique_word_count=2,
            total_word_count=2,
            parent_corpus_id=saved_parent.corpus_id,
        )

        saved_child1 = await corpus_manager.save_corpus(child1)
        saved_child2 = await corpus_manager.save_corpus(child2)

        # Test tree navigation
        children = await corpus_manager.aggregate_vocabularies(saved_parent.corpus_id)
        assert children is not None

        # Verify parent-child relationships
        assert saved_child1.parent_corpus_id == saved_parent.corpus_id
        assert saved_child2.parent_corpus_id == saved_parent.corpus_id

    async def test_vocabulary_aggregation(self, test_db, corpus_manager):
        """Test vocabulary aggregation across corpus tree."""
        # Create corpus hierarchy
        root = await corpus_manager.save_corpus(
            Corpus(
                corpus_name="root",
                language="en",
                vocabulary=["root1", "root2"],
                original_vocabulary=["Root1", "Root2"],
                unique_word_count=2,
                total_word_count=2,
            )
        )

        branch = await corpus_manager.save_corpus(
            Corpus(
                corpus_name="branch",
                language="en",
                vocabulary=["branch1", "branch2"],
                original_vocabulary=["Branch1", "Branch2"],
                unique_word_count=2,
                total_word_count=2,
                parent_corpus_id=root.corpus_id,
            )
        )

        leaf = await corpus_manager.save_corpus(
            Corpus(
                corpus_name="leaf",
                language="en",
                vocabulary=["leaf1", "leaf2"],
                original_vocabulary=["Leaf1", "Leaf2"],
                unique_word_count=2,
                total_word_count=2,
                parent_corpus_id=branch.corpus_id,
            )
        )

        # Aggregate vocabulary from leaf up
        aggregated = await corpus_manager.aggregate_vocabularies(leaf.corpus_id)

        # Should include all words from leaf, branch, and root
        expected_words = {"leaf1", "leaf2", "branch1", "branch2", "root1", "root2"}
        assert set(aggregated) == expected_words

    async def test_concurrent_corpus_updates(self, test_db, corpus_manager):
        """Test concurrent updates to corpus."""
        # Create initial corpus
        corpus = await corpus_manager.save_corpus(
            Corpus(
                corpus_name="concurrent-test",
                language="en",
                vocabulary=["initial"],
                original_vocabulary=["Initial"],
                unique_word_count=1,
                total_word_count=1,
            )
        )

        async def update_corpus(word: str):
            """Update corpus with new word."""
            loaded = await corpus_manager.get_corpus(corpus_id=corpus.corpus_id)
            loaded.vocabulary.append(word)
            loaded.unique_word_count += 1
            loaded.total_word_count += 1
            return await corpus_manager.save_corpus(loaded)

        # Concurrent updates
        words = [f"word{i}" for i in range(10)]
        tasks = [update_corpus(word) for word in words]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some updates may conflict, but at least one should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0

        # Final corpus should have at least the initial word
        final = await corpus_manager.get_corpus(corpus_id=corpus.corpus_id)
        assert "initial" in final.vocabulary

    async def test_corpus_deletion_cascade(self, test_db, corpus_manager):
        """Test cascading deletion of corpus tree."""
        # Create tree
        parent = await corpus_manager.save_corpus(
            Corpus(
                corpus_name="delete-parent",
                language="en",
                vocabulary=["parent"],
                original_vocabulary=["Parent"],
                unique_word_count=1,
                total_word_count=1,
            )
        )

        child = await corpus_manager.save_corpus(
            Corpus(
                corpus_name="delete-child",
                language="en",
                vocabulary=["child"],
                original_vocabulary=["Child"],
                unique_word_count=1,
                total_word_count=1,
                parent_corpus_id=parent.corpus_id,
            )
        )

        # Delete parent
        await corpus_manager.delete_corpus(corpus_id=parent.corpus_id)

        # Both should be gone
        parent_check = await corpus_manager.get_corpus(corpus_id=parent.corpus_id)
        child_check = await corpus_manager.get_corpus(corpus_id=child.corpus_id)

        assert parent_check is None
        assert child_check is None

    async def test_corpus_metadata_preservation(self, test_db, versioned_manager):
        """Test that metadata is preserved across versions."""
        resource_id = "metadata-test"

        # Custom metadata
        metadata = {
            "author": "test-user",
            "tags": ["test", "corpus"],
            "created_date": datetime.now(UTC).isoformat(),
            "custom_field": {"nested": "value"},
        }

        # Save with metadata
        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": ["word1"]},
            metadata=metadata,
        )

        # Update content but preserve metadata
        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": ["word1", "word2"]},
            metadata=metadata,
            config=VersionConfig(increment_version=True),
        )

        # Metadata should be preserved
        assert v2.metadata == metadata
        assert v2.metadata["author"] == "test-user"
        assert v2.metadata["tags"] == ["test", "corpus"]

    async def test_corpus_search_by_name(self, test_db, corpus_manager):
        """Test searching corpus by name."""
        # Create multiple corpora
        corpora_names = ["alpha-corpus", "beta-corpus", "gamma-corpus"]

        for name in corpora_names:
            await corpus_manager.save_corpus(
                Corpus(
                    corpus_name=name,
                    language="en",
                    vocabulary=[f"{name}-word"],
                    original_vocabulary=[f"{name}-Word"],
                    unique_word_count=1,
                    total_word_count=1,
                )
            )

        # Search by name
        result = await corpus_manager.get_corpus(corpus_name="beta-corpus")
        assert result is not None
        assert result.corpus_name == "beta-corpus"

    async def test_corpus_statistics(self, test_db, corpus_manager):
        """Test corpus statistics calculation."""
        # Create corpus with word frequencies
        corpus = Corpus(
            corpus_name="stats-corpus",
            language="en",
            vocabulary=["apple", "banana", "apple", "cherry", "apple"],
            original_vocabulary=["Apple", "Banana", "Apple", "Cherry", "Apple"],
            unique_word_count=3,
            total_word_count=5,
            word_frequencies={"apple": 3, "banana": 1, "cherry": 1},
        )

        saved = await corpus_manager.save_corpus(corpus)

        # Get saved corpus statistics
        stats = {
            "unique_words": saved.unique_word_count,
            "total_words": saved.total_word_count,
            "most_common": max(saved.word_frequencies, key=saved.word_frequencies.get)
            if saved.word_frequencies
            else None,
            "frequency_distribution": saved.word_frequencies or {},
        }

        assert stats["unique_words"] == 3
        assert stats["total_words"] == 5
        assert stats["most_common"] == "apple"
        assert stats["frequency_distribution"]["apple"] == 3


@pytest.mark.asyncio
class TestCorpusVersionChaining:
    """Test corpus version chain management."""

    @pytest_asyncio.fixture
    async def versioned_manager(self):
        """Create versioned data manager."""
        return VersionedDataManager()

    async def test_version_chain_integrity(self, test_db, versioned_manager):
        """Test that version chains maintain integrity."""
        resource_id = "chain-test"
        versions = []

        # Create chain of 5 versions
        for i in range(5):
            version = await versioned_manager.save(
                resource_id=resource_id,
                resource_type=ResourceType.CORPUS,
                namespace=CacheNamespace.CORPUS,
                content={"vocabulary": [f"word{j}" for j in range(i + 1)]},
                config=VersionConfig(version=f"{i + 1}.0.0"),
            )
            versions.append(version)

        # Verify chain integrity
        # The last version should be latest
        latest = await versioned_manager.get_latest(resource_id, ResourceType.CORPUS)
        assert latest.version_info.version == "5.0.0"
        assert latest.version_info.is_latest is True

    async def test_version_rollback(self, test_db, versioned_manager):
        """Test rolling back to previous version."""
        resource_id = "rollback-test"

        # Create versions
        v1 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": ["original"]},
            config=VersionConfig(version="1.0.0"),
        )

        v2 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": ["modified"]},
            config=VersionConfig(version="2.0.0"),
        )

        # Create v3 with v1 content (manual rollback)
        v3 = await versioned_manager.save(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            content={"vocabulary": ["original"]},  # Same as v1
            config=VersionConfig(version="3.0.0"),
            metadata={"rollback_from": "2.0.0"},
        )

        assert v3.version_info.version == "3.0.0"
        assert v3.content == v1.content  # Content from v1
        assert v3.metadata.get("rollback_from") == "2.0.0"
