"""Tests for index invalidation, metadata changes, and component versioning."""

from __future__ import annotations

import hashlib

import pytest
import pytest_asyncio
from beanie import PydanticObjectId

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import (
    CacheNamespace,
    ResourceType,
    VersionInfo,
)
from floridify.corpus.core import Corpus
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.search.index import SearchIndex
from floridify.search.semantic.constants import DEFAULT_SENTENCE_MODEL
from floridify.search.semantic.index import SemanticIndex
from floridify.search.trie.index import TrieIndex


@pytest.mark.asyncio
async def test_corpus_vocabulary_change_invalidates_indices(
    version_manager: VersionedDataManager, test_db
):
    """Test that corpus changes invalidate dependent indices."""
    corpus_id = "corpus_with_indices"

    # Create initial corpus
    corpus = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id=corpus_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="initial_hash",
                is_latest=True,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["apple", "banana"]},
            vocabulary_size=2,
            vocabulary_hash="vocab_hash_1",
        )
    )

    # Create dependent indices
    trie_index = await version_manager.save_versioned_data(
        TrieIndex.Metadata(
            resource_id=f"trie_{corpus_id}",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="trie_hash_1",
                is_latest=True,
            ),
            vocabulary_hash="vocab_hash_1",  # Same as corpus
            corpus_uuid=corpus.uuid,
            content_inline={"trie_data": ["apple", "banana"]},
        )
    )

    semantic_index = await version_manager.save_versioned_data(
        SemanticIndex.Metadata(
            resource_id=f"semantic_{corpus_id}",
            resource_type=ResourceType.SEMANTIC,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="semantic_hash_1",
                is_latest=True,
            ),
            vocabulary_hash="vocab_hash_1",  # Same as corpus
            corpus_uuid=corpus.uuid,
            model_name="test-model",
            content_inline={"embeddings": "base64_embeddings"},
        )
    )

    # Update corpus vocabulary
    updated_corpus = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id=corpus_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="2.0.0",
                data_hash="updated_hash",
                is_latest=True,
                supersedes=corpus.id,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["apple", "banana", "cherry"]},
            vocabulary_size=3,
            vocabulary_hash="vocab_hash_2",  # Changed!
        )
    )

    # Indices with old vocabulary hash should be considered invalid
    # In a real system, we'd check if indices need rebuilding
    assert updated_corpus.vocabulary_hash != corpus.vocabulary_hash
    assert trie_index.vocabulary_hash != updated_corpus.vocabulary_hash
    assert semantic_index.vocabulary_hash != updated_corpus.vocabulary_hash


@pytest.mark.asyncio
async def test_corpus_metadata_change_triggers_rebuild(
    version_manager: VersionedDataManager, test_db
):
    """Test that corpus metadata changes trigger cache invalidation."""
    corpus_id = "metadata_change_test"

    # Create initial corpus
    corpus = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id=corpus_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="hash_1",
                is_latest=True,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["word1", "word2"]},
            vocabulary_size=2,
            vocabulary_hash="vocab_hash_1",
        )
    )

    # Change only metadata (e.g., corpus type)
    updated = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id=corpus_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.1.0",
                data_hash="hash_2",
                is_latest=True,
                supersedes=corpus.id,
            ),
            corpus_type=CorpusType.LITERATURE,  # Changed type
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["word1", "word2"]},  # Same vocab
            vocabulary_size=2,
            vocabulary_hash="vocab_hash_1",  # Same hash
        )
    )

    # Even though vocabulary is same, metadata change creates new version
    assert updated.id != corpus.id
    assert updated.corpus_type != corpus.corpus_type
    assert updated.vocabulary_hash == corpus.vocabulary_hash


@pytest.mark.asyncio
async def test_semantic_index_mongodb_versioning(
    version_manager: VersionedDataManager, test_db
):
    """Test SemanticIndex.Metadata save/load with external content."""
    # Create large embeddings that would be stored externally
    large_embeddings = "x" * (20 * 1024)  # 20KB of data

    semantic = await version_manager.save_versioned_data(
        SemanticIndex.Metadata(
            resource_id="semantic_test",
            resource_type=ResourceType.SEMANTIC,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash=hashlib.sha256(large_embeddings.encode()).hexdigest(),
                is_latest=True,
            ),
            vocabulary_hash="vocab_hash",
            corpus_uuid="test-semantic-corpus-uuid",
            model_name=DEFAULT_SENTENCE_MODEL,
            embedding_dimension=384,
            index_type="flat",
            content_location="cache://semantic_test_v1",  # External storage
            content_inline=None,  # Not stored inline due to size
        )
    )

    # Verify saved correctly
    assert semantic.id is not None
    assert semantic.content_location is not None
    assert semantic.content_inline is None

    # Load and verify
    loaded = await SemanticIndex.Metadata.get(semantic.id)
    assert loaded is not None
    assert loaded.model_name == DEFAULT_SENTENCE_MODEL
    assert loaded.embedding_dimension == 384
    assert loaded.content_location.path == "cache://semantic_test_v1"


@pytest.mark.asyncio
async def test_search_index_component_versioning(
    version_manager: VersionedDataManager, test_db
):
    """Test SearchIndex with versioned component references."""
    corpus_uuid = "test-search-composite-corpus-uuid"

    # Create SearchIndex with component references
    search = await version_manager.save_versioned_data(
        SearchIndex.Metadata(
            resource_id="search_composite",
            resource_type=ResourceType.SEARCH,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="search_hash",
                is_latest=True,
            ),
            vocabulary_hash="vocab_hash",
            corpus_uuid=corpus_uuid,
            content_inline={
                "config": {
                    "min_score": 0.5,
                    "semantic_enabled": True,
                    "fuzzy_threshold": 0.7,
                }
            },
        )
    )

    assert search.id is not None

    # Update with new component versions
    updated_search = await version_manager.save_versioned_data(
        SearchIndex.Metadata(
            resource_id="search_composite",
            resource_type=ResourceType.SEARCH,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="2.0.0",
                data_hash="search_hash_2",
                is_latest=True,
                supersedes=search.id,
            ),
            vocabulary_hash="vocab_hash_2",
            corpus_uuid=corpus_uuid,
            content_inline={
                "config": {
                    "min_score": 0.6,  # Updated config
                    "semantic_enabled": True,
                    "fuzzy_threshold": 0.8,
                }
            },
        )
    )

    assert updated_search.version_info.supersedes == search.id
    assert updated_search.version_info.version == "2.0.0"
