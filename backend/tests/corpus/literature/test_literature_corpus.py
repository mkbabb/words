"""Comprehensive tests for LiteratureCorpus with real MongoDB integration."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from floridify.corpus.literature.core import LiteratureCorpus
from floridify.corpus.manager import TreeCorpusManager, get_tree_corpus_manager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.models.literature import AuthorInfo, Genre, Period
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.models import LiteratureEntry, LiteratureSource


class TestLiteratureCorpus:
    """Test LiteratureCorpus functionality with real MongoDB."""

    @pytest.mark.asyncio
    async def test_literature_corpus_creation(self, test_db):
        """Test creating a LiteratureCorpus with MongoDB persistence."""
        manager = get_tree_corpus_manager()

        corpus = LiteratureCorpus(
            corpus_name="shakespeare_works",
            language=Language.ENGLISH,
            vocabulary=["thou", "thee", "thy", "thine"],
            original_vocabulary=["thou", "thee", "thy", "thine"],
            corpus_type=CorpusType.LITERATURE,
        )

        # Save to MongoDB via manager
        saved = await manager.save_corpus(corpus)

        assert saved.corpus_id is not None
        assert saved.corpus_name == "shakespeare_works"
        assert saved.corpus_type == CorpusType.LITERATURE
        assert len(saved.vocabulary) == 4
        assert "thou" in saved.vocabulary

        # Verify retrieval from MongoDB
        loaded = await manager.get_corpus(corpus_uuid=saved.corpus_uuid)
        assert loaded is not None
        assert loaded.corpus_name == "shakespeare_works"
        assert loaded.vocabulary == saved.vocabulary

    @pytest.mark.asyncio
    async def test_add_literature_source(self, test_db):
        """Test adding a literature work as a child corpus."""
        manager = get_tree_corpus_manager()

        # Create parent literature corpus
        parent = LiteratureCorpus(
            corpus_name="english_literature",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
            is_master=True,
        )
        saved = await manager.save_corpus(parent)
        parent.corpus_id = saved.corpus_id
        parent.corpus_uuid = saved.corpus_uuid

        # Create mock connector
        mock_connector = AsyncMock(spec=GutenbergConnector)
        mock_entry = LiteratureEntry(
            title="Hamlet",
            author=AuthorInfo(
                name="Shakespeare, William",
                birth_year=1564,
                death_year=1616,
                nationality="English",
                period=Period.RENAISSANCE,
                primary_genre=Genre.DRAMA,
            ),
            text="To be or not to be, that is the question",
            gutenberg_id="1524",
        )
        mock_connector.fetch_source.return_value = mock_entry

        # Create literature source
        source = LiteratureSource(
            name="Hamlet",
            author=AuthorInfo(
                name="Shakespeare, William",
                period=Period.RENAISSANCE,
                primary_genre=Genre.DRAMA,
            ),
            genre=Genre.DRAMA,
            period=Period.RENAISSANCE,
            language=Language.ENGLISH,
            url="1524",
        )

        # Add source to corpus
        child_id = await parent.add_literature_source(source, connector=mock_connector)

        assert child_id is not None
        mock_connector.fetch_source.assert_called_once_with(source)

        # Verify child corpus was created
        children = await manager.get_children(parent.corpus_id)
        assert len(children) == 1

        child = children[0]
        assert child.corpus_type == CorpusType.LITERATURE

    @pytest.mark.asyncio
    async def test_add_multiple_works(self, test_db):
        """Test adding multiple literature works to a corpus."""
        manager = get_tree_corpus_manager()

        # Create master corpus
        master = LiteratureCorpus(
            corpus_name="shakespeare_collection",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
            is_master=True,
        )
        saved = await manager.save_corpus(master)
        master.corpus_id = saved.corpus_id
        master.corpus_uuid = saved.corpus_uuid

        # Mock connector
        mock_connector = AsyncMock(spec=GutenbergConnector)

        # Add multiple works
        works = [
            ("Hamlet", 1524, "To be or not to be"),
            ("Romeo and Juliet", 1513, "Wherefore art thou Romeo"),
            ("Macbeth", 1533, "Out damned spot"),
        ]

        child_ids = []
        for title, gutenberg_id, text in works:
            mock_entry = LiteratureEntry(
                title=title,
                author=AuthorInfo(
                    name="Shakespeare, William",
                    period=Period.RENAISSANCE,
                    primary_genre=Genre.DRAMA,
                ),
                text=text,
                gutenberg_id=str(gutenberg_id),
            )
            mock_connector.fetch_source.return_value = mock_entry

            source = LiteratureSource(
                name=title,
                author=AuthorInfo(
                    name="Shakespeare, William",
                    period=Period.RENAISSANCE,
                    primary_genre=Genre.DRAMA,
                ),
                genre=Genre.DRAMA,
                language=Language.ENGLISH,
                url=str(gutenberg_id),
            )

            child_id = await master.add_literature_source(source, connector=mock_connector)
            if child_id:
                child_ids.append(child_id)

        assert len(child_ids) == 3

        # Verify all children were added
        children = await manager.get_children(master.corpus_id)
        assert len(children) == 3

    @pytest.mark.asyncio
    async def test_literature_corpus_with_tree_manager(self, test_db):
        """Test LiteratureCorpus integration with TreeCorpusManager."""
        manager = get_tree_corpus_manager()

        # Create root literature corpus
        root = LiteratureCorpus(
            corpus_name="world_literature",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
            is_master=True,
        )
        root = await manager.save_corpus(root)

        # Create author corpus
        author_corpus = LiteratureCorpus(
            corpus_name="shakespeare",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
            parent_uuid=root.corpus_uuid,
        )
        author_corpus = await manager.save_corpus(author_corpus)

        # Create work corpus
        work_corpus = LiteratureCorpus(
            corpus_name="hamlet",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_uuid=author_corpus.corpus_uuid,
            vocabulary=["prince", "denmark", "ghost", "revenge"],
            original_vocabulary=["prince", "denmark", "ghost", "revenge"],
        )
        work_corpus = await manager.save_corpus(work_corpus)

        # Verify tree structure
        tree = await manager.get_tree(root.corpus_id)
        assert tree is not None
        assert len(tree["children"]) == 1  # author_corpus
        assert len(tree["children"][0]["children"]) == 1  # work_corpus

    @pytest.mark.asyncio
    async def test_literature_corpus_vocabulary_aggregation(self, test_db):
        """Test vocabulary aggregation across literature works."""
        manager = get_tree_corpus_manager()

        # Create parent corpus
        parent = LiteratureCorpus(
            corpus_name="poetry_collection",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
            is_master=True,
        )
        parent = await manager.save_corpus(parent)

        # Create child corpora with vocabularies
        poem1 = LiteratureCorpus(
            corpus_name="poem1",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_uuid=parent.corpus_uuid,
            vocabulary=["rose", "red", "love", "sweet"],
            original_vocabulary=["rose", "red", "love", "sweet"],
        )
        await manager.save_corpus(poem1)

        poem2 = LiteratureCorpus(
            corpus_name="poem2",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_uuid=parent.corpus_uuid,
            vocabulary=["violet", "blue", "love", "true"],
            original_vocabulary=["violet", "blue", "love", "true"],
        )
        await manager.save_corpus(poem2)

        # Aggregate vocabulary
        await manager.aggregate_vocabulary(parent.corpus_id)

        # Reload parent
        reloaded = await manager.get_corpus(corpus_uuid=parent.corpus_uuid)
        assert reloaded is not None

        # Check aggregated vocabulary
        aggregated = set(reloaded.vocabulary)
        expected = {"rose", "red", "love", "sweet", "violet", "blue", "true"}
        assert aggregated == expected

    @pytest.mark.asyncio
    async def test_literature_corpus_with_metadata(self, test_db):
        """Test LiteratureCorpus with rich metadata."""
        manager = get_tree_corpus_manager()

        corpus = LiteratureCorpus(
            corpus_name="victorian_novels",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
        )

        # Add metadata
        corpus.metadata.update(
            {
                "period": Period.VICTORIAN.value,
                "genres": [Genre.NOVEL.value, Genre.ROMANCE.value],
                "authors": ["Charles Dickens", "Jane Austen", "Charlotte Bronte"],
                "date_range": "1837-1901",
                "characteristics": ["social realism", "industrialization", "class conflict"],
            },
        )

        saved = await manager.save_corpus(corpus)

        # Verify metadata persistence
        loaded = await manager.get_corpus(corpus_uuid=saved.corpus_uuid)
        assert loaded is not None
        assert loaded.metadata["period"] == Period.VICTORIAN.value
        assert Genre.NOVEL.value in loaded.metadata["genres"]
        assert "Charles Dickens" in loaded.metadata["authors"]
        assert loaded.metadata["date_range"] == "1837-1901"

    @pytest.mark.asyncio
    async def test_literature_corpus_error_handling(self, test_db):
        """Test error handling in literature corpus operations."""
        manager = get_tree_corpus_manager()

        corpus = LiteratureCorpus(
            corpus_name="test_errors",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
        )
        saved = await manager.save_corpus(corpus)
        corpus.corpus_id = saved.corpus_id
        corpus.corpus_uuid = saved.corpus_uuid

        # Mock connector that fails
        mock_connector = AsyncMock(spec=GutenbergConnector)
        mock_connector.fetch_source.return_value = None  # Simulate fetch failure

        source = LiteratureSource(
            name="NonExistentWork",
            language=Language.ENGLISH,
            url="invalid_id",
        )

        # Should handle failure gracefully
        child_id = await corpus.add_literature_source(source, connector=mock_connector)
        assert child_id is None

        # Verify no child was added
        children = await manager.get_children(corpus.corpus_id)
        assert len(children) == 0

    @pytest.mark.asyncio
    async def test_literature_corpus_batch_operations(self, test_db):
        """Test batch operations on literature corpora."""
        manager = get_tree_corpus_manager()

        # Create multiple corpora
        corpora = []
        for i in range(5):
            corpus = LiteratureCorpus(
                corpus_name=f"work_{i}",
                language=Language.ENGLISH,
                corpus_type=CorpusType.LITERATURE,
                vocabulary=[f"word_{i}", f"unique_{i}"],
                original_vocabulary=[f"word_{i}", f"unique_{i}"],
            )
            corpus.metadata["work_number"] = i
            saved = await manager.save_corpus(corpus)
            corpora.append(saved)

        # Batch retrieval by UUIDs
        uuids = [c.corpus_uuid for c in corpora]
        loaded = await manager.get_corpora_by_uuids(uuids)

        assert len(loaded) == 5

    @pytest.mark.asyncio
    async def test_literature_corpus_search_integration(self, test_db):
        """Test literature corpus integration with search capabilities."""
        manager = get_tree_corpus_manager()

        corpus = LiteratureCorpus(
            corpus_name="searchable_literature",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[
                "love",
                "hate",
                "passion",
                "sorrow",
                "joy",
                "melancholy",
                "desire",
                "longing",
            ],
            original_vocabulary=[
                "love",
                "hate",
                "passion",
                "sorrow",
                "joy",
                "melancholy",
                "desire",
                "longing",
            ],
        )
        corpus.metadata.update(
            {
                "genre": Genre.POETRY.value,
                "themes": ["emotion", "human nature"],
                "searchable": True,
                "semantic_enabled": True,
            },
        )
        saved = await manager.save_corpus(corpus)

        # Verify metadata and vocabulary
        loaded = await manager.get_corpus(corpus_uuid=saved.corpus_uuid)
        assert loaded is not None
        assert loaded.metadata["searchable"] is True
        assert loaded.metadata.get("semantic_enabled", False) is True

        # Vocabulary should be available for search
        assert "love" in loaded.vocabulary
        assert "melancholy" in loaded.vocabulary

    @pytest.mark.asyncio
    async def test_literature_corpus_parallel_operations(self, test_db):
        """Test parallel operations on literature corpora."""
        manager = get_tree_corpus_manager()

        # Create parent
        parent = LiteratureCorpus(
            corpus_name="parallel_parent",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            original_vocabulary=[],
            is_master=True,
        )
        parent = await manager.save_corpus(parent)

        # Create children in parallel
        async def create_child(index: int):
            child = LiteratureCorpus(
                corpus_name=f"parallel_child_{index}",
                language=Language.ENGLISH,
                corpus_type=CorpusType.LITERATURE,
                parent_uuid=parent.corpus_uuid,
                vocabulary=[f"word_{index}"],
                original_vocabulary=[f"word_{index}"],
            )
            return await manager.save_corpus(child)

        # Create 10 children in parallel
        children = await asyncio.gather(*[create_child(i) for i in range(10)])

        assert len(children) == 10
        for i, child in enumerate(children):
            assert child.corpus_name == f"parallel_child_{i}"
            assert f"word_{i}" in child.vocabulary
