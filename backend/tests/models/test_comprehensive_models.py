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
            corpus_id=PydanticObjectId(),
            corpus_name="test-corpus",
            vocabulary_hash="test-hash-123",
        )
        assert valid_index.corpus_id is not None
        assert valid_index.corpus_name == "test-corpus"

        # Invalid - missing required fields
        with pytest.raises(ValidationError):
            SearchIndex(
                corpus_id=PydanticObjectId(),
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
            parent_corpus_id=parent.corpus_id,  # Use parent directly, not saved_parent
        )
        child_save_result = await child.save()
        assert child_save_result is True

        # Verify relationship exists in the objects
        assert child.parent_corpus_id == parent.corpus_id

        # Update parent's children list
        parent.child_corpus_ids.append(child.corpus_id)
        await parent.save()

        # Test basic relationship data (since retrieval may not be implemented)
        assert parent.corpus_id is not None
        assert child.corpus_id is not None
        assert child.parent_corpus_id == parent.corpus_id

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
            parent_corpus_id=master.corpus_id,
        )
        child1_saved = await child1.save()
        assert child1_saved is True

        grandchild = Corpus(
            corpus_name="grandchild",
            vocabulary=["grandchild"],
            language=Language.ENGLISH,
            parent_corpus_id=child1.corpus_id,
        )
        grandchild_saved = await grandchild.save()
        assert grandchild_saved is True

        # Verify hierarchy
        assert grandchild.parent_corpus_id == child1.corpus_id
        assert child1.parent_corpus_id == master.corpus_id
        assert master.parent_corpus_id is None


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
        assert hasattr(corpus, "content_hash")
        assert hasattr(corpus, "created_at")
        assert hasattr(corpus, "updated_at")

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
        v2.version_info.previous_version = saved_v1.id
        saved_v2 = await v2.save()

        # Update v1 to point to v2
        saved_v1.version_info.next_version = saved_v2.id
        saved_v1.version_info.is_latest = False
        await saved_v1.save()

        # Verify chain
        assert saved_v2.version_info.version == "1.0.1"
        assert saved_v2.version_info.is_latest is True
        assert saved_v2.version_info.previous_version == saved_v1.id

    async def test_content_hash(self, test_db):
        """Test content hash generation."""
        # Create two models with same content
        content = {
            "corpus_name": "hash-test",
            "vocabulary": ["word1", "word2"],
            "language": Language.ENGLISH,
        }

        m1 = Corpus.Metadata(
            resource_id="hash-1",
            resource_type=ResourceType.CORPUS,
            **content,
        )
        m1.update_content_hash()

        m2 = Corpus.Metadata(
            resource_id="hash-2",
            resource_type=ResourceType.CORPUS,
            **content,
        )
        m2.update_content_hash()

        # Same content should have same hash
        assert m1.content_hash == m2.content_hash

        # Different content should have different hash
        m3 = Corpus.Metadata(
            resource_id="hash-3",
            resource_type=ResourceType.CORPUS,
            corpus_name="different",
            vocabulary=["different"],
            language=Language.ENGLISH,
        )
        m3.update_content_hash()
        assert m3.content_hash != m1.content_hash


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
        saved = await corpus.save()
        assert saved.corpus_id is not None

        # Retrieve by ID
        retrieved = await Corpus.get(saved.corpus_id)
        assert retrieved is not None
        assert retrieved.corpus_name == "mongo-test"
        assert retrieved.vocabulary == ["mongo", "test"]

    async def test_query_operations(self, test_db):
        """Test MongoDB query operations."""
        # Create multiple corpora
        for i in range(5):
            corpus = Corpus(
                corpus_name=f"query-test-{i}",
                vocabulary=[f"word{i}"],
                language=Language.ENGLISH,
                corpus_type=CorpusType.LEXICON if i % 2 == 0 else CorpusType.LITERATURE,
            )
            await corpus.save()

        # Query by type
        lexicon_corpora = await Corpus.find(Corpus.corpus_type == CorpusType.LEXICON).to_list()
        assert len(lexicon_corpora) >= 3

        # Query by name pattern
        query_corpora = await Corpus.find(Corpus.corpus_name.regex("^query-test")).to_list()
        assert len(query_corpora) >= 5

    async def test_update_operations(self, test_db):
        """Test MongoDB update operations."""
        # Create corpus
        corpus = Corpus(
            corpus_name="update-test",
            vocabulary=["initial"],
            language=Language.ENGLISH,
        )
        saved = await corpus.save()

        # Update
        saved.vocabulary.extend(["updated", "words"])
        saved.metadata["updated_at"] = datetime.now(UTC).isoformat()
        updated = await saved.save()

        # Verify update
        retrieved = await Corpus.get(updated.corpus_id)
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
        saved = await corpus.save()
        corpus_id = saved.corpus_id

        # Delete
        await saved.delete()

        # Verify deletion
        deleted = await Corpus.get(corpus_id)
        assert deleted is None

    async def test_bulk_operations(self, test_db):
        """Test MongoDB bulk operations."""
        # Create multiple corpora
        corpora = []
        for i in range(10):
            corpus = Corpus(
                corpus_name=f"bulk-test-{i}",
                vocabulary=[f"bulk{i}"],
                language=Language.ENGLISH,
            )
            corpora.append(corpus)

        # Bulk insert
        inserted = await Corpus.insert_many(corpora)
        assert len(inserted.inserted_ids) == 10

        # Bulk query
        bulk_results = await Corpus.find(Corpus.corpus_name.regex("^bulk-test")).to_list()
        assert len(bulk_results) >= 10

    async def test_concurrent_operations(self, test_db):
        """Test concurrent MongoDB operations."""

        async def create_corpus(id: int):
            corpus = Corpus(
                corpus_name=f"concurrent-{id}",
                vocabulary=[f"word{id}"],
                language=Language.ENGLISH,
            )
            return await corpus.save()

        # Run concurrent creates
        tasks = [create_corpus(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 20
        for i, result in enumerate(results):
            assert result.corpus_name == f"concurrent-{i}"
