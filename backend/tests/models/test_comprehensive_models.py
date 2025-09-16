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
from datetime import datetime

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from floridify.caching.models import ResourceType
from floridify.corpus.core import Corpus
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.models.registry import initialize_model_registry
from floridify.models.registry import get_model_class
from floridify.caching.models import (
    ResourceType,
    MODEL_REGISTRY,
    BaseVersionedData,
    get_model_class as get_versioned_model_class,
    register_model,
)
from floridify.providers.dictionary.models import DictionaryProviderEntry
from floridify.search.models import SearchIndex


@pytest.mark.asyncio
class TestModelRegistry:
    """Test model registration system."""

    async def test_model_registration(self):
        """Test that all models are properly registered."""
        # Initialize registry
        initialize_model_registry()

        # Check all expected models are registered
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
            assert resource_type in MODEL_REGISTRY
            model_class = MODEL_REGISTRY[resource_type]
            assert issubclass(model_class, BaseVersionedData)

    async def test_get_model_class(self):
        """Test retrieving model classes from registry."""
        initialize_model_registry()

        # Test valid resource types
        corpus_class = get_versioned_model_class(ResourceType.CORPUS)
        assert corpus_class == Corpus.Metadata

        dict_class = get_versioned_model_class(ResourceType.DICTIONARY)
        assert dict_class == DictionaryProviderEntry.Metadata

        # Test invalid resource type
        with pytest.raises(ValueError, match="No model registered"):
            get_versioned_model_class("invalid_type")

    async def test_custom_model_registration(self):
        """Test registering custom models."""
        # Use a test resource type string
        test_type = "test_custom_type"

        # Define custom model
        @register_model(test_type)
        class CustomModel(BaseVersionedData):
            custom_field: str

            class Settings:
                name = "custom_models"

        # Verify registration
        assert test_type in MODEL_REGISTRY
        retrieved = get_versioned_model_class(test_type)
        assert retrieved == CustomModel

    async def test_duplicate_registration_error(self):
        """Test that duplicate registration raises error."""
        initialize_model_registry()

        # The register_model decorator doesn't raise immediately,
        # it raises when trying to register a duplicate key
        # So we test by trying to register to the same key twice
        test_type = "test_duplicate_type"

        @register_model(test_type)
        class FirstModel(BaseVersionedData):
            pass

        # This should raise when we try to register again
        with pytest.raises(ValueError, match="already registered"):

            @register_model(test_type)
            class SecondModel(BaseVersionedData):
                pass


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

        # Invalid corpus - missing required fields
        with pytest.raises(ValidationError):
            Corpus(
                vocabulary=["word1"],
                # Missing corpus_name and language
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
                }
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
            resource_id="search-index-1",
            resource_type=ResourceType.SEARCH,
            corpus_id=str(PydanticObjectId()),
            words=["word1", "word2", "word3"],
            index_type="trie",
        )
        assert valid_index.corpus_id is not None
        assert len(valid_index.words) == 3

        # Invalid - wrong resource type
        with pytest.raises(ValidationError):
            SearchIndex(
                resource_id="search-index-2",
                resource_type="wrong_type",  # Invalid type
                corpus_id=str(PydanticObjectId()),
                words=[],
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
        saved_parent = await parent.save()

        # Create child with parent reference
        child = Corpus(
            corpus_name="child-corpus",
            vocabulary=["child"],
            language=Language.ENGLISH,
            parent_corpus_id=saved_parent.corpus_id,
        )
        saved_child = await child.save()

        # Verify relationship
        assert saved_child.parent_corpus_id == saved_parent.corpus_id

        # Update parent's children list
        saved_parent.child_corpus_ids.append(saved_child.corpus_id)
        await saved_parent.save()

        # Retrieve and verify
        retrieved_parent = await Corpus.get(saved_parent.corpus_id)
        assert saved_child.corpus_id in retrieved_parent.child_corpus_ids

    async def test_corpus_tree_hierarchy(self, test_db):
        """Test multi-level corpus hierarchy."""
        # Create 3-level hierarchy
        master = Corpus(
            corpus_name="master",
            vocabulary=["master"],
            language=Language.ENGLISH,
            is_master=True,
        )
        saved_master = await master.save()

        child1 = Corpus(
            corpus_name="child1",
            vocabulary=["child1"],
            language=Language.ENGLISH,
            parent_corpus_id=saved_master.corpus_id,
        )
        saved_child1 = await child1.save()

        grandchild = Corpus(
            corpus_name="grandchild",
            vocabulary=["grandchild"],
            language=Language.ENGLISH,
            parent_corpus_id=saved_child1.corpus_id,
        )
        saved_grandchild = await grandchild.save()

        # Verify hierarchy
        assert saved_grandchild.parent_corpus_id == saved_child1.corpus_id
        assert saved_child1.parent_corpus_id == saved_master.corpus_id
        assert saved_master.parent_corpus_id is None


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
        saved.metadata["updated_at"] = datetime.utcnow().isoformat()
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
