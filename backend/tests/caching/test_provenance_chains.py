"""Test provenance chain tracking in the versioning system.

Provenance chains maintain version-to-version lineage using a doubly-linked
list structure:
- supersedes: Points to the previous version
- superseded_by: Points to the next version
- is_latest: Marks the current head of the chain

This ensures we can:
1. Navigate forward and backward through version history
2. Track which versions supersede which
3. Maintain integrity when versions are deleted
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.caching.manager import VersionedDataManager
from floridify.caching.models import BaseVersionedData, CacheNamespace, ResourceType, VersionConfig
from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language


class TestProvenanceChains:
    """Test version provenance chain integrity."""

    @pytest_asyncio.fixture
    async def corpus_manager(self, test_db):
        """Create corpus manager."""
        return TreeCorpusManager()

    @pytest_asyncio.fixture
    async def version_manager(self, test_db):
        """Create version manager."""
        return VersionedDataManager()

    @pytest.mark.asyncio
    async def test_single_version_no_chain(self, corpus_manager, test_db):
        """Test that a single version has no chain links."""
        corpus = Corpus(
            corpus_name="test_single",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=["word1", "word2"],
            original_vocabulary=["word1", "word2"],
        )
        corpus._build_signature_index()

        saved = await corpus_manager.save_corpus(corpus)

        # Get the version from DB
        versions = await Corpus.Metadata.find(
            Corpus.Metadata.resource_id == "test_single",
        ).to_list()

        assert len(versions) == 1
        version = versions[0]

        # Single version should have no chain links
        assert version.version_info.is_latest is True
        assert version.version_info.supersedes is None
        assert version.version_info.superseded_by is None

    @pytest.mark.asyncio
    async def test_two_version_chain(self, corpus_manager, test_db):
        """Test that updating creates a proper two-version chain."""
        # Create v1
        corpus_v1 = Corpus(
            corpus_name="test_chain",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=["word1", "word2"],
            original_vocabulary=["word1", "word2"],
        )
        corpus_v1._build_signature_index()
        v1 = await corpus_manager.save_corpus(corpus_v1)

        # Create v2 (update)
        corpus_v2 = Corpus(
            corpus_name="test_chain",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=["word1", "word2", "word3"],  # Added word3
            original_vocabulary=["word1", "word2", "word3"],
        )
        corpus_v2._build_signature_index()
        v2 = await corpus_manager.save_corpus(corpus_v2)

        # Get versions from DB
        versions = await Corpus.Metadata.find(
            Corpus.Metadata.resource_id == "test_chain",
        ).sort("+version_info.created_at").to_list()

        assert len(versions) == 2

        old_version, new_version = versions

        # Check chain structure
        assert old_version.version_info.is_latest is False
        assert old_version.version_info.supersedes is None
        assert old_version.version_info.superseded_by == new_version.id

        assert new_version.version_info.is_latest is True
        assert new_version.version_info.supersedes == old_version.id
        assert new_version.version_info.superseded_by is None

    @pytest.mark.asyncio
    async def test_three_version_chain(self, corpus_manager, test_db):
        """Test that multiple updates create a proper chain."""
        corpus_name = "test_long_chain"

        # Create v1
        corpus = Corpus(
            corpus_name=corpus_name,
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=["word1"],
            original_vocabulary=["word1"],
        )
        corpus._build_signature_index()
        await corpus_manager.save_corpus(corpus)

        # Create v2
        corpus.vocabulary = ["word1", "word2"]
        corpus.original_vocabulary = ["word1", "word2"]
        corpus._build_signature_index()
        await corpus_manager.save_corpus(corpus)

        # Create v3
        corpus.vocabulary = ["word1", "word2", "word3"]
        corpus.original_vocabulary = ["word1", "word2", "word3"]
        corpus._build_signature_index()
        await corpus_manager.save_corpus(corpus)

        # Get versions from DB
        versions = await Corpus.Metadata.find(
            Corpus.Metadata.resource_id == corpus_name,
            
        ).sort("+version_info.created_at").to_list()

        assert len(versions) == 3

        v1, v2, v3 = versions

        # Check v1 (oldest)
        assert v1.version_info.is_latest is False
        assert v1.version_info.supersedes is None
        assert v1.version_info.superseded_by == v2.id

        # Check v2 (middle)
        assert v2.version_info.is_latest is False
        assert v2.version_info.supersedes == v1.id
        assert v2.version_info.superseded_by == v3.id

        # Check v3 (latest)
        assert v3.version_info.is_latest is True
        assert v3.version_info.supersedes == v2.id
        assert v3.version_info.superseded_by is None

    @pytest.mark.asyncio
    async def test_chain_navigation(self, corpus_manager, test_db):
        """Test that we can navigate forward and backward through chains."""
        corpus_name = "test_navigation"

        # Create 5 versions
        for i in range(5):
            corpus = Corpus(
                corpus_name=corpus_name,
                corpus_type=CorpusType.CUSTOM,
                language=Language.ENGLISH,
                vocabulary=[f"word{j}" for j in range(i + 1)],
                original_vocabulary=[f"word{j}" for j in range(i + 1)],
            )
            corpus._build_signature_index()
            await corpus_manager.save_corpus(corpus)

        # Get all versions
        versions = await Corpus.Metadata.find(
            Corpus.Metadata.resource_id == corpus_name,
            
        ).sort("+version_info.created_at").to_list()

        assert len(versions) == 5

        # Navigate forward from oldest to newest
        current = versions[0]
        visited_forward = [current]
        while current.version_info.superseded_by:
            next_version = await Corpus.Metadata.get(current.version_info.superseded_by)
            visited_forward.append(next_version)
            current = next_version

        assert len(visited_forward) == 5
        assert visited_forward[-1].version_info.is_latest

        # Navigate backward from newest to oldest
        current = versions[-1]
        visited_backward = [current]
        while current.version_info.supersedes:
            prev_version = await Corpus.Metadata.get(current.version_info.supersedes)
            visited_backward.append(prev_version)
            current = prev_version

        assert len(visited_backward) == 5
        assert visited_backward[-1].version_info.supersedes is None

        # Lists should be reverses of each other
        assert [v.id for v in visited_forward] == [v.id for v in reversed(visited_backward)]

    @pytest.mark.asyncio
    async def test_latest_flag_consistency(self, corpus_manager, test_db):
        """Test that only one version is marked as latest."""
        corpus_name = "test_latest_flag"

        # Create multiple versions
        for i in range(3):
            corpus = Corpus(
                corpus_name=corpus_name,
                corpus_type=CorpusType.CUSTOM,
                language=Language.ENGLISH,
                vocabulary=[f"word{j}" for j in range(i + 1)],
                original_vocabulary=[f"word{j}" for j in range(i + 1)],
            )
            corpus._build_signature_index()
            await corpus_manager.save_corpus(corpus)

            # After each save, check that only one is latest
            versions = await Corpus.Metadata.find(
                Corpus.Metadata.resource_id == corpus_name,
                
            ).to_list()

            latest_count = sum(1 for v in versions if v.version_info.is_latest)
            assert latest_count == 1, f"Expected 1 latest version, found {latest_count}"

    @pytest.mark.asyncio
    async def test_provenance_with_force_rebuild(self, corpus_manager, test_db):
        """Test that force_rebuild creates new versions in the chain."""
        corpus_name = "test_rebuild"

        # Create v1
        corpus = Corpus(
            corpus_name=corpus_name,
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=["word1"],
            original_vocabulary=["word1"],
        )
        corpus._build_signature_index()
        await corpus_manager.save_corpus(corpus)

        # Create v2 with force_rebuild (same content, but should create new version)
        config = VersionConfig(force_rebuild=True)
        await corpus_manager.save_corpus(corpus, config=config)

        # Get versions
        versions = await Corpus.Metadata.find(
            Corpus.Metadata.resource_id == corpus_name,
            
        ).to_list()

        # Should have 2 versions even with same content
        assert len(versions) == 2

        # Check chain
        old_version = next(v for v in versions if not v.version_info.is_latest)
        new_version = next(v for v in versions if v.version_info.is_latest)

        assert old_version.version_info.superseded_by == new_version.id
        assert new_version.version_info.supersedes == old_version.id

    @pytest.mark.asyncio
    async def test_version_hash_changes(self, corpus_manager, test_db):
        """Test that different content creates different hashes."""
        corpus_name = "test_hashes"

        # Create v1
        corpus = Corpus(
            corpus_name=corpus_name,
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=["word1"],
            original_vocabulary=["word1"],
        )
        corpus._build_signature_index()
        await corpus_manager.save_corpus(corpus)

        # Create v2 with different content
        corpus.vocabulary = ["word1", "word2"]
        corpus.original_vocabulary = ["word1", "word2"]
        corpus._build_signature_index()
        await corpus_manager.save_corpus(corpus)

        # Get versions
        versions = await Corpus.Metadata.find(
            Corpus.Metadata.resource_id == corpus_name,
            
        ).sort("+version_info.created_at").to_list()

        assert len(versions) == 2

        # Hashes should be different
        assert versions[0].version_info.data_hash != versions[1].version_info.data_hash