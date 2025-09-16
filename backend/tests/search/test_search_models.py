"""Comprehensive tests for search models with real MongoDB integration."""

import asyncio

import pytest
from beanie import PydanticObjectId

from floridify.caching.manager import get_version_manager
from floridify.caching.models import ResourceType, VersionConfig
from floridify.corpus.core import Corpus
from floridify.models.base import Language
from floridify.search.constants import SearchMethod
from floridify.search.models import SearchIndex, SearchResult, TrieIndex


class TestSearchResult:
    """Test SearchResult model functionality."""

    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        result = SearchResult(
            word="test",
            score=0.95,
            method=SearchMethod.EXACT,
            language=Language.ENGLISH,
            metadata={"frequency": 100},
        )

        assert result.word == "test"
        assert result.score == 0.95
        assert result.method == SearchMethod.EXACT
        assert result.language == Language.ENGLISH
        assert result.metadata["frequency"] == 100

    def test_search_result_comparison(self):
        """Test SearchResult comparison for sorting."""
        result1 = SearchResult(word="a", score=0.9, method=SearchMethod.FUZZY)
        result2 = SearchResult(word="b", score=0.8, method=SearchMethod.FUZZY)
        result3 = SearchResult(word="c", score=0.95, method=SearchMethod.EXACT)

        # Higher score should be "less than" for reverse sorting
        assert result3 < result1 < result2

        # Test sorting
        results = sorted([result2, result1, result3])
        assert results[0].score == 0.95
        assert results[1].score == 0.9
        assert results[2].score == 0.8

    def test_search_result_with_lemma(self):
        """Test SearchResult with lemmatized word."""
        result = SearchResult(
            word="running",
            lemmatized_word="run",
            score=0.85,
            method=SearchMethod.FUZZY,
        )

        assert result.word == "running"
        assert result.lemmatized_word == "run"

    def test_search_result_validation(self):
        """Test SearchResult validation."""
        # Valid score
        result = SearchResult(word="test", score=0.5, method=SearchMethod.FUZZY)
        assert result.score == 0.5

        # Invalid score (too high)
        with pytest.raises(ValueError):
            SearchResult(word="test", score=1.5, method=SearchMethod.FUZZY)

        # Invalid score (negative)
        with pytest.raises(ValueError):
            SearchResult(word="test", score=-0.1, method=SearchMethod.FUZZY)


