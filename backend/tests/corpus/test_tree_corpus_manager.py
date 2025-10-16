"""TreeCorpusManager integration tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.caching.models import VersionConfig
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest_asyncio.fixture
async def manager(test_db) -> TreeCorpusManager:
    """Provide an isolated manager for each test."""
    return TreeCorpusManager()


@pytest.mark.asyncio
async def test_save_and_get_roundtrip(manager: TreeCorpusManager) -> None:
    """Corpora persist and round-trip through metadata conversion."""
    created = await manager.save_corpus(
        corpus_name="unit_test",
        content={"vocabulary": ["alpha", "beta"]},
        corpus_type=CorpusType.LEXICON,
        language=Language.ENGLISH,
    )

    assert created is not None
    assert created.corpus_name == "unit_test"
    assert created.vocabulary == ["alpha", "beta"]

    found = await manager.get_corpus(corpus_name="unit_test")
    assert found is not None
    assert found.corpus_name == "unit_test"
    assert found.vocabulary_to_index["alpha"] == 0


@pytest.mark.asyncio
async def test_child_relationships(manager: TreeCorpusManager) -> None:
    """Children attach to parents without rebuilding the tree."""
    parent = await manager.save_corpus(
        corpus_name="parent",
        content={"vocabulary": ["root"]},
        corpus_type=CorpusType.LEXICON,
        language=Language.ENGLISH,
        is_master=True,
    )
    assert parent and parent.corpus_uuid

    child = await manager.save_corpus(
        corpus_name="child",
        content={"vocabulary": ["leaf"]},
        corpus_type=CorpusType.LEXICON,
        language=Language.ENGLISH,
        parent_uuid=parent.corpus_uuid,
    )
    assert child and child.corpus_uuid

    updated_parent = await manager.get_corpus(corpus_uuid=parent.corpus_uuid)
    assert updated_parent is not None
    assert child.corpus_uuid in updated_parent.child_uuids

    aggregated = await manager.aggregate_vocabularies(corpus_uuid=parent.corpus_uuid)
    # Master corpora are containers - only children's vocabulary is aggregated
    assert aggregated == sorted({"leaf"})


@pytest.mark.asyncio
async def test_update_and_delete(manager: TreeCorpusManager) -> None:
    """Updates modify metadata in place and deletion removes versions."""
    corpus = await manager.save_corpus(
        corpus_name="to_update",
        content={"vocabulary": ["one"]},
    )
    assert corpus and corpus.corpus_id
    updated = await manager.update_corpus(
        corpus_id=corpus.corpus_id,
        content={"vocabulary": ["one", "two"]},
        metadata={"is_master": True},
    )
    assert updated is not None
    assert updated.is_master is True
    assert updated.vocabulary == ["one", "two"]

    # Use the updated corpus ID for deletion
    deleted = await manager.delete_corpus(corpus_id=updated.corpus_id)
    assert deleted is True
    assert await manager.get_corpus(corpus_id=updated.corpus_id) is None


@pytest.mark.asyncio
async def test_versioning_for_corpus(manager: TreeCorpusManager) -> None:
    """Saving twice increments stored versions while returning latest."""
    config = VersionConfig()
    saved_once = await manager.save_corpus(
        corpus_name="versioned",
        content={"vocabulary": ["alpha"]},
        config=config,
    )
    assert saved_once and saved_once.corpus_id

    saved_twice = await manager.save_corpus(
        corpus_name="versioned",
        content={"vocabulary": ["alpha", "beta"]},
        corpus_id=saved_once.corpus_id,
        config=VersionConfig(),
    )
    assert saved_twice is not None
    assert saved_twice.vocabulary == ["alpha", "beta"]

    latest = await manager.get_corpus(corpus_name="versioned")
    assert latest is not None
    assert latest.vocabulary == ["alpha", "beta"]
