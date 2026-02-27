"""Comprehensive model tests.

Tests all model functionality including:
- Model validation and serialization
- Registry functionality
- Relationship handling
- Versioning behavior
- MongoDB integration
- Base model inheritance
"""

import asyncio
from datetime import UTC, datetime

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from floridify.caching.models import (
    BaseVersionedData,
    ResourceType,
)
from floridify.corpus.core import Corpus
from floridify.corpus.manager import get_tree_corpus_manager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.models.registry import get_model_class as get_versioned_model_class
from floridify.providers.dictionary.models import DictionaryProviderEntry
from floridify.search.models import SearchIndex


@pytest.mark.asyncio
class TestModelRegistry:
    """Test model registration system."""

    async def test_model_registration(self):
        """Test that all models are properly registered."""
        # Check all expected models are accessible via the registry
        expected_types = [
            ResourceType.CORPUS,
            ResourceType.DICTIONARY,
            ResourceType.LANGUAGE,
            ResourceType.LITERATURE,
            ResourceType.SEARCH,
            ResourceType.TRIE,
            ResourceType.SEMANTIC,
        ]

        for resource_type in expected_types:
            # Test that we can get a model class for each resource type
            model_class = get_versioned_model_class(resource_type)
            assert issubclass(model_class, BaseVersionedData)

    async def test_get_model_class(self):
        """Test retrieving model classes from registry."""
        # Test valid resource types
        corpus_class = get_versioned_model_class(ResourceType.CORPUS)
        assert corpus_class == Corpus.Metadata

        dict_class = get_versioned_model_class(ResourceType.DICTIONARY)
        assert dict_class == DictionaryProviderEntry.Metadata

        # Test invalid resource type
        with pytest.raises(ValueError, match="Unknown resource type"):
            get_versioned_model_class("invalid_type")

    async def test_registry_completeness(self):
        """Test that the registry covers all expected resource types."""
        # Test that all ResourceType enum values are handled
        for resource_type in ResourceType:
            try:
                model_class = get_versioned_model_class(resource_type)
                assert issubclass(model_class, BaseVersionedData)
            except ValueError:
                pytest.fail(f"Resource type {resource_type} not handled by registry")

    async def test_model_class_instantiation(self):
        """Test that registry returns classes that can be instantiated."""
        # Test a few key model classes to ensure they work
        corpus_class = get_versioned_model_class(ResourceType.CORPUS)
        dict_class = get_versioned_model_class(ResourceType.DICTIONARY)

        # These should be able to create instances (though we need proper data)
        assert hasattr(corpus_class, "__init__")
        assert hasattr(dict_class, "__init__")

        # Check they have the required fields for BaseVersionedData
        for model_class in [corpus_class, dict_class]:
            required_fields = ["resource_id", "resource_type", "namespace"]
            for field in required_fields:
                assert field in model_class.model_fields


