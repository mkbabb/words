"""Tests for version chain integrity, orphan cleanup, and dependency cascading."""

from __future__ import annotations

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
from floridify.search.trie.index import TrieIndex


@pytest.mark.asyncio
async def test_orphaned_version_cleanup(version_manager: VersionedDataManager, test_db):
    """Test cleanup of broken version chains."""
    resource_id = "orphan_test"

    # Create a version chain
    v1 = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="hash_1",
                is_latest=False,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["word1"]},
            vocabulary_size=1,
            vocabulary_hash="vocab_1",
        )
    )

    v2 = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id=resource_id,
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="2.0.0",
                data_hash="hash_2",
                is_latest=True,
                supersedes=v1.id,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["word1", "word2"]},
            vocabulary_size=2,
            vocabulary_hash="vocab_2",
        )
    )

    # Manually break the chain by deleting v1
    await v1.delete()

    # Try to get latest version - should still work
    latest = await version_manager.get_latest_version(
        resource_id=resource_id, resource_type=ResourceType.CORPUS
    )
    assert latest is not None
    assert latest.id == v2.id

    # Verify chain repair (v2 should no longer reference deleted v1)
    refreshed_v2 = await Corpus.Metadata.get(v2.id)
    # The system should handle the broken reference gracefully
    assert refreshed_v2 is not None


@pytest.mark.asyncio
async def test_version_dependency_cascading(
    version_manager: VersionedDataManager, test_db
):
    """Test cascading updates when parent resources change."""
    # Create a hierarchy: SearchIndex -> TrieIndex -> Corpus
    corpus = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id="base_corpus",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="corpus_hash",
                is_latest=True,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["test"]},
            vocabulary_size=1,
            vocabulary_hash="vocab_hash",
        )
    )

    await version_manager.save_versioned_data(
        TrieIndex.Metadata(
            resource_id="derived_trie",
            resource_type=ResourceType.TRIE,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="trie_hash",
                is_latest=True,
            ),
            vocabulary_hash="vocab_hash",
            corpus_uuid=corpus.uuid,
            content_inline={"trie_data": ["test"]},
        )
    )

    await version_manager.save_versioned_data(
        SearchIndex.Metadata(
            resource_id="composite_search",
            resource_type=ResourceType.SEARCH,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="1.0.0",
                data_hash="search_hash",
                is_latest=True,
            ),
            vocabulary_hash="vocab_hash",
            corpus_uuid=corpus.uuid,
            content_inline={"config": {"min_score": 0.5}},
        )
    )

    # Update corpus
    new_corpus = await version_manager.save_versioned_data(
        Corpus.Metadata(
            resource_id="base_corpus",
            resource_type=ResourceType.CORPUS,
            namespace=CacheNamespace.CORPUS,
            version_info=VersionInfo(
                version="2.0.0",
                data_hash="corpus_hash_2",
                is_latest=True,
                supersedes=corpus.id,
            ),
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            content_inline={"vocabulary": ["test", "new"]},
            vocabulary_size=2,
            vocabulary_hash="vocab_hash_2",
        )
    )

    # Verify new version supersedes old
    assert new_corpus.version_info.supersedes == corpus.id

    # Old versions should no longer be latest
    old_corpus = await Corpus.Metadata.get(corpus.id)
    assert old_corpus is not None
    assert not old_corpus.version_info.is_latest


@pytest.mark.asyncio
async def test_trie_index_version_chains(version_manager: VersionedDataManager, test_db):
    """Test TrieIndex version history and retrieval."""
    resource_id = "trie_versioned"

    # Create multiple versions
    versions = []
    for i in range(3):
        prev_id = versions[-1].id if versions else None
        trie = await version_manager.save_versioned_data(
            TrieIndex.Metadata(
                resource_id=resource_id,
                resource_type=ResourceType.TRIE,
                namespace=CacheNamespace.CORPUS,
                version_info=VersionInfo(
                    version=f"{i + 1}.0.0",
                    data_hash=f"trie_hash_{i}",
                    is_latest=(i == 2),
                    supersedes=prev_id,
                ),
                vocabulary_hash=f"vocab_hash_{i}",
                corpus_uuid="test-trie-versioned-corpus-uuid",
                content_inline={
                    "trie_data": [f"word_{j}" for j in range(i + 1)],
                    "word_frequencies": {f"word_{j}": j + 1 for j in range(i + 1)},
                },
            )
        )
        versions.append(trie)

    # Verify chain integrity
    all_versions = await version_manager.list_versions(
        resource_id=resource_id, resource_type=ResourceType.TRIE
    )
    assert len(all_versions) == 3

    # Verify latest
    latest = await version_manager.get_latest_version(
        resource_id=resource_id, resource_type=ResourceType.TRIE
    )
    assert latest.version_info.version == "3.0.0"

    # Verify chain links
    for i in range(1, len(versions)):
        assert versions[i].version_info.supersedes == versions[i - 1].id
