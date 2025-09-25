"""Comprehensive tests for LiteratureCorpus with real MongoDB integration."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from floridify.corpus.literature.core import LiteratureCorpus
from floridify.corpus.manager import TreeCorpusManager
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
        corpus = LiteratureCorpus(
            corpus_name="shakespeare_works",
            language=Language.ENGLISH,
            vocabulary=["thou", "thee", "thy", "thine"],
            corpus_type=CorpusType.LITERATURE,
        )

        # Save to MongoDB
        await corpus.save()

        assert corpus.corpus_id is not None
        assert corpus.corpus_name == "shakespeare_works"
        assert corpus.corpus_type == CorpusType.LITERATURE
        assert len(corpus.vocabulary) == 4
        assert "thou" in corpus.vocabulary

        # Verify retrieval from MongoDB
        loaded = await LiteratureCorpus.get(corpus.corpus_id)
        assert loaded is not None
        assert loaded.corpus_name == "shakespeare_works"
        assert loaded.vocabulary == corpus.vocabulary

    @pytest.mark.asyncio
    async def test_add_literature_source(self, test_db):
        """Test adding a literature work as a child corpus."""
        # Create parent literature corpus
        parent = LiteratureCorpus(
            corpus_name="english_literature",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            is_master=True,
        )
        await parent.save()

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
        manager = TreeCorpusManager()
        children = await manager.get_children(parent.corpus_id)
        assert len(children) == 1

        child = children[0]
        assert child.corpus_name == "english_literature_Hamlet"
        assert child.corpus_type == CorpusType.LITERATURE
        assert child.metadata["title"] == "Hamlet"
        assert child.metadata["author"] == "Shakespeare, William"
        assert child.metadata["genre"] == Genre.DRAMA.value
        assert child.metadata["period"] == Period.RENAISSANCE.value

    @pytest.mark.asyncio
    async def test_add_multiple_works(self, test_db):
        """Test adding multiple literature works to a corpus."""
        # Create master corpus
        master = LiteratureCorpus(
            corpus_name="shakespeare_collection",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            is_master=True,
        )
        await master.save()

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
        manager = TreeCorpusManager()
        children = await manager.get_children(master.corpus_id)
        assert len(children) == 3

        # Check titles
        child_titles = [child.metadata["title"] for child in children]
        assert "Hamlet" in child_titles
        assert "Romeo and Juliet" in child_titles
        assert "Macbeth" in child_titles

    @pytest.mark.asyncio
    async def test_literature_corpus_with_tree_manager(self, test_db):
        """Test LiteratureCorpus integration with TreeCorpusManager."""
        manager = TreeCorpusManager()

        # Create root literature corpus
        root = LiteratureCorpus(
            corpus_name="world_literature",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            is_master=True,
        )
        await root.save()

        # Create author corpus
        author_corpus = LiteratureCorpus(
            corpus_name="shakespeare",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            parent_corpus_id=root.corpus_id,
        )
        await author_corpus.save()

        # Add to tree
        await manager.add_child(root, author_corpus)

        # Create work corpus
        work_corpus = LiteratureCorpus(
            corpus_name="hamlet",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_corpus_id=author_corpus.corpus_id,
            vocabulary=["prince", "denmark", "ghost", "revenge"],
        )
        work_corpus.metadata.update(
            {
                "title": "Hamlet",
                "author": "Shakespeare, William",
                "genre": Genre.TRAGEDY.value,
                "period": Period.RENAISSANCE.value,
            },
        )
        await work_corpus.save()

        # Add to tree
        await manager.add_child(author_corpus, work_corpus)

        # Verify tree structure
        tree = await manager.get_tree(root.corpus_id)
        assert tree is not None
        assert len(tree["children"]) == 1  # author_corpus
        assert len(tree["children"][0]["children"]) == 1  # work_corpus
        assert tree["children"][0]["children"][0]["metadata"]["title"] == "Hamlet"

    @pytest.mark.asyncio
    async def test_literature_corpus_vocabulary_aggregation(self, test_db):
        """Test vocabulary aggregation across literature works."""
        # Create parent corpus
        parent = LiteratureCorpus(
            corpus_name="poetry_collection",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            is_master=True,
        )
        await parent.save()

        # Create child corpora with vocabularies
        poem1 = LiteratureCorpus(
            corpus_name="poem1",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_corpus_id=parent.corpus_id,
            vocabulary=["rose", "red", "love", "sweet"],
        )
        await poem1.save()

        poem2 = LiteratureCorpus(
            corpus_name="poem2",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            parent_corpus_id=parent.corpus_id,
            vocabulary=["violet", "blue", "love", "true"],
        )
        await poem2.save()

        # Add children to parent
        manager = TreeCorpusManager()
        await manager.add_child(parent, poem1)
        await manager.add_child(parent, poem2)

        # Aggregate vocabulary
        await manager.aggregate_vocabulary(parent.corpus_id)

        # Reload parent
        reloaded = await LiteratureCorpus.get(parent.corpus_id)
        assert reloaded is not None

        # Check aggregated vocabulary
        aggregated = set(reloaded.vocabulary)
        expected = {"rose", "red", "love", "sweet", "violet", "blue", "true"}
        assert aggregated == expected

    @pytest.mark.asyncio
    async def test_literature_corpus_with_metadata(self, test_db):
        """Test LiteratureCorpus with rich metadata."""
        corpus = LiteratureCorpus(
            corpus_name="victorian_novels",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
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

        await corpus.save()

        # Verify metadata persistence
        loaded = await LiteratureCorpus.get(corpus.corpus_id)
        assert loaded is not None
        assert loaded.metadata["period"] == Period.VICTORIAN.value
        assert Genre.NOVEL.value in loaded.metadata["genres"]
        assert "Charles Dickens" in loaded.metadata["authors"]
        assert loaded.metadata["date_range"] == "1837-1901"

    @pytest.mark.asyncio
    async def test_literature_corpus_versioning(self, test_db):
        """Test versioning of literature corpus changes."""
        corpus = LiteratureCorpus(
            corpus_name="evolving_work",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=["original", "words"],
        )
        await corpus.save()

        original_id = corpus.corpus_id
        original_version = corpus.version_info.version

        # Update vocabulary
        corpus.vocabulary.extend(["new", "additions"])
        corpus.update_version("Added new vocabulary")
        await corpus.save()

        # Check version was updated
        assert corpus.version_info.version != original_version
        assert corpus.corpus_id == original_id  # Same document

        # Load and verify
        loaded = await LiteratureCorpus.get(original_id)
        assert loaded is not None
        assert "new" in loaded.vocabulary
        assert "additions" in loaded.vocabulary

    @pytest.mark.asyncio
    async def test_literature_corpus_error_handling(self, test_db):
        """Test error handling in literature corpus operations."""
        corpus = LiteratureCorpus(
            corpus_name="test_errors",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
        )
        await corpus.save()

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
        manager = TreeCorpusManager()
        children = await manager.get_children(corpus.corpus_id)
        assert len(children) == 0

    @pytest.mark.asyncio
    async def test_literature_corpus_batch_operations(self, test_db):
        """Test batch operations on literature corpora."""
        # Create multiple corpora
        corpora = []
        for i in range(5):
            corpus = LiteratureCorpus(
                corpus_name=f"work_{i}",
                language=Language.ENGLISH,
                corpus_type=CorpusType.LITERATURE,
                vocabulary=[f"word_{i}", f"unique_{i}"],
            )
            corpus.metadata["work_number"] = i
            await corpus.save()
            corpora.append(corpus)

        # Batch retrieval
        ids = [c.corpus_id for c in corpora]
        loaded = await LiteratureCorpus.get_many_by_ids(ids)

        assert len(loaded) == 5
        work_numbers = [c.metadata["work_number"] for c in loaded]
        assert sorted(work_numbers) == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_literature_corpus_search_integration(self, test_db):
        """Test literature corpus integration with search capabilities."""
        # Create corpus with meaningful vocabulary
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
        )
        corpus.metadata.update(
            {
                "genre": Genre.POETRY.value,
                "themes": ["emotion", "human nature"],
                "searchable": True,
                "semantic_enabled": True,  # Store semantic flag in metadata
            },
        )
        await corpus.save()

        # Verify searchable metadata
        loaded = await LiteratureCorpus.get(corpus.corpus_id)
        assert loaded is not None
        assert loaded.metadata["searchable"] is True
        assert loaded.metadata.get("semantic_enabled", False) is True  # Check in metadata

        # Vocabulary should be available for search
        assert "love" in loaded.vocabulary
        assert "melancholy" in loaded.vocabulary

    @pytest.mark.asyncio
    async def test_literature_corpus_parallel_operations(self, test_db):
        """Test parallel operations on literature corpora."""
        # Create parent
        parent = LiteratureCorpus(
            corpus_name="parallel_parent",
            language=Language.ENGLISH,
            corpus_type=CorpusType.LITERATURE,
            vocabulary=[],
            is_master=True,
        )
        await parent.save()

        # Create children in parallel
        async def create_child(index: int):
            child = LiteratureCorpus(
                corpus_name=f"parallel_child_{index}",
                language=Language.ENGLISH,
                corpus_type=CorpusType.LITERATURE,
                parent_corpus_id=parent.corpus_id,
                vocabulary=[f"word_{index}"],
            )
            await child.save()
            return child

        # Create 10 children in parallel
        children = await asyncio.gather(*[create_child(i) for i in range(10)])

        assert len(children) == 10
        for i, child in enumerate(children):
            assert child.corpus_name == f"parallel_child_{i}"
            assert f"word_{i}" in child.vocabulary
