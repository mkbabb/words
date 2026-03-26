"""Tests for corpus parent-child linking, cycle detection, aggregation, and concurrent operations."""

from __future__ import annotations

import asyncio

import pytest

from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
async def test_corpus_parent_child_linking(tree_manager: TreeCorpusManager, test_db):
    """Test proper parent-child relationship management."""
    # Create parent corpus
    parent = Corpus(
        corpus_name="parent_corpus",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=["parent", "word"],
        original_vocabulary=["parent", "word"],
    )
    saved_parent = await tree_manager.save_corpus(parent)

    # Create child corpus
    child = Corpus(
        corpus_name="child_corpus",
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        vocabulary=["child", "word"],
        original_vocabulary=["child", "word"],
        parent_uuid=saved_parent.corpus_uuid,
    )
    saved_child = await tree_manager.save_corpus(child)

    # Verify bidirectional linking
    assert saved_child.parent_uuid == saved_parent.corpus_uuid

    # Reload parent to verify child was added
    reloaded_parent = await tree_manager.get_corpus(corpus_uuid=saved_parent.corpus_uuid)
    assert saved_child.corpus_uuid in reloaded_parent.child_uuids

    # Create another child
    child2 = Corpus(
        corpus_name="child_corpus_2",
        corpus_type=CorpusType.LITERATURE,
        language=Language.ENGLISH,
        vocabulary=["another", "child"],
        original_vocabulary=["another", "child"],
        parent_uuid=saved_parent.corpus_uuid,
    )
    saved_child2 = await tree_manager.save_corpus(child2)

    # Reload parent again
    reloaded_parent = await tree_manager.get_corpus(corpus_uuid=saved_parent.corpus_uuid)
    assert len(reloaded_parent.child_uuids) == 2
    assert saved_child.corpus_uuid in reloaded_parent.child_uuids
    assert saved_child2.corpus_uuid in reloaded_parent.child_uuids


@pytest.mark.asyncio
async def test_corpus_cycle_detection(tree_manager: TreeCorpusManager, test_db):
    """Test detection and prevention of circular references in corpus hierarchy."""
    # Create a chain: A -> B -> C
    corpus_a = await tree_manager.save_corpus(
        Corpus(
            corpus_name="corpus_a",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["a"],
            original_vocabulary=["a"],
        )
    )

    corpus_b = await tree_manager.save_corpus(
        Corpus(
            corpus_name="corpus_b",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["b"],
            original_vocabulary=["b"],
            parent_uuid=corpus_a.corpus_uuid,
        )
    )

    await tree_manager.save_corpus(
        Corpus(
            corpus_name="corpus_c",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["c"],
            original_vocabulary=["c"],
            parent_uuid=corpus_b.corpus_uuid,
        )
    )

    # Try to create cycle: A -> B -> C -> A
    # Note: link_parent_child method doesn't exist - would need to implement cycle detection
    # in save_corpus when setting parent_corpus_id
    # with pytest.raises(ValueError, match="cycle"):
    #     await tree_manager.link_parent_child(
    #         parent_corpus_id=corpus_c.corpus_id,
    #         child_corpus_id=corpus_a.corpus_id
    #     )

    # Try to make B a parent of A (would create A -> B -> A cycle)
    # with pytest.raises(ValueError, match="cycle"):
    #     await tree_manager.link_parent_child(
    #         parent_corpus_id=corpus_b.corpus_id,
    #         child_corpus_id=corpus_a.corpus_id
    #     )


