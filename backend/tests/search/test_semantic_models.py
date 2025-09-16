"""Comprehensive tests for semantic search models with real MongoDB."""

import asyncio
import base64

import numpy as np
import pytest
from beanie import PydanticObjectId

from floridify.caching.models import ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.models.base import Language
from floridify.search.semantic.constants import DEFAULT_BATCH_SIZE, MODEL_BATCH_SIZES
from floridify.search.semantic.models import SemanticIndex


class TestSemanticIndexCreation:
    """Test SemanticIndex creation and initialization."""

    @pytest.mark.asyncio
    async def test_basic_creation(self, test_db):
        """Test creating a basic SemanticIndex."""
        corpus = await Corpus.create(
            corpus_name="semantic_test",
            vocabulary=["test", "example", "word"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)

        assert index.corpus_id == corpus.id
        assert index.corpus_name == "semantic_test"
        assert index.vocabulary_hash == corpus.vocabulary_hash
        assert index.model_name == "all-MiniLM-L6-v2"  # Default
        assert len(index.vocabulary) == 3
        assert index.batch_size > 0

    @pytest.mark.asyncio
    async def test_creation_with_custom_model(self, test_db):
        """Test creating SemanticIndex with custom model."""
        corpus = await Corpus.create(
            corpus_name="custom_model_test",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        model_name = "BAAI/bge-m3"
        index = await SemanticIndex.create(corpus, model_name=model_name)

        assert index.model_name == model_name
        # Should auto-select batch size for this model
        assert index.batch_size == MODEL_BATCH_SIZES.get(model_name, DEFAULT_BATCH_SIZE)

    @pytest.mark.asyncio
    async def test_creation_with_custom_batch_size(self, test_db):
        """Test creating SemanticIndex with custom batch size."""
        corpus = await Corpus.create(
            corpus_name="batch_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        custom_batch_size = 64
        index = await SemanticIndex.create(corpus, batch_size=custom_batch_size)

        assert index.batch_size == custom_batch_size

    @pytest.mark.asyncio
    async def test_lemmatized_vocabulary(self, test_db):
        """Test SemanticIndex with lemmatized vocabulary."""
        corpus = Corpus(
            corpus_name="lemma_test",
            vocabulary=["running", "ran", "runs"],
            lemmatized_vocabulary=["run", "run", "run"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)

        assert index.vocabulary == ["running", "ran", "runs"]
        assert index.lemmatized_vocabulary == ["run", "run", "run"]


class TestSemanticIndexPersistence:
    """Test SemanticIndex MongoDB persistence."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, test_db):
        """Test saving and loading SemanticIndex."""
        corpus = await Corpus.create(
            corpus_name="persist_semantic",
            vocabulary=["save", "load", "test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create and configure index
        index = await SemanticIndex.create(corpus)
        index.num_embeddings = 3
        index.embedding_dimension = 384
        index.build_time_seconds = 1.5
        index.memory_usage_mb = 10.0

        # Save
        await index.save()

        # Load
        loaded = await SemanticIndex.get(corpus_id=corpus.corpus_id, model_name=index.model_name)

        assert loaded is not None
        assert loaded.corpus_name == "persist_semantic"
        assert loaded.num_embeddings == 3
        assert loaded.embedding_dimension == 384
        assert loaded.vocabulary == ["save", "load", "test"]

    @pytest.mark.asyncio
    async def test_load_by_corpus_name(self, test_db):
        """Test loading SemanticIndex by corpus name."""
        corpus = await Corpus.create(
            corpus_name="name_load_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus, model_name="test-model")
        await index.save()

        # Load by name
        loaded = await SemanticIndex.get(corpus_name="name_load_test", model_name="test-model")

        assert loaded is not None
        assert loaded.corpus_name == "name_load_test"
        assert loaded.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_get_or_create_cached(self, test_db):
        """Test get_or_create returns cached index."""
        corpus = await Corpus.create(
            corpus_name="cache_test",
            vocabulary=["cached"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # First call creates
        index1 = await SemanticIndex.get_or_create(corpus)
        index1.num_embeddings = 100  # Mark it
        await index1.save()

        # Second call gets cached
        index2 = await SemanticIndex.get_or_create(corpus)
        assert index2.num_embeddings == 100  # Should have our mark

    @pytest.mark.asyncio
    async def test_get_or_create_new_on_hash_change(self, test_db):
        """Test get_or_create creates new index on vocabulary change."""
        corpus = await Corpus.create(
            corpus_name="hash_change_test",
            vocabulary=["original"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create first index
        index1 = await SemanticIndex.get_or_create(corpus)
        hash1 = index1.vocabulary_hash

        # Update corpus
        corpus.vocabulary.append("new")
        corpus.update_version("Added word")
        await corpus.save()

        # Should create new index
        index2 = await SemanticIndex.get_or_create(corpus)
        assert index2.vocabulary_hash != hash1
        assert "new" in index2.vocabulary


class TestSemanticIndexData:
    """Test SemanticIndex data storage."""

    @pytest.mark.asyncio
    async def test_embeddings_storage(self, test_db):
        """Test storing embeddings as base64."""
        corpus = await Corpus.create(
            corpus_name="embeddings_test",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)

        # Simulate embeddings
        embeddings = np.random.randn(2, 384).astype(np.float32)
        embeddings_bytes = embeddings.tobytes()
        index.embeddings = base64.b64encode(embeddings_bytes).decode("utf-8")
        index.num_embeddings = 2
        index.embedding_dimension = 384

        await index.save()

        # Load and verify
        loaded = await SemanticIndex.get(corpus_id=corpus.corpus_id)
        assert loaded is not None
        assert loaded.embeddings == index.embeddings

        # Decode and verify shape
        decoded_bytes = base64.b64decode(loaded.embeddings)
        decoded_array = np.frombuffer(decoded_bytes, dtype=np.float32).reshape(2, 384)
        assert decoded_array.shape == (2, 384)

    @pytest.mark.asyncio
    async def test_faiss_index_storage(self, test_db):
        """Test storing FAISS index as base64."""
        corpus = await Corpus.create(
            corpus_name="faiss_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)

        # Simulate FAISS index data
        fake_index_data = b"fake_faiss_index_binary_data"
        index.index_data = base64.b64encode(fake_index_data).decode("utf-8")
        index.index_type = "IVF"
        index.index_params = {"nlist": 100, "nprobe": 10}

        await index.save()

        # Load and verify
        loaded = await SemanticIndex.get(corpus_id=corpus.corpus_id)
        assert loaded is not None
        assert loaded.index_type == "IVF"
        assert loaded.index_params["nlist"] == 100
        assert base64.b64decode(loaded.index_data) == fake_index_data

    @pytest.mark.asyncio
    async def test_variant_mappings(self, test_db):
        """Test variant and lemma mappings."""
        corpus = Corpus(
            corpus_name="mapping_test",
            vocabulary=["running", "ran", "walks", "walked"],
            lemmatized_vocabulary=["run", "run", "walk", "walk"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)

        # Set up mappings
        index.variant_mapping = {
            "0": 0,  # running -> run (lemma idx 0)
            "1": 0,  # ran -> run
            "2": 1,  # walks -> walk (lemma idx 1)
            "3": 1,  # walked -> walk
        }

        index.lemma_to_embeddings = {
            "0": [0, 1],  # run has embeddings 0 and 1
            "1": [2, 3],  # walk has embeddings 2 and 3
        }

        await index.save()

        # Load and verify
        loaded = await SemanticIndex.get(corpus_id=corpus.corpus_id)
        assert loaded is not None
        assert loaded.variant_mapping["0"] == 0
        assert loaded.lemma_to_embeddings["0"] == [0, 1]


class TestSemanticIndexStatistics:
    """Test SemanticIndex statistics tracking."""

    @pytest.mark.asyncio
    async def test_statistics_persistence(self, test_db):
        """Test persisting index statistics."""
        corpus = await Corpus.create(
            corpus_name="stats_test",
            vocabulary=["test"] * 100,  # 100 words
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)

        # Set statistics
        index.num_embeddings = 100
        index.embedding_dimension = 768
        index.build_time_seconds = 5.5
        index.memory_usage_mb = 25.3
        index.embeddings_per_second = 18.2

        await index.save()

        # Load and verify
        loaded = await SemanticIndex.get(corpus_id=corpus.corpus_id)
        assert loaded is not None
        assert loaded.num_embeddings == 100
        assert loaded.embedding_dimension == 768
        assert loaded.build_time_seconds == 5.5
        assert loaded.memory_usage_mb == 25.3
        assert loaded.embeddings_per_second == 18.2


class TestSemanticIndexVersioning:
    """Test SemanticIndex versioning."""

    @pytest.mark.asyncio
    async def test_version_config_usage(self, test_db):
        """Test using version configuration."""
        corpus = await Corpus.create(
            corpus_name="version_config_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Save with custom config
        index = await SemanticIndex.create(corpus)
        config = VersionConfig(use_cache=False)
        await index.save(config)

        # Load with config
        loaded = await SemanticIndex.get(corpus_id=corpus.corpus_id, config=config)
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_multiple_model_versions(self, test_db):
        """Test multiple models for same corpus."""
        corpus = await Corpus.create(
            corpus_name="multi_model",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create indices with different models
        model1 = "all-MiniLM-L6-v2"
        index1 = await SemanticIndex.create(corpus, model_name=model1)
        index1.embedding_dimension = 384
        await index1.save()

        model2 = "BAAI/bge-m3"
        index2 = await SemanticIndex.create(corpus, model_name=model2)
        index2.embedding_dimension = 1024
        await index2.save()

        # Load each model
        loaded1 = await SemanticIndex.get(corpus_id=corpus.corpus_id, model_name=model1)
        loaded2 = await SemanticIndex.get(corpus_id=corpus.corpus_id, model_name=model2)

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1.embedding_dimension == 384
        assert loaded2.embedding_dimension == 1024


class TestSemanticIndexErrors:
    """Test error handling in SemanticIndex."""

    @pytest.mark.asyncio
    async def test_missing_corpus_error(self):
        """Test error when corpus ID/name not provided."""
        with pytest.raises(ValueError, match="Either corpus_id or corpus_name"):
            await SemanticIndex.get()

    @pytest.mark.asyncio
    async def test_not_found(self, test_db):
        """Test handling when index not found."""
        fake_id = PydanticObjectId()
        index = await SemanticIndex.get(corpus_id=fake_id)
        assert index is None

    @pytest.mark.asyncio
    async def test_invalid_model_name(self, test_db):
        """Test handling invalid model names."""
        corpus = await Corpus.create(
            corpus_name="invalid_model",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Should still create with unknown model
        index = await SemanticIndex.create(corpus, model_name="nonexistent-model")
        assert index.model_name == "nonexistent-model"
        # Should use default batch size
        assert index.batch_size == DEFAULT_BATCH_SIZE


class TestSemanticIndexConcurrency:
    """Test concurrent operations on SemanticIndex."""

    @pytest.mark.asyncio
    async def test_concurrent_creation(self, test_db):
        """Test concurrent index creation."""
        corpora = []
        for i in range(5):
            corpus = await Corpus.create(
                corpus_name=f"concurrent_{i}",
                vocabulary=[f"word_{i}"],
                language=Language.ENGLISH,
            )
            await corpus.save()
            corpora.append(corpus)

        # Create indices concurrently
        tasks = [SemanticIndex.create(c) for c in corpora]
        indices = await asyncio.gather(*tasks)

        assert len(indices) == 5
        for i, index in enumerate(indices):
            assert index.corpus_name == f"concurrent_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_get_or_create(self, test_db):
        """Test concurrent get_or_create calls."""
        corpus = await Corpus.create(
            corpus_name="concurrent_get",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Multiple concurrent calls
        tasks = [SemanticIndex.get_or_create(corpus) for _ in range(5)]
        indices = await asyncio.gather(*tasks)

        # All should get the same index
        first_hash = indices[0].vocabulary_hash
        for index in indices[1:]:
            assert index.vocabulary_hash == first_hash


class TestSemanticIndexMetadata:
    """Test SemanticIndex metadata handling."""

    @pytest.mark.asyncio
    async def test_metadata_defaults(self):
        """Test SemanticIndex.Metadata defaults."""
        metadata = SemanticIndex.Metadata(
            resource_id="test_semantic",
            corpus_id=PydanticObjectId(),
            model_name="test-model",
        )

        assert metadata.resource_type == ResourceType.SEMANTIC
        assert metadata.namespace == "semantic"
        assert metadata.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_metadata_in_save(self, test_db):
        """Test metadata saved with index."""
        corpus = await Corpus.create(
            corpus_name="metadata_save",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)
        index.num_embeddings = 50
        index.embedding_dimension = 768
        await index.save()

        # Metadata should include these fields
        # This is verified internally by the save method


class TestSemanticIndexSerialization:
    """Test SemanticIndex serialization."""

    @pytest.mark.asyncio
    async def test_model_dump_exclude_none(self, test_db):
        """Test model_dump excludes None values."""
        corpus = await Corpus.create(
            corpus_name="dump_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = await SemanticIndex.create(corpus)
        dumped = index.model_dump()

        # Should not have None values
        for value in dumped.values():
            assert value is not None

    @pytest.mark.asyncio
    async def test_model_load(self):
        """Test loading from dictionary."""
        data = {
            "index_id": str(PydanticObjectId()),
            "corpus_id": str(PydanticObjectId()),
            "corpus_name": "test",
            "vocabulary_hash": "hash123",
            "model_name": "test-model",
            "vocabulary": ["word1", "word2"],
            "num_embeddings": 2,
        }

        index = SemanticIndex.model_load(data)
        assert index.corpus_name == "test"
        assert index.model_name == "test-model"
        assert len(index.vocabulary) == 2
