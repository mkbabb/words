"""Comprehensive cascade deletion tests for Corpus and Index documents.

Tests verify that deleting a Corpus properly cascades to all dependent
SearchIndex, TrieIndex, and SemanticIndex documents, preventing orphaned indices.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.caching.manager import get_version_manager
from floridify.caching.models import ResourceType
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.search.models import SearchIndex, TrieIndex
from floridify.search.semantic.models import SemanticIndex


class TestCascadeDeletion:
    """Test cascade deletion for all Document classes to prevent orphaned indices."""

    @pytest_asyncio.fixture
    async def tree_manager(self, test_db) -> TreeCorpusManager:
        """Create a tree corpus manager."""
        return TreeTreeCorpusManager()

    @pytest_asyncio.fixture
    async def test_corpus(self, tree_manager: TreeCorpusManager) -> Corpus:
        """Create a test corpus with vocabulary."""
        vocabulary = ["apple", "banana", "cherry", "date", "elderberry"]
        corpus = await Corpus.create(
            corpus_name="cascade_test_corpus",
            vocabulary=vocabulary,
            language=Language.ENGLISH,
            semantic=False,  # Start without semantic index
        )
        await corpus.save()
        return corpus

    @pytest.mark.asyncio
    async def test_corpus_deletion_cascades_to_search_index(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test that deleting a Corpus cascades to SearchIndex."""
        # Create a SearchIndex for the corpus
        search_index = await SearchIndex.create(
            corpus=test_corpus,
            semantic=False,  # No semantic index for this test
        )
        await search_index.save()

        # Verify SearchIndex exists
        retrieved_search = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert retrieved_search is not None
        assert retrieved_search.corpus_uuid == test_corpus.corpus_uuid

        # Delete the corpus (should cascade to SearchIndex)
        await test_corpus.delete()

        # Verify SearchIndex is deleted
        deleted_search = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted_search is None

    @pytest.mark.asyncio
    async def test_search_index_deletion_cascades_to_trie_index(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test that deleting a SearchIndex cascades to TrieIndex."""
        # Create TrieIndex
        trie_index = await TrieIndex.create(corpus=test_corpus)
        await trie_index.save()

        # Create SearchIndex that references the TrieIndex
        search_index = await SearchIndex.create(corpus=test_corpus, semantic=False)
        search_index.trie_index_id = trie_index.index_id
        search_index.has_trie = True
        await search_index.save()

        # Verify both exist
        retrieved_trie = await TrieIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert retrieved_trie is not None

        retrieved_search = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert retrieved_search is not None

        # Delete SearchIndex (should cascade to TrieIndex)
        await search_index.delete()

        # Verify both are deleted
        deleted_trie = await TrieIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted_trie is None

        deleted_search = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted_search is None

    @pytest.mark.asyncio
    async def test_search_index_deletion_cascades_to_semantic_index(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test that deleting a SearchIndex cascades to SemanticIndex."""
        # Create SemanticIndex
        semantic_index = await SemanticIndex.create(
            corpus=test_corpus,
            model_name="all-MiniLM-L6-v2",
        )
        await semantic_index.save()

        # Create SearchIndex that references the SemanticIndex
        search_index = await SearchIndex.create(
            corpus=test_corpus,
            semantic=True,
            semantic_model="all-MiniLM-L6-v2",
        )
        search_index.semantic_index_id = semantic_index.index_id
        search_index.has_semantic = True
        await search_index.save()

        # Verify both exist
        retrieved_semantic = await SemanticIndex.get(
            corpus_uuid=test_corpus.corpus_uuid,
            model_name="all-MiniLM-L6-v2",
        )
        assert retrieved_semantic is not None

        retrieved_search = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert retrieved_search is not None

        # Delete SearchIndex (should cascade to SemanticIndex)
        await search_index.delete()

        # Verify both are deleted
        deleted_semantic = await SemanticIndex.get(
            corpus_uuid=test_corpus.corpus_uuid,
            model_name="all-MiniLM-L6-v2",
        )
        assert deleted_semantic is None

        deleted_search = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted_search is None

    @pytest.mark.asyncio
    async def test_full_cascade_deletion_all_indices(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test complete cascade: Corpus → SearchIndex → (TrieIndex, SemanticIndex)."""
        # Create TrieIndex
        trie_index = await TrieIndex.create(corpus=test_corpus)
        await trie_index.save()

        # Create SemanticIndex
        semantic_index = await SemanticIndex.create(
            corpus=test_corpus,
            model_name="all-MiniLM-L6-v2",
        )
        await semantic_index.save()

        # Create SearchIndex that references both
        search_index = await SearchIndex.create(
            corpus=test_corpus,
            semantic=True,
            semantic_model="all-MiniLM-L6-v2",
        )
        search_index.trie_index_id = trie_index.index_id
        search_index.has_trie = True
        search_index.semantic_index_id = semantic_index.index_id
        search_index.has_semantic = True
        await search_index.save()

        # Verify all exist
        assert await TrieIndex.get(corpus_uuid=test_corpus.corpus_uuid) is not None
        assert (
            await SemanticIndex.get(
                corpus_uuid=test_corpus.corpus_uuid,
                model_name="all-MiniLM-L6-v2",
            )
            is not None
        )
        assert await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid) is not None

        # Delete the corpus (should cascade to all indices)
        await test_corpus.delete()

        # Verify all are deleted
        assert await TrieIndex.get(corpus_uuid=test_corpus.corpus_uuid) is None
        assert (
            await SemanticIndex.get(
                corpus_uuid=test_corpus.corpus_uuid,
                model_name="all-MiniLM-L6-v2",
            )
            is None
        )
        assert await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid) is None

    @pytest.mark.asyncio
    async def test_trie_index_deletion_standalone(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test that TrieIndex can be deleted independently."""
        # Create TrieIndex
        trie_index = await TrieIndex.create(corpus=test_corpus)
        await trie_index.save()

        # Verify it exists
        retrieved = await TrieIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert retrieved is not None
        assert retrieved.corpus_uuid == test_corpus.corpus_uuid

        # Delete it
        await trie_index.delete()

        # Verify it's deleted
        deleted = await TrieIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_semantic_index_deletion_standalone(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test that SemanticIndex can be deleted independently."""
        # Create SemanticIndex
        semantic_index = await SemanticIndex.create(
            corpus=test_corpus,
            model_name="all-MiniLM-L6-v2",
        )
        await semantic_index.save()

        # Verify it exists
        retrieved = await SemanticIndex.get(
            corpus_uuid=test_corpus.corpus_uuid,
            model_name="all-MiniLM-L6-v2",
        )
        assert retrieved is not None
        assert retrieved.corpus_uuid == test_corpus.corpus_uuid

        # Delete it
        await semantic_index.delete()

        # Verify it's deleted
        deleted = await SemanticIndex.get(
            corpus_uuid=test_corpus.corpus_uuid,
            model_name="all-MiniLM-L6-v2",
        )
        assert deleted is None

    @pytest.mark.asyncio
    async def test_partial_deletion_missing_trie_index(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test deletion when TrieIndex reference exists but index is missing."""
        # Create SearchIndex with trie reference but no actual TrieIndex
        from beanie import PydanticObjectId

        search_index = await SearchIndex.create(corpus=test_corpus, semantic=False)
        search_index.has_trie = True
        search_index.trie_index_id = PydanticObjectId()  # Fake reference
        await search_index.save()

        # Delete should succeed even though TrieIndex doesn't exist
        await search_index.delete()

        # Verify SearchIndex is deleted
        deleted = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_partial_deletion_missing_semantic_index(
        self, tree_manager: TreeCorpusManager, test_corpus: Corpus, test_db
    ):
        """Test deletion when SemanticIndex reference exists but index is missing."""
        # Create SearchIndex with semantic reference but no actual SemanticIndex
        from beanie import PydanticObjectId

        search_index = await SearchIndex.create(
            corpus=test_corpus,
            semantic=True,
            semantic_model="all-MiniLM-L6-v2",
        )
        search_index.has_semantic = True
        search_index.semantic_index_id = PydanticObjectId()  # Fake reference
        await search_index.save()

        # Delete should succeed even though SemanticIndex doesn't exist
        await search_index.delete()

        # Verify SearchIndex is deleted
        deleted = await SearchIndex.get(corpus_uuid=test_corpus.corpus_uuid)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_no_orphaned_documents_after_corpus_deletion(
        self, tree_manager: TreeCorpusManager, test_db
    ):
        """Verify no orphaned documents remain in MongoDB after corpus deletion."""
        # Create corpus with all indices
        vocabulary = ["test", "word", "list"]
        corpus = await Corpus.create(
            corpus_name="orphan_test_corpus",
            vocabulary=vocabulary,
            language=Language.ENGLISH,
            semantic=False,
        )
        await corpus.save()

        corpus_id = corpus.corpus_id

        # Create all indices
        trie_index = await TrieIndex.create(corpus=corpus)
        await trie_index.save()

        semantic_index = await SemanticIndex.create(
            corpus=corpus,
            model_name="all-MiniLM-L6-v2",
        )
        await semantic_index.save()

        search_index = await SearchIndex.create(
            corpus=corpus,
            semantic=True,
            semantic_model="all-MiniLM-L6-v2",
        )
        search_index.trie_index_id = trie_index.index_id
        search_index.has_trie = True
        search_index.semantic_index_id = semantic_index.index_id
        search_index.has_semantic = True
        await search_index.save()

        # Delete the corpus
        await corpus.delete()

        # Verify no documents remain for this corpus_id
        vm = get_version_manager()

        # Check Corpus metadata
        corpus_metadata = await vm.get_latest(
            resource_id=corpus.corpus_name,
            resource_type=ResourceType.CORPUS,
        )
        assert corpus_metadata is None

        # Check SearchIndex metadata
        search_metadata = await vm.get_latest(
            resource_id=f"{corpus_id!s}:search",
            resource_type=ResourceType.SEARCH,
        )
        assert search_metadata is None

        # Check TrieIndex metadata
        trie_metadata = await vm.get_latest(
            resource_id=f"{corpus_id!s}:trie",
            resource_type=ResourceType.TRIE,
        )
        assert trie_metadata is None

        # Check SemanticIndex metadata
        semantic_metadata = await vm.get_latest(
            resource_id=f"{corpus_id!s}:semantic:all-MiniLM-L6-v2",
            resource_type=ResourceType.SEMANTIC,
        )
        assert semantic_metadata is None

    @pytest.mark.asyncio
    async def test_deletion_error_handling_corpus_without_id(
        self, tree_manager: TreeCorpusManager, test_db
    ):
        """Test that deletion fails gracefully for corpus without ID."""
        corpus = Corpus(
            corpus_name="no_id_corpus",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=["test"],
            original_vocabulary=["test"],
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="corpus_id"):
            await corpus.delete()

    @pytest.mark.asyncio
    async def test_deletion_error_handling_search_index_without_id(
        self, tree_manager: TreeCorpusManager, test_db
    ):
        """Test that deletion fails gracefully for SearchIndex without ID."""
        from beanie import PydanticObjectId

        search_index = SearchIndex(
            corpus_uuid="invalid-uuid",
            corpus_name="invalid",
            vocabulary_hash="",
        )
        search_index.corpus_uuid = None  # type: ignore

        # Should raise ValueError
        with pytest.raises(ValueError, match="corpus_uuid"):
            await search_index.delete()

    @pytest.mark.asyncio
    async def test_multiple_corpora_deletion_isolation(
        self, tree_manager: TreeCorpusManager, test_db
    ):
        """Test that deleting one corpus doesn't affect others."""
        # Create two separate corpora
        corpus1 = await Corpus.create(
            corpus_name="corpus_1",
            vocabulary=["one", "two"],
            language=Language.ENGLISH,
            semantic=False,
        )
        await corpus1.save()

        corpus2 = await Corpus.create(
            corpus_name="corpus_2",
            vocabulary=["three", "four"],
            language=Language.ENGLISH,
            semantic=False,
        )
        await corpus2.save()

        # Create indices for both
        search1 = await SearchIndex.create(corpus=corpus1, semantic=False)
        await search1.save()

        search2 = await SearchIndex.create(corpus=corpus2, semantic=False)
        await search2.save()

        # Delete corpus1
        await corpus1.delete()

        # Verify corpus1 and its index are deleted
        assert await Corpus.get(corpus_uuid=corpus1.corpus_uuid) is None
        assert await SearchIndex.get(corpus_uuid=corpus1.corpus_uuid) is None

        # Verify corpus2 and its index still exist
        assert await Corpus.get(corpus_uuid=corpus2.corpus_uuid) is not None
        assert await SearchIndex.get(corpus_uuid=corpus2.corpus_uuid) is not None

        # Clean up
        await corpus2.delete()
