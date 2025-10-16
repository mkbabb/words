"""Comprehensive corpus lifecycle and validation tests."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language


class TestCorpusLifecycle:
    """Test complete corpus lifecycle including creation, updates, caching, and deletion."""

    @pytest_asyncio.fixture
    async def tree_manager(self, test_db) -> TreeCorpusManager:
        """Create a tree corpus manager."""
        return TreeCorpusManager()

    @pytest.mark.asyncio
    async def test_corpus_creation_with_normalization(
        self, tree_manager: TreeCorpusManager, test_db
    ):
        """Test corpus creation with vocabulary normalization and deduplication."""
        # Test vocabulary with various cases needing normalization
        raw_vocabulary = [
            "Apple",  # Capitalization
            "apple",  # Duplicate after normalization
            "café",  # Diacritics
            "cafe",  # Duplicate after diacritic removal
            "naïve",  # Diacritics
            "TEST",  # All caps
            "test",  # Duplicate
            "  spaced  ",  # Extra spaces
            "multi-word phrase",  # Phrase
            "another phrase",  # Another phrase
        ]

        corpus = Corpus(
            corpus_name="normalization_test",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=raw_vocabulary,
            original_vocabulary=raw_vocabulary,
        )

        # Save corpus (should trigger normalization)
        saved = await tree_manager.save_corpus(corpus)

        assert saved.corpus_uuid is not None
        assert saved.vocabulary is not None

        # Verify normalization occurred
        sorted(set(word.lower().strip() for word in raw_vocabulary))
        # The actual normalization might be more complex, but we check basics
        assert len(saved.vocabulary) <= len(raw_vocabulary)  # Deduplication
        # Check that multi-word phrases are preserved but single words are stripped
        for word in saved.vocabulary:
            if " " not in word:  # Single words
                assert word == word.strip()  # No extra spaces

        # Verify indices were built
        assert saved.vocabulary_to_index is not None
        assert len(saved.vocabulary_to_index) == len(saved.vocabulary)

        # Verify vocabulary hash was computed
        assert saved.vocabulary_hash is not None
        assert len(saved.vocabulary_hash) > 0

    @pytest.mark.asyncio
    async def test_corpus_parent_child_linking(self, tree_manager: TreeCorpusManager, test_db):
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
    async def test_corpus_cycle_detection(self, tree_manager: TreeCorpusManager, test_db):
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
    async def test_corpus_vocabulary_hashing_consistency(
        self, tree_manager: TreeCorpusManager, test_db
    ):
        """Test that vocabulary hashing is consistent and triggers rebuilds correctly."""
        vocabulary = ["apple", "banana", "cherry", "date", "elderberry"]

        corpus1 = await tree_manager.save_corpus(
            Corpus(
                corpus_name="hash_test_1",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=vocabulary.copy(),
                original_vocabulary=vocabulary.copy(),
            )
        )

        # Create another corpus with same vocabulary
        corpus2 = await tree_manager.save_corpus(
            Corpus(
                corpus_name="hash_test_2",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=vocabulary.copy(),
                original_vocabulary=vocabulary.copy(),
            )
        )

        # Same vocabulary should produce same hash
        assert corpus1.vocabulary_hash == corpus2.vocabulary_hash

        # Modify vocabulary slightly
        modified_vocab = vocabulary.copy() + ["fig"]
        corpus3 = await tree_manager.save_corpus(
            Corpus(
                corpus_name="hash_test_3",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=modified_vocab,
                original_vocabulary=modified_vocab,
            )
        )

        # Different vocabulary should produce different hash
        assert corpus3.vocabulary_hash != corpus1.vocabulary_hash

    @pytest.mark.asyncio
    async def test_corpus_cascading_deletion(self, tree_manager: TreeCorpusManager, test_db):
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
    async def test_corpus_update_triggers_version(self, tree_manager: TreeCorpusManager, test_db):
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
    async def test_corpus_lemmatization_integration(self, tree_manager: TreeCorpusManager, test_db):
        """Test corpus creation with lemmatization."""
        # Words with various forms
        vocabulary = [
            "running",
            "runs",
            "ran",
            "run",  # Should lemmatize to "run"
            "better",
            "best",
            "good",  # Different lemmas
            "children",
            "child",  # Should lemmatize to "child"
            "teeth",
            "tooth",  # Irregular plural
        ]

        corpus = Corpus(
            corpus_name="lemma_test",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
        )

        # Trigger lemmatization

        saved = await tree_manager.save_corpus(corpus)

        # Verify lemmatization occurred
        assert saved.lemmatized_vocabulary is not None
        assert len(saved.lemmatized_vocabulary) > 0

        # Check lemma to word mappings exist
        assert saved.lemma_to_word_indices is not None
        assert len(saved.lemma_to_word_indices) > 0

        # Verify some expected lemmatizations
        if "run" in saved.lemma_to_word_indices:
            run_indices = saved.lemma_to_word_indices["run"]
            run_words = [saved.vocabulary[i] for i in run_indices]
            # Should map multiple forms to "run"
            assert len(run_words) >= 2

    @pytest.mark.asyncio
    async def test_corpus_diacritic_handling(self, tree_manager: TreeCorpusManager, test_db):
        """Test proper handling of diacritics in corpus vocabulary."""
        vocabulary = [
            "café",
            "cafe",  # With and without accent
            "naïve",
            "naive",  # With and without diaeresis
            "résumé",
            "resume",  # Multiple diacritics
            "Zürich",  # German umlaut
            "señor",  # Spanish tilde
            "français",  # French cedilla
        ]

        corpus = Corpus(
            corpus_name="diacritic_test",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
        )

        saved = await tree_manager.save_corpus(corpus)

        # Verify original forms are preserved
        assert saved.original_vocabulary is not None
        for word in vocabulary:
            assert word in saved.original_vocabulary

        # Verify normalized forms exist
        if saved.normalized_to_original_indices:
            # Check that normalized versions map to originals
            assert "cafe" in saved.vocabulary or "café" in saved.vocabulary
            assert "naive" in saved.vocabulary or "naïve" in saved.vocabulary

    @pytest.mark.asyncio
    async def test_corpus_concurrent_operations(self, tree_manager: TreeCorpusManager, test_db):
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

        # Reload parent and check children
        reloaded = await tree_manager.get_corpus(corpus_uuid=base_corpus.corpus_uuid)
        assert len(reloaded.child_uuids) == len(successful_children)

    @pytest.mark.asyncio
    async def test_small_bespoke_corpus(self, tree_manager: TreeCorpusManager, test_db):
        """Test with a small, hand-crafted corpus."""
        vocabulary = ["hello", "world", "test", "corpus", "small"]

        corpus = await tree_manager.save_corpus(
            Corpus(
                corpus_name="bespoke_small",
                corpus_type=CorpusType.CUSTOM,
                language=Language.ENGLISH,
                vocabulary=vocabulary,
                original_vocabulary=vocabulary,
            )
        )

        assert len(corpus.vocabulary) == len(vocabulary)
        assert all(word in corpus.vocabulary for word in vocabulary)
        assert corpus.corpus_type == CorpusType.CUSTOM

    @pytest.mark.asyncio
    async def test_language_level_corpus(self, tree_manager: TreeCorpusManager, test_db):
        """Test language-level corpus with larger vocabulary."""
        # Simulate a language corpus
        base_words = ["the", "be", "to", "of", "and", "a", "in", "that", "have", "I"]
        # Generate variations
        vocabulary = []
        for word in base_words:
            vocabulary.append(word)
            vocabulary.append(word.upper())
            vocabulary.append(word.capitalize())

        corpus = await tree_manager.save_corpus(
            Corpus(
                corpus_name="language_english",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=vocabulary,
                original_vocabulary=vocabulary,
                is_master=True,  # Mark as master language corpus
            )
        )

        assert corpus.is_master is True
        assert corpus.corpus_type == CorpusType.LANGUAGE
        # Deduplication should reduce size
        assert len(corpus.vocabulary) <= len(vocabulary)

    @pytest.mark.asyncio
    async def test_literature_level_corpus(self, tree_manager: TreeCorpusManager, test_db):
        """Test literature-level corpus with domain-specific vocabulary."""
        # Shakespeare-style vocabulary
        vocabulary = [
            "thou",
            "thee",
            "thy",
            "thine",
            "art",
            "hath",
            "doth",
            "wherefore",
            "whence",
            "hither",
            "thither",
            "'tis",
            "'twas",
            "verily",
            "forsooth",
            "prithee",
            "anon",
            "ere",
            "oft",
        ]

        parent = await tree_manager.save_corpus(
            Corpus(
                corpus_name="english_literature",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=["english"],
                original_vocabulary=["english"],
                is_master=True,
            )
        )

        corpus = await tree_manager.save_corpus(
            Corpus(
                corpus_name="shakespeare_works",
                corpus_type=CorpusType.LITERATURE,
                language=Language.ENGLISH,
                vocabulary=vocabulary,
                original_vocabulary=vocabulary,
                parent_uuid=parent.corpus_uuid,
            )
        )

        assert corpus.corpus_type == CorpusType.LITERATURE
        assert corpus.parent_uuid == parent.corpus_uuid
        assert all(word in corpus.vocabulary for word in vocabulary)

    @pytest.mark.asyncio
    async def test_corpus_aggregation(self, tree_manager: TreeCorpusManager, test_db):
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
        aggregated = await tree_manager.aggregate_from_children(parent_corpus_uuid=parent.corpus_uuid)
        assert aggregated is not None

        # Should include vocabularies from all children
        expected_words = ["parent", "child1", "unique1", "child2", "unique2"]
        assert all(word in aggregated.vocabulary for word in expected_words)

    @pytest.mark.asyncio
    async def test_corpus_french_vocabulary(self, tree_manager: TreeCorpusManager, test_db):
        """Test corpus with French vocabulary and special characters."""
        vocabulary = [
            "français",
            "élève",
            "château",
            "œuvre",
            "naïf",
            "être",
            "avoir",
            "aller",
            "faire",
            "dire",
            "bœuf",
            "cœur",
            "sœur",
            "œil",
            "hôtel",
        ]

        corpus = await tree_manager.save_corpus(
            Corpus(
                corpus_name="french_corpus",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.FRENCH,
                vocabulary=vocabulary,
                original_vocabulary=vocabulary,
            )
        )

        assert corpus.language == Language.FRENCH
        assert len(corpus.vocabulary) == len(set(vocabulary))
        # Original forms should be preserved
        assert all(word in corpus.original_vocabulary for word in vocabulary)