class TestTrieIndex:
    """Test TrieIndex model with MongoDB persistence."""

    @pytest.mark.asyncio
    async def test_trie_index_creation(self, test_db):
        """Test creating a TrieIndex from corpus."""
        # Create test corpus
        corpus = await Corpus.create(
            corpus_name="trie_test",
            vocabulary=["apple", "banana", "cherry"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create trie index
        index = await TrieIndex.create(corpus)

        assert index.corpus_id == corpus.corpus_id
        assert index.corpus_name == "trie_test"
        assert index.vocabulary_hash == corpus.vocabulary_hash
        assert len(index.trie_data) == 3
        assert index.trie_data == ["apple", "banana", "cherry"]  # Sorted
        assert index.word_count == 3
        assert index.build_time_seconds > 0

    @pytest.mark.asyncio
    async def test_trie_index_frequencies(self, test_db):
        """Test trie index with word frequencies."""
        # Create corpus with frequencies
        corpus = await Corpus.create(
            corpus_name="freq_test",
            vocabulary=["common", "rare", "medium"],
            language=Language.ENGLISH,
        )
        # Add frequencies
        corpus.word_frequencies = {"common": 1000, "rare": 10, "medium": 100}
        await corpus.save()

        # Create trie index
        index = await TrieIndex.create(corpus)

        assert index.word_frequencies["common"] == 1000
        assert index.word_frequencies["rare"] == 10
        assert index.word_frequencies["medium"] == 100
        assert index.max_frequency == 1000

    @pytest.mark.asyncio
    async def test_trie_index_persistence(self, test_db):
        """Test saving and loading TrieIndex from MongoDB."""
        # Create corpus
        corpus = await Corpus.create(
            corpus_name="persist_test",
            vocabulary=["word1", "word2"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create and save index
        index = await TrieIndex.create(corpus)
        await index.save()

        # Load index
        loaded = await TrieIndex.get(corpus_id=corpus.corpus_id)

        assert loaded is not None
        assert loaded.corpus_name == "persist_test"
        assert loaded.vocabulary_hash == index.vocabulary_hash
        assert loaded.trie_data == index.trie_data
        assert loaded.word_count == 2

    @pytest.mark.asyncio
    async def test_trie_index_get_by_name(self, test_db):
        """Test loading TrieIndex by corpus name."""
        # Create corpus
        corpus = await Corpus.create(
            corpus_name="name_lookup",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create and save index
        index = await TrieIndex.create(corpus)
        await index.save()

        # Load by name
        loaded = await TrieIndex.get(corpus_name="name_lookup")

        assert loaded is not None
        assert loaded.corpus_name == "name_lookup"

    @pytest.mark.asyncio
    async def test_trie_index_get_or_create(self, test_db):
        """Test get_or_create functionality."""
        # Create corpus
        corpus = await Corpus.create(
            corpus_name="get_or_create",
            vocabulary=["test1", "test2"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # First call should create
        index1 = await TrieIndex.get_or_create(corpus)
        assert index1.word_count == 2

        # Second call should get existing
        index2 = await TrieIndex.get_or_create(corpus)
        assert index2.vocabulary_hash == index1.vocabulary_hash

        # Update corpus vocabulary
        corpus.vocabulary.append("test3")
        corpus.update_version("Added word")
        await corpus.save()

        # Should create new index due to hash change
        index3 = await TrieIndex.get_or_create(corpus)
        assert index3.vocabulary_hash != index1.vocabulary_hash
        assert index3.word_count == 3

    @pytest.mark.asyncio
    async def test_trie_index_normalized_mapping(self, test_db):
        """Test normalized to original word mapping."""
        # Create corpus with diacritics
        corpus = Corpus(
            corpus_name="diacritic_test",
            vocabulary=["cafe", "naive", "resume"],
            original_vocabulary=["café", "naïve", "résumé"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create index
        index = await TrieIndex.create(corpus)

        assert index.normalized_to_original["cafe"] == "café"
        assert index.normalized_to_original["naive"] == "naïve"
        assert index.normalized_to_original["resume"] == "résumé"

    @pytest.mark.asyncio
    async def test_trie_index_version_config(self, test_db):
        """Test TrieIndex with version configuration."""
        corpus = await Corpus.create(
            corpus_name="version_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Save with version config
        index = await TrieIndex.create(corpus)
        config = VersionConfig(use_cache=False)
        await index.save(config)

        # Load with config
        loaded = await TrieIndex.get(corpus_id=corpus.corpus_id, config=config)
        assert loaded is not None


class TestSearchIndex:
    """Test SearchIndex model with MongoDB persistence."""

    @pytest.mark.asyncio
    async def test_search_index_creation(self, test_db):
        """Test creating a SearchIndex."""
        corpus = await Corpus.create(
            corpus_name="search_index_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        index = SearchIndex(
            corpus_id=corpus.corpus_id,
            corpus_name="search_index_test",
            vocabulary_hash=corpus.vocabulary_hash,
            min_score=0.8,
            semantic_enabled=True,
            semantic_model="BAAI/bge-m3",
            has_trie=True,
            has_fuzzy=True,
            has_semantic=False,
            vocabulary_size=1,
        )

        assert index.corpus_name == "search_index_test"
        assert index.min_score == 0.8
        assert index.semantic_enabled is True
        assert index.has_trie is True

    @pytest.mark.asyncio
    async def test_search_index_persistence(self, test_db):
        """Test saving and loading SearchIndex from MongoDB."""
        corpus = await Corpus.create(
            corpus_name="search_persist",
            vocabulary=["word"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create and save index
        index = SearchIndex(
            corpus_id=corpus.corpus_id,
            corpus_name="search_persist",
            vocabulary_hash=corpus.vocabulary_hash,
            semantic_enabled=False,
            vocabulary_size=1,
        )
        await index.save()

        # Load index
        loaded = await SearchIndex.get(corpus_id=corpus.corpus_id)

        assert loaded is not None
        assert loaded.corpus_name == "search_persist"
        assert loaded.semantic_enabled is False

    @pytest.mark.asyncio
    async def test_search_index_get_or_create(self, test_db):
        """Test SearchIndex get_or_create functionality."""
        corpus = await Corpus.create(
            corpus_name="search_get_or_create",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # First call should create
        index1 = await SearchIndex.get_or_create(
            corpus=corpus, min_score=0.7, semantic=True, semantic_model="test-model"
        )

        assert index1.corpus_name == "search_get_or_create"
        assert index1.min_score == 0.7
        assert index1.semantic_enabled is True

        # Second call should get existing
        index2 = await SearchIndex.get_or_create(corpus=corpus)
        assert index2.index_id == index1.index_id

    @pytest.mark.asyncio
    async def test_search_index_component_references(self, test_db):
        """Test SearchIndex with component index references."""
        corpus = await Corpus.create(
            corpus_name="components_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create trie index
        trie_index = await TrieIndex.create(corpus)
        await trie_index.save()

        # Create search index with references
        search_index = SearchIndex(
            corpus_id=corpus.corpus_id,
            corpus_name="components_test",
            vocabulary_hash=corpus.vocabulary_hash,
            trie_index_id=trie_index.index_id,
            has_trie=True,
        )

        assert search_index.trie_index_id == trie_index.index_id
        assert search_index.has_trie is True

    @pytest.mark.asyncio
    async def test_search_index_update_components(self, test_db):
        """Test updating SearchIndex components."""
        corpus = await Corpus.create(
            corpus_name="update_components",
            vocabulary=["initial"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create initial index
        index = await SearchIndex.get_or_create(corpus=corpus, semantic=False)
        assert index.has_semantic is False

        # Update to enable semantic
        index.semantic_enabled = True
        index.has_semantic = True
        index.semantic_model = "new-model"
        await index.save()

        # Load and verify
        loaded = await SearchIndex.get(corpus_id=corpus.corpus_id)
        assert loaded is not None
        assert loaded.semantic_enabled is True
        assert loaded.semantic_model == "new-model"


class TestModelVersioning:
    """Test versioning functionality for search models."""

    @pytest.mark.asyncio
    async def test_trie_index_versioning(self, test_db):
        """Test TrieIndex version tracking."""
        corpus = await Corpus.create(
            corpus_name="trie_version",
            vocabulary=["v1"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create v1
        index_v1 = await TrieIndex.create(corpus)
        await index_v1.save()

        # Update corpus
        corpus.vocabulary.append("v2")
        corpus.update_version("Added v2")
        await corpus.save()

        # Create v2
        index_v2 = await TrieIndex.create(corpus)
        await index_v2.save()

        # Both versions should have different hashes
        assert index_v1.vocabulary_hash != index_v2.vocabulary_hash
        assert index_v2.word_count > index_v1.word_count

    @pytest.mark.asyncio
    async def test_search_index_versioning(self, test_db):
        """Test SearchIndex version tracking."""
        corpus = await Corpus.create(
            corpus_name="search_version",
            vocabulary=["original"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create v1
        index_v1 = await SearchIndex.get_or_create(corpus=corpus)
        v1_hash = index_v1.vocabulary_hash

        # Update corpus
        corpus.vocabulary.append("updated")
        corpus.update_version("Updated vocabulary")
        await corpus.save()

        # Create v2
        index_v2 = await SearchIndex.get_or_create(corpus=corpus)

        assert index_v2.vocabulary_hash != v1_hash
        assert index_v2.vocabulary_size > index_v1.vocabulary_size


class TestConcurrentOperations:
    """Test concurrent operations on search models."""

    @pytest.mark.asyncio
    async def test_concurrent_trie_creation(self, test_db):
        """Test concurrent TrieIndex creation."""
        # Create multiple corpora
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
        tasks = [TrieIndex.create(c) for c in corpora]
        indices = await asyncio.gather(*tasks)

        assert len(indices) == 5
        for i, index in enumerate(indices):
            assert index.corpus_name == f"concurrent_{i}"

    @pytest.mark.asyncio
    async def test_concurrent_search_index_operations(self, test_db):
        """Test concurrent SearchIndex operations."""
        corpus = await Corpus.create(
            corpus_name="concurrent_search",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Multiple concurrent get_or_create calls
        tasks = [
            SearchIndex.get_or_create(corpus=corpus, min_score=0.7 + i * 0.01) for i in range(5)
        ]

        indices = await asyncio.gather(*tasks)

        # Should all get the same index (first one created)
        first_id = indices[0].index_id
        for index in indices[1:]:
            assert index.index_id == first_id


class TestErrorHandling:
    """Test error handling in search models."""

    @pytest.mark.asyncio
    async def test_trie_index_missing_corpus(self):
        """Test error when corpus ID/name not provided."""
        with pytest.raises(ValueError, match="Either corpus_id or corpus_name"):
            await TrieIndex.get()

    @pytest.mark.asyncio
    async def test_search_index_missing_corpus(self):
        """Test error when corpus ID/name not provided."""
        with pytest.raises(ValueError, match="Either corpus_id or corpus_name"):
            await SearchIndex.get()

    @pytest.mark.asyncio
    async def test_trie_index_not_found(self, test_db):
        """Test handling when TrieIndex not found."""
        fake_id = PydanticObjectId()
        index = await TrieIndex.get(corpus_id=fake_id)
        assert index is None

    @pytest.mark.asyncio
    async def test_search_index_not_found(self, test_db):
        """Test handling when SearchIndex not found."""
        index = await SearchIndex.get(corpus_name="nonexistent")
        assert index is None


class TestModelMetadata:
    """Test model metadata and nested classes."""

    @pytest.mark.asyncio
    async def test_trie_metadata_defaults(self, test_db):
        """Test TrieIndex.Metadata defaults."""
        metadata = TrieIndex.Metadata(
            resource_id="test_trie",
            corpus_id=PydanticObjectId(),
        )

        assert metadata.resource_type == ResourceType.TRIE
        assert metadata.namespace == "trie"

    @pytest.mark.asyncio
    async def test_search_metadata_defaults(self, test_db):
        """Test SearchIndex.Metadata defaults."""
        metadata = SearchIndex.Metadata(resource_id="test_search")

        assert metadata.resource_type == ResourceType.SEARCH
        assert metadata.namespace == "search"

    @pytest.mark.asyncio
    async def test_metadata_versioning(self, test_db):
        """Test metadata version tracking."""
        corpus = await Corpus.create(
            corpus_name="metadata_test",
            vocabulary=["test"],
            language=Language.ENGLISH,
        )
        await corpus.save()

        # Create and save index
        index = await TrieIndex.create(corpus)
        await index.save()

        # Get version manager to check metadata
        manager = get_version_manager()
        metadata = await manager.get_latest(
            resource_id=f"{corpus.corpus_name}:trie",
            resource_type=ResourceType.TRIE,
        )

        assert metadata is not None
        assert metadata.resource_type == ResourceType.TRIE
        assert hasattr(metadata, "version_info")
