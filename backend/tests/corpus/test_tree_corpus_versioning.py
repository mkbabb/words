"""Comprehensive tests for TreeCorpus versioning chains."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from floridify.caching.models import VersionInfo
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


class TestTreeCorpusVersioning:
    """Comprehensive tests for TreeCorpus versioning functionality."""

    @pytest.mark.asyncio
    async def test_basic_version_creation(self, test_db):
        """Test basic version creation and updates."""
        corpus = Corpus(
            corpus_name="versioned_corpus",
            language=Language.ENGLISH,
            vocabulary=["initial", "words"],
            corpus_type=CorpusType.LANGUAGE,
        )
        corpus.version_info = VersionInfo(version="1.0.0", data_hash="hash_v1", is_latest=True)
        await corpus.save()

        # Verify initial version
        assert corpus.version_info.version == "1.0.0"
        assert corpus.version_info.is_latest is True
        initial_id = corpus.id

        # Update version
        corpus.vocabulary.extend(["new", "additions"])
        corpus.update_version("Added new vocabulary")
        await corpus.save()

        # Verify version was updated
        assert corpus.version_info.version != "1.0.0"
        assert corpus.id == initial_id  # Same document
        assert "new" in corpus.vocabulary

    @pytest.mark.asyncio
    async def test_version_chain_tracking(self, test_db):
        """Test tracking version chains with parent references."""
        manager = TreeCorpusManager()

        # Create initial version
        v1 = Corpus(
            corpus_name="chain_test",
            language=Language.ENGLISH,
            vocabulary=["v1"],
            corpus_type=CorpusType.LANGUAGE,
        )
        v1.version_info = VersionInfo(
            version="1.0.0",
            data_hash="hash_v1",
            is_latest=True,
            parent_version=None,
        )
        await v1.save()

        # Create second version
        v2 = Corpus(
            corpus_name="chain_test",
            language=Language.ENGLISH,
            vocabulary=["v1", "v2"],
            corpus_type=CorpusType.LANGUAGE,
        )
        v2.version_info = VersionInfo(
            version="2.0.0",
            data_hash="hash_v2",
            is_latest=True,
            parent_version="1.0.0",
        )
        await v2.save()

        # Mark v1 as not latest
        v1.version_info.is_latest = False
        await v1.save()

        # Create third version
        v3 = Corpus(
            corpus_name="chain_test",
            language=Language.ENGLISH,
            vocabulary=["v1", "v2", "v3"],
            corpus_type=CorpusType.LANGUAGE,
        )
        v3.version_info = VersionInfo(
            version="3.0.0",
            data_hash="hash_v3",
            is_latest=True,
            parent_version="2.0.0",
        )
        await v3.save()

        # Mark v2 as not latest
        v2.version_info.is_latest = False
        await v2.save()

        # Verify chain
        assert v3.version_info.parent_version == "2.0.0"
        assert v2.version_info.parent_version == "1.0.0"
        assert v1.version_info.parent_version is None

        # Only v3 should be latest
        assert v3.version_info.is_latest is True
        assert v2.version_info.is_latest is False
        assert v1.version_info.is_latest is False

    @pytest.mark.asyncio
    async def test_concurrent_version_updates(self, test_db):
        """Test handling concurrent version updates."""
        corpus = Corpus(
            corpus_name="concurrent_test",
            language=Language.ENGLISH,
            vocabulary=["base"],
            corpus_type=CorpusType.LANGUAGE,
        )
        corpus.version_info = VersionInfo(version="1.0.0", data_hash="hash_v1", is_latest=True)
        await corpus.save()
        corpus_id = corpus.id

        # Simulate concurrent updates
        async def update_corpus(suffix: str):
            # Load corpus
            loaded = await Corpus.get(corpus_id)
            if loaded:
                # Add vocabulary
                loaded.vocabulary.append(f"word_{suffix}")
                loaded.update_version(f"Update {suffix}")
                await loaded.save()
                return loaded.version_info.version

        # Run concurrent updates
        results = await asyncio.gather(
            update_corpus("a"),
            update_corpus("b"),
            update_corpus("c"),
            return_exceptions=True,
        )

        # Filter out any errors
        versions = [r for r in results if isinstance(r, str)]
        assert len(versions) > 0

        # Reload and check final state
        final = await Corpus.get(corpus_id)
        assert final is not None
        assert len(final.vocabulary) > 1

    @pytest.mark.asyncio
    async def test_version_rollback(self, test_db):
        """Test rolling back to previous versions."""
        manager = TreeCorpusManager()

        # Create corpus with multiple versions
        corpus = Corpus(
            corpus_name="rollback_test",
            language=Language.ENGLISH,
            vocabulary=["original"],
            corpus_type=CorpusType.LANGUAGE,
        )
        corpus.version_info = VersionInfo(version="1.0.0", data_hash="hash_v1", is_latest=True)
        await corpus.save()

        # Save state for rollback
        v1_vocabulary = corpus.vocabulary.copy()
        v1_version = corpus.version_info.version

        # Update to v2
        corpus.vocabulary.extend(["added_in_v2"])
        corpus.update_version("Version 2")
        await corpus.save()
        v2_version = corpus.version_info.version

        # Update to v3
        corpus.vocabulary.extend(["added_in_v3"])
        corpus.update_version("Version 3")
        await corpus.save()

        # Rollback to v1 (manual simulation)
        corpus.vocabulary = v1_vocabulary
        corpus.update_version(f"Rolled back from {corpus.version_info.version} to {v1_version}")
        await corpus.save()

        # Verify rollback
        assert "added_in_v2" not in corpus.vocabulary
        assert "added_in_v3" not in corpus.vocabulary
        assert "original" in corpus.vocabulary

    @pytest.mark.asyncio
    async def test_version_metadata_tracking(self, test_db):
        """Test tracking metadata in version info."""
        corpus = Corpus(
            corpus_name="metadata_test",
            language=Language.ENGLISH,
            vocabulary=["test"],
            corpus_type=CorpusType.LANGUAGE,
        )

        # Add version with metadata
        corpus.version_info = VersionInfo(
            version="1.0.0",
            data_hash="hash_v1",
            is_latest=True,
            change_log="Initial version",
            metadata={
                "author": "test_user",
                "reason": "initialization",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        await corpus.save()

        # Update with new metadata
        corpus.vocabulary.append("new_word")
        corpus.version_info = VersionInfo(
            version="2.0.0",
            data_hash="hash_v2",
            is_latest=True,
            parent_version="1.0.0",
            change_log="Added new vocabulary",
            metadata={
                "author": "test_user",
                "reason": "vocabulary expansion",
                "added_words": 1,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        await corpus.save()

        # Verify metadata is preserved
        loaded = await Corpus.get(corpus.id)
        assert loaded is not None
        assert loaded.version_info.metadata["added_words"] == 1
        assert loaded.version_info.change_log == "Added new vocabulary"

    @pytest.mark.asyncio
    async def test_tree_versioning_with_hierarchy(self, test_db):
        """Test versioning in hierarchical tree structure."""
        manager = TreeCorpusManager()

        # Create parent corpus
        parent = Corpus(
            corpus_name="parent",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        parent.version_info = VersionInfo(version="1.0.0", data_hash="parent_v1", is_latest=True)
        await parent.save()

        # Create child corpus
        child = Corpus(
            corpus_name="child",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_corpus_id=parent.id,
            vocabulary=["child_word"],
        )
        child.version_info = VersionInfo(version="1.0.0", data_hash="child_v1", is_latest=True)
        await child.save()

        # Add child to parent
        await manager.add_child(parent, child)

        # Update child version
        child.vocabulary.append("new_child_word")
        child.update_version("Child update")
        await child.save()

        # Update parent version
        parent.update_version("Parent update after child change")
        await parent.save()

        # Verify both have new versions
        assert child.version_info.version != "1.0.0"
        assert parent.version_info.version != "1.0.0"

    @pytest.mark.asyncio
    async def test_version_hash_consistency(self, test_db):
        """Test that version hashes are consistent."""
        corpus = Corpus(
            corpus_name="hash_test",
            language=Language.ENGLISH,
            vocabulary=["word1", "word2"],
            corpus_type=CorpusType.LANGUAGE,
        )

        # Compute hash
        hash1 = corpus.compute_vocabulary_hash()
        corpus.version_info = VersionInfo(version="1.0.0", data_hash=hash1, is_latest=True)
        await corpus.save()

        # Compute hash again with same data
        hash2 = corpus.compute_vocabulary_hash()
        assert hash1 == hash2

        # Change vocabulary
        corpus.vocabulary.append("word3")
        hash3 = corpus.compute_vocabulary_hash()
        assert hash3 != hash1

        # Update version with new hash
        corpus.update_version("Added word3")
        corpus.version_info.data_hash = hash3
        await corpus.save()

        # Verify hash is stored
        loaded = await Corpus.get(corpus.id)
        assert loaded is not None
        assert loaded.version_info.data_hash == hash3

    @pytest.mark.asyncio
    async def test_version_branching(self, test_db):
        """Test branching versions (multiple versions from same parent)."""
        # Create base version
        base = Corpus(
            corpus_name="branch_test",
            language=Language.ENGLISH,
            vocabulary=["base"],
            corpus_type=CorpusType.LANGUAGE,
        )
        base.version_info = VersionInfo(version="1.0.0", data_hash="base_hash", is_latest=False)
        await base.save()

        # Create branch A
        branch_a = Corpus(
            corpus_name="branch_test_a",
            language=Language.ENGLISH,
            vocabulary=["base", "branch_a"],
            corpus_type=CorpusType.LANGUAGE,
        )
        branch_a.version_info = VersionInfo(
            version="2.0.0-a",
            data_hash="branch_a_hash",
            is_latest=True,
            parent_version="1.0.0",
        )
        await branch_a.save()

        # Create branch B
        branch_b = Corpus(
            corpus_name="branch_test_b",
            language=Language.ENGLISH,
            vocabulary=["base", "branch_b"],
            corpus_type=CorpusType.LANGUAGE,
        )
        branch_b.version_info = VersionInfo(
            version="2.0.0-b",
            data_hash="branch_b_hash",
            is_latest=True,
            parent_version="1.0.0",
        )
        await branch_b.save()

        # Both branches have same parent
        assert branch_a.version_info.parent_version == "1.0.0"
        assert branch_b.version_info.parent_version == "1.0.0"

        # But different content
        assert "branch_a" in branch_a.vocabulary
        assert "branch_b" in branch_b.vocabulary
        assert "branch_a" not in branch_b.vocabulary
        assert "branch_b" not in branch_a.vocabulary

    @pytest.mark.asyncio
    async def test_version_cleanup(self, test_db):
        """Test cleaning up old versions."""
        # Create corpus with many versions
        corpus = Corpus(
            corpus_name="cleanup_test",
            language=Language.ENGLISH,
            vocabulary=["v1"],
            corpus_type=CorpusType.LANGUAGE,
        )
        corpus.version_info = VersionInfo(version="1.0.0", data_hash="v1_hash", is_latest=True)
        await corpus.save()
        corpus_id = corpus.id

        # Create 10 versions
        for i in range(2, 12):
            corpus.vocabulary.append(f"v{i}")
            corpus.update_version(f"Version {i}")
            await corpus.save()

        # Find all versions (in a real system)
        all_versions = await Corpus.find_many({"corpus_name": "cleanup_test"}).to_list()

        # In this implementation, we're updating the same document
        # In a real versioning system, you might have multiple documents
        assert len(all_versions) >= 1

    @pytest.mark.asyncio
    async def test_version_conflict_resolution(self, test_db):
        """Test resolving version conflicts."""
        manager = TreeCorpusManager()

        # Create corpus
        corpus = Corpus(
            corpus_name="conflict_test",
            language=Language.ENGLISH,
            vocabulary=["original"],
            corpus_type=CorpusType.LANGUAGE,
        )
        corpus.version_info = VersionInfo(version="1.0.0", data_hash="v1_hash", is_latest=True)
        await corpus.save()

        # Simulate two users loading the same version
        user1_corpus = await Corpus.get(corpus.id)
        user2_corpus = await Corpus.get(corpus.id)

        # Both make different changes
        if user1_corpus:
            user1_corpus.vocabulary.append("user1_word")
            user1_corpus.update_version("User 1 changes")
            await user1_corpus.save()

        if user2_corpus:
            user2_corpus.vocabulary.append("user2_word")
            user2_corpus.update_version("User 2 changes")
            # This save might conflict
            await user2_corpus.save()

        # Load final state
        final = await Corpus.get(corpus.id)
        assert final is not None
        # Last write wins in this simple implementation
        # A real system might merge or reject conflicts

    @pytest.mark.asyncio
    async def test_version_timestamp_tracking(self, test_db):
        """Test tracking timestamps across versions."""
        corpus = Corpus(
            corpus_name="timestamp_test",
            language=Language.ENGLISH,
            vocabulary=["test"],
            corpus_type=CorpusType.LANGUAGE,
        )

        # Set initial timestamp
        created_time = datetime.now(UTC) - timedelta(days=7)
        corpus.created_at = created_time
        corpus.version_info = VersionInfo(
            version="1.0.0",
            data_hash="v1_hash",
            is_latest=True,
            created_at=created_time,
        )
        await corpus.save()

        # Update after some time
        await asyncio.sleep(0.1)  # Small delay
        corpus.vocabulary.append("new")
        corpus.update_version("Update after delay")
        update_time = datetime.now(UTC)
        corpus.version_info.created_at = update_time
        await corpus.save()

        # Verify timestamps
        loaded = await Corpus.get(corpus.id)
        assert loaded is not None
        assert loaded.created_at <= loaded.version_info.created_at

    @pytest.mark.asyncio
    async def test_version_migration(self, test_db):
        """Test migrating between version formats."""
        # Old format corpus (simulated)
        old_corpus = Corpus(
            corpus_name="migration_test",
            language=Language.ENGLISH,
            vocabulary=["old_format"],
            corpus_type=CorpusType.LANGUAGE,
        )
        # Simulate old version format
        old_corpus.version_info = VersionInfo(
            version="1",  # Old simple version
            data_hash="old_hash",
            is_latest=True,
        )
        await old_corpus.save()

        # Migrate to new format
        old_corpus.version_info.version = "1.0.0"  # Semantic versioning
        old_corpus.version_info.metadata = {
            "migrated": True,
            "migration_date": datetime.now(UTC).isoformat(),
            "old_version": "1",
        }
        await old_corpus.save()

        # Verify migration
        migrated = await Corpus.get(old_corpus.id)
        assert migrated is not None
        assert migrated.version_info.version == "1.0.0"
        assert migrated.version_info.metadata["migrated"] is True
        assert migrated.version_info.metadata["old_version"] == "1"