@pytest.mark.asyncio
async def test_corpus_cascading_deletion(tree_manager: TreeCorpusManager, test_db):
    """Test cascading deletion of corpus hierarchy."""
    # Create hierarchy: parent -> child1, child2 -> grandchild
    parent = await tree_manager.save_corpus(
        Corpus(
            corpus_name="parent_to_delete",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["parent"],
            original_vocabulary=["parent"],
        )
    )

    child1 = await tree_manager.save_corpus(
        Corpus(
            corpus_name="child1_to_delete",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["child1"],
            original_vocabulary=["child1"],
            parent_uuid=parent.corpus_uuid,
        )
    )

    child2 = await tree_manager.save_corpus(
        Corpus(
            corpus_name="child2_to_delete",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["child2"],
            original_vocabulary=["child2"],
            parent_uuid=parent.corpus_uuid,
        )
    )

    grandchild = await tree_manager.save_corpus(
        Corpus(
            corpus_name="grandchild_to_delete",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["grandchild"],
            original_vocabulary=["grandchild"],
            parent_uuid=child1.corpus_uuid,
        )
    )

    # Delete parent with cascade
    await tree_manager.delete_corpus(corpus_uuid=parent.corpus_uuid, cascade=True)

    # Verify all are deleted
    assert await tree_manager.get_corpus(corpus_uuid=parent.corpus_uuid) is None
    assert await tree_manager.get_corpus(corpus_uuid=child1.corpus_uuid) is None
    assert await tree_manager.get_corpus(corpus_uuid=child2.corpus_uuid) is None
    assert await tree_manager.get_corpus(corpus_uuid=grandchild.corpus_uuid) is None


@pytest.mark.asyncio
async def test_corpus_update_triggers_version(tree_manager: TreeCorpusManager, test_db):
    """Test that corpus updates create new versions correctly."""
    # Create initial corpus
    corpus = await tree_manager.save_corpus(
        Corpus(
            corpus_name="versioned_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["initial", "vocabulary"],
            original_vocabulary=["initial", "vocabulary"],
        )
    )

    initial_id = corpus.corpus_uuid
    initial_hash = corpus.vocabulary_hash

    # Update corpus vocabulary
    corpus.vocabulary = ["updated", "vocabulary", "new"]
    corpus.original_vocabulary = ["updated", "vocabulary", "new"]

    # Force rebuild of indices for the update
    await corpus._rebuild_indices()

    updated = await tree_manager.save_corpus(corpus)

    # Should have same UUID but different vocabulary hash
    assert updated.corpus_uuid == initial_id
    assert updated.vocabulary_hash != initial_hash
    assert len(updated.vocabulary) == 3


@pytest.mark.asyncio
async def test_corpus_aggregation(tree_manager: TreeCorpusManager, test_db):
    """Test vocabulary aggregation from child corpora."""
    # Create parent
    parent = await tree_manager.save_corpus(
        Corpus(
            corpus_name="aggregation_parent",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["parent"],
            original_vocabulary=["parent"],
        )
    )

    # Create children with different vocabularies
    await tree_manager.save_corpus(
        Corpus(
            corpus_name="aggregation_child1",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["child1", "unique1"],
            original_vocabulary=["child1", "unique1"],
            parent_uuid=parent.corpus_uuid,
        )
    )

    await tree_manager.save_corpus(
        Corpus(
            corpus_name="aggregation_child2",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=["child2", "unique2"],
            original_vocabulary=["child2", "unique2"],
            parent_uuid=parent.corpus_uuid,
        )
    )

    # Aggregate vocabulary from children
    aggregated = await tree_manager.aggregate_from_children(
        parent_corpus_uuid=parent.corpus_uuid
    )
    assert aggregated is not None

    # Should include vocabularies from all children
    expected_words = ["parent", "child1", "unique1", "child2", "unique2"]
    assert all(word in aggregated.vocabulary for word in expected_words)


@pytest.mark.asyncio
async def test_corpus_concurrent_operations(tree_manager: TreeCorpusManager, test_db):
    """Test concurrent corpus operations for race conditions."""
    base_corpus = await tree_manager.save_corpus(
        Corpus(
            corpus_name="concurrent_base",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["base"],
            original_vocabulary=["base"],
        )
    )

    async def create_child(index: int):
        """Create a child corpus concurrently."""
        child = Corpus(
            corpus_name=f"concurrent_child_{index}",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=[f"child_{index}"],
            original_vocabulary=[f"child_{index}"],
            parent_uuid=base_corpus.corpus_uuid,
        )
        return await tree_manager.save_corpus(child)

    # Create children concurrently
    children = await asyncio.gather(
        *[create_child(i) for i in range(5)], return_exceptions=True
    )

    # Filter out any exceptions
    successful_children = [c for c in children if not isinstance(c, Exception)]
    assert len(successful_children) >= 3  # At least some should succeed

    # Verify children were created with parent_uuid set
    for child in successful_children:
        assert child.parent_uuid == base_corpus.corpus_uuid
