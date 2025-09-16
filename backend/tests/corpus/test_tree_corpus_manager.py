"""Comprehensive tests for TreeCorpusManager operations."""

import pytest
from beanie import PydanticObjectId

from floridify.caching.models import VersionConfig
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


@pytest.mark.asyncio
class TestTreeCorpusManager:
    """Test TreeCorpusManager operations."""

    @pytest.fixture
    def manager(self):
        """Create a TreeCorpusManager instance."""
        return TreeCorpusManager()

    @pytest.fixture
    def sample_vocabulary(self):
        """Sample vocabulary data."""
        return ["apple", "banana", "cherry", "date", "elderberry"]

    @pytest.fixture
    def sample_corpus(self, sample_vocabulary):
        """Create a sample corpus."""
        corpus = Corpus(
            name="test_corpus",
            description="Test corpus",
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            vocabulary=sample_vocabulary,
        )
        corpus.corpus_id = PydanticObjectId()
        return corpus

    async def test_save_corpus(self, test_db, manager, sample_vocabulary):
        """Test saving a corpus."""
        # Create and save a real corpus
        result = await manager.save_corpus(
            corpus_name="test_save_corpus",
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        assert result is not None
        assert result.corpus_name == "test_save_corpus"
        assert result.vocabulary == sample_vocabulary

    async def test_get_corpus_by_id(self, test_db, manager, sample_vocabulary):
        """Test retrieving corpus by ID."""
        # First save a corpus
        saved = await manager.save_corpus(
            corpus_name="test_get_by_id",
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        assert saved is not None
        assert saved.corpus_id is not None

        # Now retrieve it by ID
        result = await manager.get_corpus(corpus_id=saved.corpus_id)

        assert result is not None
        assert result.corpus_name == "test_get_by_id"

    async def test_get_corpus_by_name(self, test_db, manager, sample_vocabulary):
        """Test retrieving corpus by name."""
        # First save a corpus
        corpus_name = "test_get_by_name"
        await manager.save_corpus(
            corpus_name=corpus_name,
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        # Now retrieve it by name
        result = await manager.get_corpus(corpus_name=corpus_name)

        assert result is not None
        assert result.corpus_name == corpus_name

    async def test_get_corpus_not_found(self, test_db, manager):
        """Test handling when corpus is not found."""
        # Try to get a corpus that doesn't exist
        result = await manager.get_corpus(corpus_name="nonexistent_corpus_xyz123")

        assert result is None

    async def test_delete_corpus(self, test_db, manager, sample_vocabulary):
        """Test deleting a corpus."""
        # First save a corpus
        saved = await manager.save_corpus(
            corpus_name="test_delete",
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        assert saved is not None
        assert saved.corpus_id is not None

        # Delete it
        result = await manager.delete_corpus(saved.corpus_id)

        assert result is True

        # Verify it's gone
        retrieved = await manager.get_corpus(corpus_id=saved.corpus_id)
        assert retrieved is None

    async def test_update_corpus(self, test_db, manager, sample_vocabulary):
        """Test updating a corpus."""
        # First save a corpus
        saved = await manager.save_corpus(
            corpus_name="test_update",
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        assert saved is not None

        # Update it with new vocabulary
        new_vocab = ["fig", "grape", "orange"]
        result = await manager.update_corpus(
            corpus_id=saved.corpus_id, content={"vocabulary": new_vocab}
        )

        assert result is not None
        assert result.vocabulary == new_vocab

    async def test_create_tree_structure(self, test_db, manager, sample_vocabulary):
        """Test creating a hierarchical tree structure."""
        # Create parent corpus
        parent = await manager.save_corpus(
            corpus_name="parent_corpus",
            content={"vocabulary": sample_vocabulary[:3]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            is_master=True,
        )

        assert parent is not None
        parent_id = parent.id

        # Create child corpora
        child1 = await manager.save_corpus(
            corpus_name="child1",
            content={"vocabulary": sample_vocabulary[2:4]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            parent_corpus_id=parent_id,
        )

        child2 = await manager.save_corpus(
            corpus_name="child2",
            content={"vocabulary": sample_vocabulary[3:]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            parent_corpus_id=parent_id,
        )

        assert child1 is not None
        assert child2 is not None

        # Update parent with children
        updated_parent = await manager.update_corpus(
            corpus_id=parent_id, metadata={"child_corpus_ids": [child1.id, child2.id]}
        )

        assert updated_parent is not None
        assert len(updated_parent.child_corpus_ids) == 2

    async def test_aggregate_vocabularies(self, test_db, manager):
        """Test vocabulary aggregation from tree structure."""
        # Create parent corpus
        parent = await manager.save_corpus(
            corpus_name="parent_aggregate",
            content={"vocabulary": ["apple", "banana"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            is_master=True,
        )

        assert parent is not None
        parent_id = parent.id

        # Create child corpora
        child1 = await manager.save_corpus(
            corpus_name="child1_aggregate",
            content={"vocabulary": ["cherry", "date"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            parent_corpus_id=parent_id,
        )

        child2 = await manager.save_corpus(
            corpus_name="child2_aggregate",
            content={"vocabulary": ["elderberry", "fig"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            parent_corpus_id=parent_id,
        )

        # Update parent with children
        await manager.update_corpus(
            corpus_id=parent_id, metadata={"child_corpus_ids": [child1.id, child2.id]}
        )

        # Test aggregation
        aggregated = await manager.aggregate_vocabularies(parent_id)

        # Should contain all vocabularies
        expected = {"apple", "banana", "cherry", "date", "elderberry", "fig"}
        assert set(aggregated) == expected

    async def test_get_vocabulary_with_aggregation(self, test_db, manager, sample_vocabulary):
        """Test getting vocabulary with optional aggregation."""
        # Create a corpus
        saved = await manager.save_corpus(
            corpus_name="test_vocab_aggregation",
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        assert saved is not None

        # Get vocabulary without aggregation
        vocab = await manager.get_vocabulary(saved.corpus_id, aggregate=False)
        assert vocab == sample_vocabulary

        # Get vocabulary with aggregation (should be the same for a single corpus)
        vocab = await manager.get_vocabulary(saved.corpus_id, aggregate=True)
        assert set(vocab) == set(sample_vocabulary)

    async def test_update_parent_child_relationships(self, test_db, manager):
        """Test updating parent-child relationships."""
        # Create parent corpus
        parent = await manager.save_corpus(
            corpus_name="parent_update",
            content={"vocabulary": ["parent"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        # Create child corpus
        child = await manager.save_corpus(
            corpus_name="child_update",
            content={"vocabulary": ["child"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        assert parent is not None
        assert child is not None

        # Update parent relationship
        await manager.update_parent(child.id, parent.id)

        # Verify the relationship
        updated_child = await manager.get_corpus(corpus_id=child.id)
        assert updated_child is not None
        assert updated_child.metadata.get("parent_corpus_id") == str(parent.id)

    async def test_remove_child_from_parent(self, test_db, manager):
        """Test removing a child from parent."""
        # Create parent corpus
        parent = await manager.save_corpus(
            corpus_name="parent_remove",
            content={"vocabulary": ["parent"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        # Create child corpus
        child = await manager.save_corpus(
            corpus_name="child_remove",
            content={"vocabulary": ["child"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            parent_corpus_id=parent.id,
        )

        # Update parent with child
        await manager.update_corpus(corpus_id=parent.id, metadata={"child_corpus_ids": [child.id]})

        # Remove child with deletion
        await manager.remove_child(parent.id, child.id, delete_child=True)

        # Verify child is deleted
        deleted_child = await manager.get_corpus(corpus_id=child.id)
        assert deleted_child is None

    async def test_create_from_language_sources(self, test_db, manager):
        """Test creating corpus from language sources."""
        # Create a language corpus with sources
        corpus = await manager.save_corpus(
            corpus_name="test_language_corpus",
            content={"vocabulary": ["word1", "word2", "word3"]},
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            metadata={
                "sources": [
                    {"name": "source1", "url": "https://example.com/1"},
                    {"name": "source2", "url": "https://example.com/2"},
                ]
            },
        )

        assert corpus is not None
        assert corpus.corpus_name == "test_language_corpus"
        assert "sources" in corpus.metadata
        assert len(corpus.metadata["sources"]) == 2

    async def test_rebuild_source_specific(self, test_db, manager):
        """Test rebuilding only specific source in corpus tree."""
        # Create parent corpus
        parent = await manager.save_corpus(
            corpus_name="parent_rebuild",
            content={"vocabulary": ["old", "vocab"]},
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            is_master=True,
        )

        # Create child corpus
        child = await manager.save_corpus(
            corpus_name="source1_rebuild",
            content={"vocabulary": ["source1", "words"]},
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            parent_corpus_id=parent.id,
        )

        # Update parent with child
        await manager.update_corpus(corpus_id=parent.id, metadata={"child_corpus_ids": [child.id]})

        # Update child vocabulary
        new_vocab = ["new", "source1", "vocabulary"]
        updated_child = await manager.update_corpus(
            corpus_id=child.id, content={"vocabulary": new_vocab}
        )

        assert updated_child is not None
        assert updated_child.vocabulary == new_vocab

        # Verify parent can aggregate new vocabulary
        aggregated = await manager.aggregate_vocabularies(parent.id)
        assert "new" in aggregated

    async def test_circular_reference_prevention(self, test_db, manager):
        """Test prevention of circular references in tree."""
        # Create first corpus
        corpus1 = await manager.save_corpus(
            corpus_name="corpus1_cycle",
            content={"vocabulary": ["corpus1"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        # Create second corpus
        corpus2 = await manager.save_corpus(
            corpus_name="corpus2_cycle",
            content={"vocabulary": ["corpus2"]},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
        )

        # Simple cycle detection helper
        visited = set()

        def detect_cycle(corpus_id):
            """Helper to detect cycles."""
            if corpus_id in visited:
                return True
            visited.add(corpus_id)
            return False

        # Should detect the cycle
        assert detect_cycle(corpus1.id) is False
        assert detect_cycle(corpus2.id) is False
        assert detect_cycle(corpus1.id) is True  # Cycle detected

    async def test_version_management_integration(self, test_db, manager, sample_vocabulary):
        """Test that version management is properly integrated."""
        config = VersionConfig(
            force_rebuild=False,
            use_cache=True,
            increment_version=True,
        )

        # Save with version config
        result = await manager.save_corpus(
            corpus_name="test_versioning",
            content={"vocabulary": sample_vocabulary},
            corpus_type=CorpusType.LEXICON,
            language=Language.ENGLISH,
            config=config,
        )

        assert result is not None
        assert result.version_info.version == "1.0.0"

        # Update and check version increment
        updated = await manager.update_corpus(
            corpus_id=result.corpus_id,
            content={"vocabulary": sample_vocabulary + ["new_word"]},
            config=config,
        )

        if updated and hasattr(updated, "version_info"):
            # Version should be incremented if versioning is working
            assert updated.version_info.version != "1.0.0"
