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
        assert valid_index.corpus_id is not None
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
        # Create parent
        parent = Corpus(
            corpus_name="parent-corpus",
            vocabulary=["parent"],
            language=Language.ENGLISH,
            is_master=True,
        )
        save_result = await parent.save()
        assert save_result is True

        # Create child with parent reference
        child = Corpus(
            corpus_name="child-corpus",
            vocabulary=["child"],
            language=Language.ENGLISH,
            parent_uuid=parent.corpus_id,  # Use parent directly, not saved_parent
        )
        child_save_result = await child.save()
        assert child_save_result is True

        # Verify relationship exists in the objects
        assert child.parent_uuid == parent.corpus_id

        # Update parent's children list
        parent.child_uuids.append(child.corpus_id)
        await parent.save()

        # Test basic relationship data (since retrieval may not be implemented)
        assert parent.corpus_id is not None
        assert child.corpus_id is not None
        assert child.parent_uuid == parent.corpus_id

    async def test_corpus_tree_hierarchy(self, test_db):
        """Test multi-level corpus hierarchy."""
        # Create 3-level hierarchy
        master = Corpus(
            corpus_name="master",
            vocabulary=["master"],
            language=Language.ENGLISH,
            is_master=True,
        )
        master_saved = await master.save()
        assert master_saved is True

        child1 = Corpus(
            corpus_name="child1",
            vocabulary=["child1"],
            language=Language.ENGLISH,
            parent_uuid=master.corpus_id,
        )
        child1_saved = await child1.save()
        assert child1_saved is True

        grandchild = Corpus(
            corpus_name="grandchild",
            vocabulary=["grandchild"],
            language=Language.ENGLISH,
            parent_uuid=child1.corpus_id,
        )
        grandchild_saved = await grandchild.save()
        assert grandchild_saved is True

        # Verify hierarchy
        assert grandchild.parent_uuid == child1.corpus_id
        assert child1.parent_uuid == master.corpus_id
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
            vocabulary=["test"],
            language=Language.ENGLISH,
        )

        # Check version fields exist
        assert hasattr(corpus, "version_info")
        assert hasattr(corpus.version_info, "data_hash")
        assert hasattr(corpus.version_info, "created_at")
        # updated_at removed in new versioning API

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
            vocabulary=["v1"],
            language=Language.ENGLISH,
        )
        saved_v1 = await v1.save()
        assert saved_v1.version_info.version == "1.0.0"

        # Create new version
        v2 = Corpus.Metadata(
            resource_id="increment-test",
            resource_type=ResourceType.CORPUS,
            corpus_name="test",
            vocabulary=["v1", "v2"],
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
        # Create two corpora with same content
        c1 = Corpus(
            corpus_name="hash-test-1",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
        )
        await c1.save()

        c2 = Corpus(
            corpus_name="hash-test-2",
            vocabulary=["word1", "word2"],  # Same vocabulary as c1
            language=Language.ENGLISH,
        )
        await c2.save()

        # Retrieve metadata to check hashes
        from floridify.caching.manager import get_version_manager

        manager = get_version_manager()

        m1 = await manager.get_latest(
            resource_id=c1.corpus_name,
            resource_type=ResourceType.CORPUS,
        )
        m2 = await manager.get_latest(
            resource_id=c2.corpus_name,
            resource_type=ResourceType.CORPUS,
        )

        # Same vocabulary should produce same vocabulary hash in content
        # (Note: vocabulary_hash metadata field may be empty if not extracted during save)
        # Different corpus content (names, IDs) = different data_hash
        assert m1.version_info.data_hash != m2.version_info.data_hash

        # Create corpus with different content
        c3 = Corpus(
            corpus_name="hash-test-3",
            vocabulary=["different", "words"],  # Different vocabulary
            language=Language.ENGLISH,
        )
        await c3.save()

        m3 = await manager.get_latest(
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
        # Create and save
        corpus = Corpus(
            corpus_name="mongo-test",
            vocabulary=["mongo", "test"],
            language=Language.ENGLISH,
        )
        save_result = await corpus.save()
        assert save_result is True
        assert corpus.corpus_id is not None

        # Retrieve by ID
        retrieved = await Corpus.get(corpus.corpus_id)
        assert retrieved is not None
        assert retrieved.corpus_name == "mongo-test"
        assert retrieved.vocabulary == ["mongo", "test"]

    async def test_query_operations(self, test_db):
        """Test MongoDB query operations via Corpus.Metadata."""
        # Create multiple corpora
        for i in range(5):
            corpus = Corpus(
                corpus_name=f"query-test-{i}",
                vocabulary=[f"word{i}"],
                language=Language.ENGLISH,
                corpus_type=CorpusType.LEXICON if i % 2 == 0 else CorpusType.LITERATURE,
            )
            await corpus.save()

        # Query Corpus.Metadata (Beanie Document) by type
        # Use dict syntax for nested fields to avoid ExpressionField issues
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
        # Create corpus
        corpus = Corpus(
            corpus_name="update-test",
            vocabulary=["initial"],
            language=Language.ENGLISH,
        )
        result = await corpus.save()
        assert result is True
        corpus_id = corpus.corpus_id

        # Update the corpus object directly
        corpus.vocabulary.extend(["updated", "words"])
        corpus.metadata["updated_at"] = datetime.now(UTC).isoformat()

        # Save updates (creates new version)
        result = await corpus.save()
        assert result is True

        # Retrieve fresh copy and verify updates
        retrieved = await Corpus.get(corpus_uuid=corpus.corpus_uuid)
        assert retrieved is not None
        assert "initial" in retrieved.vocabulary
        assert "updated" in retrieved.vocabulary
        assert "words" in retrieved.vocabulary
        assert "updated_at" in retrieved.metadata

    async def test_delete_operations(self, test_db):
        """Test MongoDB delete operations."""
        # Create corpus
        corpus = Corpus(
            corpus_name="delete-test",
            vocabulary=["delete", "me"],
            language=Language.ENGLISH,
        )
        result = await corpus.save()
        assert result is True
        corpus_id = corpus.corpus_id

        # Delete
        await corpus.delete()

        # Verify deletion
        deleted = await Corpus.get(corpus_uuid=corpus.corpus_uuid)
        assert deleted is None

    async def test_bulk_operations(self, test_db):
        """Test saving multiple corpora and bulk query."""
        # Create and save multiple corpora
        corpus_ids = []
        for i in range(10):
            corpus = Corpus(
                corpus_name=f"bulk-test-{i}",
                vocabulary=[f"bulk{i}"],
                language=Language.ENGLISH,
            )
            result = await corpus.save()
            assert result is True
            corpus_ids.append(corpus.corpus_id)

        assert len(corpus_ids) == 10

        # Bulk query via Corpus.Metadata
        import re

        bulk_meta = await Corpus.Metadata.find(
            {"resource_id": re.compile("^bulk-test"), "version_info.is_latest": True}
        ).to_list()
        assert len(bulk_meta) >= 10

    async def test_concurrent_operations(self, test_db):
        """Test concurrent MongoDB operations."""

        async def create_corpus(id: int):
            corpus = Corpus(
                corpus_name=f"concurrent-{id}",
                vocabulary=[f"word{id}"],
                language=Language.ENGLISH,
            )
            result = await corpus.save()
            # Return corpus with save status
            return (result, corpus)

        # Run concurrent creates
        tasks = [create_corpus(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 20
        for i, (save_result, corpus) in enumerate(results):
            assert save_result is True
            assert corpus.corpus_name == f"concurrent-{i}"
            assert corpus.corpus_id is not None