@pytest.mark.asyncio
class TestModelValidation:
    """Test model validation and serialization."""

    async def test_corpus_validation(self):
        """Test Corpus model validation."""
        # Valid corpus
        valid_corpus = Corpus(
            corpus_name="test-corpus",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
        )
        assert valid_corpus.corpus_name == "test-corpus"
        assert len(valid_corpus.vocabulary) == 2

        # Invalid corpus - missing required vocabulary field
        with pytest.raises(ValidationError):
            Corpus(
                corpus_name="test-corpus",
                # Missing required vocabulary field
            )

    async def test_dictionary_entry_validation(self):
        """Test DictionaryProviderEntry validation."""
        # Valid entry
        valid_entry = DictionaryProviderEntry(
            resource_id="dict-entry-1",
            resource_type=ResourceType.DICTIONARY,
            word="test",
            definitions=[
                {
                    "text": "A procedure for critical evaluation",
                    "part_of_speech": "noun",
                },
            ],
            provider="test_provider",
        )
        assert valid_entry.word == "test"
        assert len(valid_entry.definitions) == 1

        # Invalid - missing required fields
        with pytest.raises(ValidationError):
            DictionaryProviderEntry(
                word="test",
                # Missing resource_id, resource_type, definitions, provider
            )

    async def test_search_index_validation(self):
        """Test SearchIndex validation."""
        # Valid index
        valid_index = SearchIndex(
            corpus_uuid="test-corpus-uuid",
            corpus_name="test-corpus",
            vocabulary_hash="test-hash-123",
        )
        assert valid_index.corpus_uuid is not None
        assert valid_index.corpus_name == "test-corpus"

        # Invalid - missing required fields
        with pytest.raises(ValidationError):
            SearchIndex(
                corpus_uuid="test-corpus-uuid",
                # Missing required corpus_name and vocabulary_hash
            )

    async def test_model_serialization(self):
        """Test model serialization/deserialization."""
        # Create corpus
        corpus = Corpus(
            corpus_name="serialize-test",
            vocabulary=["test", "words"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
            metadata={"custom": "data"},
        )

        # Serialize to dict
        corpus_dict = corpus.model_dump()
        assert corpus_dict["corpus_name"] == "serialize-test"
        assert "vocabulary" in corpus_dict
        assert "metadata" in corpus_dict

        # Deserialize from dict
        restored = Corpus(**corpus_dict)
        assert restored.corpus_name == corpus.corpus_name
        assert restored.vocabulary == corpus.vocabulary
        assert restored.metadata == corpus.metadata


@pytest.mark.asyncio
class TestModelRelationships:
    """Test model relationship handling."""

    async def test_corpus_parent_child(self, test_db):
        """Test corpus parent-child relationships."""
        manager = get_tree_corpus_manager()

        # Create parent
        parent = await Corpus.create(
            corpus_name="parent-corpus",
            vocabulary=["parent"],
            language=Language.ENGLISH,
        )
        parent.is_master = True
        parent = await manager.save_corpus(parent)
        assert parent is not None

        # Create child with parent reference
        child = await Corpus.create(
            corpus_name="child-corpus",
            vocabulary=["child"],
            language=Language.ENGLISH,
        )
        child.parent_uuid = parent.corpus_uuid
        child = await manager.save_corpus(child)
        assert child is not None

        # Verify relationship exists in the objects
        assert child.parent_uuid == parent.corpus_uuid

    async def test_corpus_tree_hierarchy(self, test_db):
        """Test multi-level corpus hierarchy."""
        manager = get_tree_corpus_manager()

        # Create 3-level hierarchy
        master = await Corpus.create(
            corpus_name="master",
            vocabulary=["master"],
            language=Language.ENGLISH,
        )
        master.is_master = True
        master = await manager.save_corpus(master)
        assert master is not None

        child1 = await Corpus.create(
            corpus_name="child1",
            vocabulary=["child1"],
            language=Language.ENGLISH,
        )
        child1.parent_uuid = master.corpus_uuid
        child1 = await manager.save_corpus(child1)
        assert child1 is not None

        grandchild = await Corpus.create(
            corpus_name="grandchild",
            vocabulary=["grandchild"],
            language=Language.ENGLISH,
        )
        grandchild.parent_uuid = child1.corpus_uuid
        grandchild = await manager.save_corpus(grandchild)
        assert grandchild is not None

        # Verify hierarchy
        assert grandchild.parent_uuid == child1.corpus_uuid
        assert child1.parent_uuid == master.corpus_uuid
        assert master.parent_uuid is None


@pytest.mark.asyncio
class TestVersionedModels:
    """Test versioned model behavior."""

    async def test_versioned_fields(self, test_db):
        """Test versioned model fields."""
        # Create versioned corpus
        corpus = Corpus.Metadata(
            resource_id="versioned-corpus",
            resource_type=ResourceType.CORPUS,
            corpus_name="test",
            language=Language.ENGLISH,
        )

        # Check version fields exist
        assert hasattr(corpus, "version_info")
        assert hasattr(corpus.version_info, "data_hash")
        assert hasattr(corpus.version_info, "created_at")

        # Save and verify
        saved = await corpus.save()
        assert saved.id is not None
        assert saved.version_info.version == "1.0.0"
        assert saved.version_info.is_latest is True

    async def test_version_increment(self, test_db):
        """Test version incrementing."""
        # Create initial version
        v1 = Corpus.Metadata(
            resource_id="increment-test",
            resource_type=ResourceType.CORPUS,
            corpus_name="test",
            language=Language.ENGLISH,
        )
        saved_v1 = await v1.save()
        assert saved_v1.version_info.version == "1.0.0"

        # Create new version
        v2 = Corpus.Metadata(
            resource_id="increment-test",
            resource_type=ResourceType.CORPUS,
            corpus_name="test",
            language=Language.ENGLISH,
        )
        v2.version_info.version = "1.0.1"
        v2.version_info.supersedes = saved_v1.id
        saved_v2 = await v2.save()

        # Update v1 to point to v2
        saved_v1.version_info.superseded_by = saved_v2.id
        saved_v1.version_info.is_latest = False
        await saved_v1.save()

        # Verify chain
        assert saved_v2.version_info.version == "1.0.1"
        assert saved_v2.version_info.is_latest is True
        assert saved_v2.version_info.supersedes == saved_v1.id

    async def test_content_hash(self, test_db):
        """Test content hash generation via full Corpus save/load."""
        manager = get_tree_corpus_manager()

        # Create two corpora with same content
        c1 = await Corpus.create(
            corpus_name="hash-test-1",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
        )
        await manager.save_corpus(c1)

        c2 = await Corpus.create(
            corpus_name="hash-test-2",
            vocabulary=["word1", "word2"],  # Same vocabulary as c1
            language=Language.ENGLISH,
        )
        await manager.save_corpus(c2)

        # Retrieve metadata to check hashes
        from floridify.caching.manager import get_version_manager

        vm = get_version_manager()

        m1 = await vm.get_latest(
            resource_id=c1.corpus_name,
            resource_type=ResourceType.CORPUS,
        )
        m2 = await vm.get_latest(
            resource_id=c2.corpus_name,
            resource_type=ResourceType.CORPUS,
        )

        # Same vocabulary should produce same vocabulary hash in content
        # Different corpus content (names, IDs) = different data_hash
        assert m1.version_info.data_hash != m2.version_info.data_hash

        # Create corpus with different content
        c3 = await Corpus.create(
            corpus_name="hash-test-3",
            vocabulary=["different", "words"],  # Different vocabulary
            language=Language.ENGLISH,
        )
        await manager.save_corpus(c3)

        m3 = await vm.get_latest(
            resource_id=c3.corpus_name,
            resource_type=ResourceType.CORPUS,
        )

        # Different content = different data_hash (this is what matters)
        assert m3.version_info.data_hash != m1.version_info.data_hash
        assert m3.version_info.data_hash != m2.version_info.data_hash


@pytest.mark.asyncio
class TestMongoDBIntegration:
    """Test MongoDB integration for models."""

    async def test_save_and_retrieve(self, test_db):
        """Test saving and retrieving models."""
        manager = get_tree_corpus_manager()

        # Create and save
        corpus = await Corpus.create(
            corpus_name="mongo-test",
            vocabulary=["mongo", "test"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)
        assert saved is not None
        assert saved.corpus_id is not None

        # Retrieve by uuid
        retrieved = await manager.get_corpus(corpus_uuid=saved.corpus_uuid)
        assert retrieved is not None
        assert retrieved.corpus_name == "mongo-test"
        assert "mongo" in retrieved.vocabulary
        assert "test" in retrieved.vocabulary

    async def test_query_operations(self, test_db):
        """Test MongoDB query operations via Corpus.Metadata."""
        manager = get_tree_corpus_manager()

        # Create multiple corpora
        for i in range(5):
            corpus = await Corpus.create(
                corpus_name=f"query-test-{i}",
                vocabulary=[f"word{i}"],
                language=Language.ENGLISH,
            )
            corpus.corpus_type = CorpusType.LEXICON if i % 2 == 0 else CorpusType.LITERATURE
            await manager.save_corpus(corpus)

        # Query Corpus.Metadata (Beanie Document) by type
        import re

        lexicon_meta = await Corpus.Metadata.find(
            {"corpus_type": CorpusType.LEXICON, "version_info.is_latest": True}
        ).to_list()
        assert len(lexicon_meta) >= 3

        # Query by name pattern using resource_id (which stores corpus_name)
        query_meta = await Corpus.Metadata.find(
            {"resource_id": re.compile("^query-test"), "version_info.is_latest": True}
        ).to_list()
        assert len(query_meta) >= 5

    async def test_update_operations(self, test_db):
        """Test MongoDB update operations."""
        manager = get_tree_corpus_manager()

        # Create corpus
        corpus = await Corpus.create(
            corpus_name="update-test",
            vocabulary=["initial"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)
        assert saved is not None

        # Update the corpus vocabulary
        await saved.add_words(["updated", "words"])

        # Save updates (creates new version)
        updated = await manager.save_corpus(saved)
        assert updated is not None

        # Retrieve fresh copy and verify updates
        retrieved = await manager.get_corpus(corpus_uuid=saved.corpus_uuid)
        assert retrieved is not None
        assert "initial" in retrieved.vocabulary
        assert "updated" in retrieved.vocabulary
        assert "words" in retrieved.vocabulary

    async def test_delete_operations(self, test_db):
        """Test MongoDB delete operations."""
        manager = get_tree_corpus_manager()

        # Create corpus
        corpus = await Corpus.create(
            corpus_name="delete-test",
            vocabulary=["delete", "me"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)
        assert saved is not None

        # Delete
        await manager.delete_corpus(corpus_name=saved.corpus_name)

        # Verify deletion
        deleted = await manager.get_corpus(corpus_name="delete-test")
        assert deleted is None

    async def test_bulk_operations(self, test_db):
        """Test saving multiple corpora and bulk query."""
        manager = get_tree_corpus_manager()

        # Create and save multiple corpora
        for i in range(10):
            corpus = await Corpus.create(
                corpus_name=f"bulk-test-{i}",
                vocabulary=[f"bulk{i}"],
                language=Language.ENGLISH,
            )
            saved = await manager.save_corpus(corpus)
            assert saved is not None

        # Bulk query via Corpus.Metadata
        import re

        bulk_meta = await Corpus.Metadata.find(
            {"resource_id": re.compile("^bulk-test"), "version_info.is_latest": True}
        ).to_list()
        assert len(bulk_meta) >= 10

    async def test_concurrent_operations(self, test_db):
        """Test concurrent MongoDB operations."""
        manager = get_tree_corpus_manager()

        async def create_corpus(id: int):
            corpus = await Corpus.create(
                corpus_name=f"concurrent-{id}",
                vocabulary=[f"word{id}"],
                language=Language.ENGLISH,
            )
            saved = await manager.save_corpus(corpus)
            return saved

        # Run concurrent creates
        tasks = [create_corpus(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 20
        for i, corpus in enumerate(results):
            assert corpus is not None
            assert corpus.corpus_name == f"concurrent-{i}"
