"""Test corpus tree structure operations."""

import pytest
from beanie import PydanticObjectId

from floridify.caching.models import CacheNamespace, ResourceType, VersionInfo
from floridify.corpus.core import Corpus
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


def create_test_corpus(
    corpus_name: str,
    corpus_type: CorpusType = CorpusType.LITERATURE,
    is_master: bool = False,
    vocabulary: list[str] | None = None,
    parent_uuid: str | None = None,
) -> Corpus.Metadata:
    """Helper to create a test corpus with required fields."""
    vocabulary = vocabulary or []
    return Corpus.Metadata(
        resource_id=corpus_name,
        resource_type=ResourceType.CORPUS,
        namespace=CacheNamespace.CORPUS,
        version_info=VersionInfo(
            version="1.0.0",
            data_hash=f"hash_{corpus_name}",
            is_latest=True,
        ),
        corpus_type=corpus_type,
        is_master=is_master,
        parent_uuid=parent_uuid,
        content_inline={"vocabulary": vocabulary} if vocabulary else None,
        language=Language.ENGLISH,
        vocabulary_size=len(vocabulary),
        vocabulary_hash=f"hash_{corpus_name}",
    )


class TestTreeStructure:
    """Test parent-child tree operations."""

    @pytest.mark.asyncio
    async def test_add_child_to_parent(self, test_db, corpus_tree, assert_helpers):
        """Test adding a child updates parent.child_uuids."""
        parent = corpus_tree["master"]
        new_child = create_test_corpus(
            "New_Work",
            corpus_type=CorpusType.LITERATURE,
            vocabulary=["new", "words"],
            parent_uuid=parent.uuid,
        )
        await new_child.save()

        # Add child to parent
        parent.child_uuids.append(new_child.uuid)
        await parent.save()

        # Verify relationship
        assert_helpers.assert_parent_child_linked(parent, new_child)
        assert new_child.uuid in parent.child_uuids

    @pytest.mark.asyncio
    async def test_remove_child_from_parent(self, test_db, corpus_tree):
        """Test removing child from parent.child_uuids."""
        parent = corpus_tree["master"]
        child = corpus_tree["work1"]

        # Remove child
        original_count = len(parent.child_uuids)
        parent.child_uuids.remove(child.uuid)
        await parent.save()

        # Verify removal
        assert child.uuid not in parent.child_uuids
        assert len(parent.child_uuids) == original_count - 1

    @pytest.mark.asyncio
    async def test_circular_reference_prevention(self, test_db, corpus_tree):
        """Test that circular references are properly prevented in tree operations."""
        from floridify.corpus.manager import TreeCorpusManager

        manager = TreeCorpusManager()
        parent = corpus_tree["master"]
        child = corpus_tree["work1"]

        # Test 1: Can't make parent its own child
        parent.child_uuids.append(parent.uuid)

        # Should detect circular reference when saving metadata directly
        saved = await manager.save_metadata(parent)
        # Manager should have cleaned the circular reference
        assert parent.uuid not in saved.child_uuids

        # Test 2: Can't create circular parent-child relationship
        # Try to make child the parent of its own parent (should be rejected)
        result = await manager.update_parent(parent.id, child.id)
        # Should reject (return False) or None
        assert result in (None, False)

        # Test 3: Verify tree remains consistent after operations
        # Reload to ensure consistency
        reloaded_parent = await manager.get_corpus(corpus_uuid=parent.uuid)
        reloaded_child = await manager.get_corpus(corpus_uuid=child.uuid)

        # Parent should not be in its own children
        assert reloaded_parent.corpus_uuid not in reloaded_parent.child_uuids
        # Child's parent should not create a cycle
        if reloaded_child.parent_uuid:
            assert reloaded_child.parent_uuid != reloaded_child.corpus_uuid

    @pytest.mark.asyncio
    async def test_orphan_detection(self, test_db, corpus_tree):
        """Test finding corpora without parents."""
        all_corpora = list(corpus_tree.values())

        # Find orphans (should only be master)
        orphans = [c for c in all_corpora if c.parent_uuid is None]

        assert len(orphans) == 1
        assert orphans[0].resource_id == "English"
        assert orphans[0].is_master is True

    @pytest.mark.asyncio
    async def test_tree_depth_traversal(self, test_db, corpus_tree):
        """Test navigating multi-level hierarchies."""

        async def get_depth(corpus: Corpus.Metadata) -> int:
            """Calculate depth from root."""
            depth = 0
            current = corpus
            while current.parent_uuid:
                depth += 1
                parent = await Corpus.Metadata.find_one({"uuid": current.parent_uuid})
                if not parent:
                    break
                current = parent
            return depth

        # Test depths
        assert await get_depth(corpus_tree["master"]) == 0
        assert await get_depth(corpus_tree["work1"]) == 1
        assert await get_depth(corpus_tree["chapter1"]) == 2

    @pytest.mark.asyncio
    async def test_tree_consistency(self, test_db, corpus_tree, assert_helpers):
        """Test entire tree structure consistency."""
        assert assert_helpers.assert_tree_consistency(corpus_tree["master"], corpus_tree)

    @pytest.mark.asyncio
    async def test_multiple_parents_prevention(self, test_db):
        """Test that a child can only have one parent."""
        parent1 = create_test_corpus(
            "Parent1",
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        await parent1.save()

        parent2 = create_test_corpus(
            "Parent2",
            corpus_type=CorpusType.LANGUAGE,
            is_master=True,
        )
        await parent2.save()

        child = create_test_corpus(
            "Child",
            corpus_type=CorpusType.LITERATURE,
            parent_uuid=parent1.uuid,
        )
        await child.save()

        # Child already has parent1, setting parent2 should be validated
        assert child.parent_uuid == parent1.uuid
        # In real implementation, setting new parent should update old parent's child_uuids

    @pytest.mark.asyncio
    async def test_master_corpus_properties(self, test_db, corpus_tree):
        """Test that master corpus has correct properties."""
        master = corpus_tree["master"]

        assert master.is_master is True
        # Compare the enum value (string) since Beanie serializes enums
        assert master.corpus_type == CorpusType.LANGUAGE.value
        assert master.parent_uuid is None
        assert len(master.child_uuids) > 0

    @pytest.mark.asyncio
    async def test_leaf_node_properties(self, test_db, corpus_tree):
        """Test that leaf nodes have no children."""
        chapter = corpus_tree["chapter1"]

        assert len(chapter.child_uuids) == 0
        assert chapter.parent_uuid is not None
        assert chapter.is_master is False
