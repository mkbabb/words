"""Comprehensive TreeCorpus CRUD operation tests."""

import pytest

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
class TestTreeCorpusCRUD:
    """Test TreeCorpus CRUD operations comprehensively."""

    async def test_create_single_corpus(self, test_db):
        """Test creating a single corpus."""
        manager = TreeCorpusManager()

        corpus = Corpus(
            corpus_name="test-single",
            vocabulary=["hello", "world", "test"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LEXICON,
        )

        saved = await manager.save_corpus(corpus)

        assert saved is not None
        assert saved.corpus_id is not None
        assert saved.corpus_name == "test-single"
        assert saved.vocabulary == ["hello", "world", "test"]
        assert saved.language == Language.ENGLISH

    async def test_create_tree_structure(self, test_db):
        """Test creating a complete tree structure."""
        manager = TreeCorpusManager()

        # Create master
        master = Corpus(
            corpus_name="master",
            vocabulary=["master", "vocab"],
            language=Language.ENGLISH,
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        saved_master = await manager.save_corpus(master)
        assert saved_master.is_master is True

        # Create children
        child1 = Corpus(
            corpus_name="child1",
            vocabulary=["child", "one"],
            language=Language.ENGLISH,
            parent_uuid=saved_master.corpus_uuid,
        )
        saved_child1 = await manager.save_corpus(child1)

        child2 = Corpus(
            corpus_name="child2",
            vocabulary=["child", "two"],
            language=Language.ENGLISH,
            parent_uuid=saved_master.corpus_uuid,
        )
        saved_child2 = await manager.save_corpus(child2)

        # Create grandchild
        grandchild = Corpus(
            corpus_name="grandchild",
            vocabulary=["grand", "child"],
            language=Language.ENGLISH,
            parent_uuid=saved_child1.corpus_uuid,
        )
        saved_grandchild = await manager.save_corpus(grandchild)

        # Verify relationships
        assert saved_child1.parent_uuid == saved_master.corpus_uuid
        assert saved_child2.parent_uuid == saved_master.corpus_uuid
        assert saved_grandchild is not None
        assert saved_grandchild.parent_uuid == saved_child1.corpus_uuid

    async def test_read_corpus(self, test_db):
        """Test reading corpus by ID and name."""
        manager = TreeCorpusManager()

        # Create corpus
        corpus = Corpus(
            corpus_name="test-read",
            vocabulary=["read", "test"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)

        # Read by ID
        by_id = await manager.get_corpus(corpus_id=saved.corpus_id)
        assert by_id is not None
        assert by_id.corpus_name == "test-read"

        # Read by name
        by_name = await manager.get_corpus(corpus_name="test-read")
        assert by_name is not None
        assert by_name.corpus_id == saved.corpus_id

    async def test_update_corpus(self, test_db):
        """Test updating corpus content and metadata."""
        manager = TreeCorpusManager()

        # Create corpus
        corpus = Corpus(
            corpus_name="test-update",
            vocabulary=["initial"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)

        # Update vocabulary
        updated = await manager.update_corpus(
            corpus_id=saved.corpus_id,
            content={
                "vocabulary": ["initial", "updated", "words"],
                "metadata": {"updated": True},
            },
        )

        assert updated is not None
        assert "updated" in updated.vocabulary
        assert "words" in updated.vocabulary
        assert updated.metadata.get("updated") is True

    async def test_delete_corpus(self, test_db):
        """Test deleting corpus."""
        manager = TreeCorpusManager()

        # Create corpus
        corpus = Corpus(
            corpus_name="test-delete",
            vocabulary=["delete", "me"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)

        # Delete it
        deleted = await manager.delete_corpus(saved.corpus_id)
        assert deleted is True

        # Verify it's gone
        gone = await manager.get_corpus(corpus_id=saved.corpus_id)
        assert gone is None

    async def test_delete_cascade(self, test_db):
        """Test cascading deletion in tree."""
        manager = TreeCorpusManager()

        # Create tree
        master = Corpus(
            corpus_name="cascade-master",
            vocabulary=["master"],
            language=Language.ENGLISH,
        )
        saved_master = await manager.save_corpus(master)

        child = Corpus(
            corpus_name="cascade-child",
            vocabulary=["child"],
            language=Language.ENGLISH,
            parent_uuid=saved_master.corpus_uuid,
        )
        saved_child = await manager.save_corpus(child)

        grandchild = Corpus(
            corpus_name="cascade-grandchild",
            vocabulary=["grandchild"],
            language=Language.ENGLISH,
            parent_uuid=saved_child.corpus_uuid,
        )
        await manager.save_corpus(grandchild)

        # Delete middle child
        deleted = await manager.delete_corpus(saved_child.corpus_id)
        assert deleted is True

        # Child should be gone
        gone_child = await manager.get_corpus(corpus_id=saved_child.corpus_id)
        assert gone_child is None

        # Master should still exist
        master_exists = await manager.get_corpus(corpus_id=saved_master.corpus_id)
        assert master_exists is not None

    async def test_vocabulary_aggregation(self, test_db):
        """Test vocabulary aggregation in tree."""
        manager = TreeCorpusManager()

        # Create tree with vocabularies
        master = Corpus(
            corpus_name="agg-master",
            vocabulary=["master", "word"],
            language=Language.ENGLISH,
            is_master=True,
        )
        saved_master = await manager.save_corpus(master)

        child1 = Corpus(
            corpus_name="agg-child1",
            vocabulary=["child", "one", "word"],
            language=Language.ENGLISH,
        )
        saved_child1 = await manager.save_corpus(child1)
        # Properly establish parent-child relationship
        await manager.update_parent(saved_master.corpus_id, saved_child1.corpus_id)

        child2 = Corpus(
            corpus_name="agg-child2",
            vocabulary=["child", "two", "unique"],
            language=Language.ENGLISH,
        )
        saved_child2 = await manager.save_corpus(child2)
        # Properly establish parent-child relationship
        await manager.update_parent(saved_master.corpus_id, saved_child2.corpus_id)

        # Aggregate vocabularies
        aggregated = await manager.aggregate_vocabularies(saved_master.corpus_id)

        # Master corpus is just a container, so it should only have children's vocabulary
        # (master's own vocabulary is not included when is_master=True)
        expected = {"child", "one", "two", "unique", "word"}
        assert set(aggregated) == expected

    async def test_update_parent(self, test_db):
        """Test updating parent-child relationships."""
        manager = TreeCorpusManager()

        # Create initial structure
        parent1 = Corpus(
            corpus_name="parent1",
            vocabulary=["parent1"],
            language=Language.ENGLISH,
        )
        saved_parent1 = await manager.save_corpus(parent1)

        parent2 = Corpus(
            corpus_name="parent2",
            vocabulary=["parent2"],
            language=Language.ENGLISH,
        )
        saved_parent2 = await manager.save_corpus(parent2)

        child = Corpus(
            corpus_name="movable-child",
            vocabulary=["child"],
            language=Language.ENGLISH,
            parent_uuid=saved_parent1.corpus_uuid,
        )
        saved_child = await manager.save_corpus(child)

        # Move child to parent2
        await manager.update_parent(
            parent_id=saved_parent2.corpus_id,
            child_id=saved_child.corpus_id,
        )

        # Verify move
        moved_child = await manager.get_corpus(corpus_id=saved_child.corpus_id)
        assert moved_child.parent_uuid == saved_parent2.corpus_uuid

    async def test_remove_child(self, test_db):
        """Test removing child from parent without deletion."""
        manager = TreeCorpusManager()

        # Create parent-child
        parent = Corpus(
            corpus_name="parent",
            vocabulary=["parent"],
            language=Language.ENGLISH,
        )
        saved_parent = await manager.save_corpus(parent)

        child = Corpus(
            corpus_name="removable-child",
            vocabulary=["child"],
            language=Language.ENGLISH,
            parent_uuid=saved_parent.corpus_uuid,
        )
        saved_child = await manager.save_corpus(child)

        # Update parent to track child
        saved_parent.child_uuids = [saved_child.corpus_uuid]
        await manager.save_corpus(saved_parent)

        # Remove child from parent (but don't delete)
        removed = await manager.remove_child(
            parent_id=saved_parent.corpus_id,
            child_id=saved_child.corpus_id,
            delete_child=False,
        )
        assert removed is True

        # Child should still exist but without parent
        orphan = await manager.get_corpus(corpus_id=saved_child.corpus_id)
        assert orphan is not None
        assert orphan.parent_uuid is None

        # Parent should not have child
        parent_after = await manager.get_corpus(corpus_id=saved_parent.corpus_id)
        assert saved_child.corpus_uuid not in parent_after.child_uuids

    async def test_cache_invalidation(self, test_db):
        """Test cache invalidation on corpus changes."""
        manager = TreeCorpusManager()

        # Create corpus
        corpus = Corpus(
            corpus_name="cache-test",
            vocabulary=["cache", "test"],
            language=Language.ENGLISH,
        )
        saved = await manager.save_corpus(corpus)

        # Get with cache
        cached = await manager.get_corpus(
            corpus_id=saved.corpus_id,
            config=VersionConfig(use_cache=True),
        )
        assert cached is not None

        # Invalidate
        invalidated = await manager.invalidate_corpus(corpus_name="cache-test")
        assert invalidated is True

        # Force fresh read
        fresh = await manager.get_corpus(
            corpus_id=saved.corpus_id,
            config=VersionConfig(force_rebuild=True),
        )
        assert fresh is not None
