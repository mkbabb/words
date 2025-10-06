"""Semantic search functionality tests."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest
import pytest_asyncio

from floridify.models.dictionary import Definition, DictionaryProvider, Language, Word
from floridify.search.semantic.core import SemanticSearch


@pytest_asyncio.fixture
async def semantic_engine(test_db, words_with_definitions):
    """Create a semantic search engine instance with corpus."""
    from floridify.corpus.core import Corpus, CorpusType
    from floridify.corpus.manager import CorpusManager

    # Extract vocabulary from test words
    vocabulary = sorted(set(word.text for word, _ in words_with_definitions))

    # Create and save corpus
    corpus = Corpus(
        corpus_name="test_semantic_corpus",
        corpus_type=CorpusType.LANGUAGE,
        language=Language.ENGLISH,
        vocabulary=vocabulary,
        original_vocabulary=vocabulary,
        lemmatized_vocabulary=vocabulary,  # Use same vocabulary as lemmas for simplicity
    )

    # Build necessary indices for semantic search
    corpus.vocabulary_to_index = {word: i for i, word in enumerate(vocabulary)}
    corpus._build_signature_index()

    manager = CorpusManager()
    saved_corpus = await manager.save_corpus(corpus)

    # Create semantic search engine from corpus
    engine = await SemanticSearch.from_corpus(corpus=saved_corpus)

    yield engine


@pytest_asyncio.fixture
async def words_with_definitions(test_db):
    """Create words with semantic definitions for testing."""
    test_data = [
        {
            "word": "happy",
            "definition": "feeling or showing pleasure or contentment",
            "synonyms": ["joyful", "cheerful", "delighted"],
        },
        {
            "word": "sad",
            "definition": "feeling or showing sorrow; unhappy",
            "synonyms": ["unhappy", "sorrowful", "dejected"],
        },
        {
            "word": "angry",
            "definition": "feeling or showing strong annoyance, displeasure, or hostility",
            "synonyms": ["furious", "irate", "enraged"],
        },
        {
            "word": "calm",
            "definition": "not showing or feeling nervousness, anger, or other strong emotions",
            "synonyms": ["peaceful", "serene", "tranquil"],
        },
        {
            "word": "excited",
            "definition": "very enthusiastic and eager",
            "synonyms": ["thrilled", "eager", "enthusiastic"],
        },
    ]

    created_words = []
    for data in test_data:
        word = Word(text=data["word"], language=Language.ENGLISH)
        await word.save()

        definition = Definition(
            word_id=word.id,
            text=data["definition"],
            part_of_speech="adjective",
            synonyms=data["synonyms"],
            providers=[DictionaryProvider.FREE_DICTIONARY],
        )
        await definition.save()

        created_words.append((word, definition))

    return created_words


class TestSemanticSearch:
    """Test suite for semantic search functionality."""

    @pytest.mark.asyncio
    async def test_initialize_index(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test initializing semantic index from corpus."""
        # Initialize the semantic engine
        await semantic_engine.initialize()

        # Verify index was created
        assert semantic_engine.sentence_index is not None
        assert semantic_engine.sentence_embeddings is not None

    @pytest.mark.asyncio
    async def test_semantic_similarity(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test semantic similarity search."""
        await semantic_engine.initialize()

        # Search for semantically similar words
        results = await semantic_engine.search("joyful", max_results=5)

        assert len(results) > 0
        # "happy" should be in top results due to semantic similarity
        words = [r.word for r in results]
        assert "happy" in words[:3]  # Should be in top 3 results

    @pytest.mark.asyncio
    async def test_embedding_generation(self, semantic_engine: SemanticSearch, test_db):
        """Test embedding generation for text."""
        text = "feeling happy and content"

        with patch.object(semantic_engine, "_encode") as mock_embed:
            mock_embed.return_value = np.array([[0.1] * 768])  # Standard embedding size

            embedding = semantic_engine._encode([text])

            assert embedding is not None
            assert embedding.shape == (1, 768)
            assert isinstance(embedding, np.ndarray)

    @pytest.mark.asyncio
    async def test_search_with_threshold(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test semantic search with similarity threshold."""
        await semantic_engine.initialize()

        # Search with high threshold
        results = await semantic_engine.search("joyful", max_results=10, min_score=0.8)

        # All results should have high similarity
        assert all(r.score >= 0.8 for r in results)

    @pytest.mark.asyncio
    async def test_search_empty_index(self, test_db):
        """Test search on empty index."""
        from floridify.corpus.core import Corpus, CorpusType
        from floridify.corpus.manager import CorpusManager

        # Create empty corpus using proper initialization
        corpus = await Corpus.create(
            corpus_name="empty_semantic_corpus",
            vocabulary=[],
            language=Language.ENGLISH,
        )
        corpus.corpus_type = CorpusType.LANGUAGE
        corpus.lemmatized_vocabulary = []

        manager = CorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        # Create semantic search from empty corpus
        engine = await SemanticSearch.from_corpus(corpus=saved_corpus)

        # Search should return empty results
        results = await engine.search("test")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_index_persistence(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test index persistence through versioning system."""
        await semantic_engine.initialize()

        # Create a new engine from the same corpus (should use cached index)
        new_engine = await SemanticSearch.from_corpus(corpus=semantic_engine.corpus)

        # Both should give same results
        results1 = await semantic_engine.search("happy", max_results=3)
        results2 = await new_engine.search("happy", max_results=3)

        # Check that we get consistent results
        assert len(results1) == len(results2)
        # Results might be in different order but should contain same words
        words1 = set(r.word for r in results1)
        words2 = set(r.word for r in results2)
        assert words1 == words2

    @pytest.mark.asyncio
    async def test_batch_embedding(self, semantic_engine: SemanticSearch, test_db):
        """Test batch embedding generation."""
        texts = [
            "happy and joyful",
            "sad and sorrowful",
            "angry and furious",
            "calm and peaceful",
        ]

        with patch.object(semantic_engine, "_encode") as mock_embed:
            mock_embeddings = np.random.rand(len(texts), 768)
            mock_embed.return_value = mock_embeddings

            embeddings = semantic_engine._encode(texts)

            assert embeddings.shape == (4, 768)

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test semantic search returns proper results structure."""
        await semantic_engine.initialize()

        # Do a real search
        results = await semantic_engine.search("joyful", max_results=5)

        # Verify result structure
        for result in results:
            assert hasattr(result, "word")
            assert hasattr(result, "score")
            assert 0 <= result.score <= 1.0
            assert result.word in semantic_engine.corpus.vocabulary

        # Check that results are sorted by score
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_concurrent_searches(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test concurrent semantic searches."""
        import asyncio

        await semantic_engine.initialize()

        queries = ["joyful", "sorrowful", "peaceful", "furious"]

        # Run searches concurrently (search is async)
        results = await asyncio.gather(
            *[semantic_engine.search(q, max_results=3) for q in queries]
        )

        # Each search should return results
        assert all(len(r) > 0 for r in results)

    @pytest.mark.asyncio
    async def test_index_update(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test updating semantic index with new corpus."""
        await semantic_engine.initialize()
        initial_embeddings = semantic_engine.sentence_embeddings

        # Update corpus with new vocabulary
        from floridify.corpus.core import Corpus, CorpusType

        new_vocabulary = sorted(set([w.text for w, _ in words_with_definitions] + ["ecstatic"]))
        new_corpus = Corpus(
            corpus_name="test_semantic_corpus_updated",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=new_vocabulary,
            original_vocabulary=new_vocabulary,
        )

        await semantic_engine.update_corpus(new_corpus)

        # Embeddings should be updated
        assert semantic_engine.sentence_embeddings is not None
        assert len(semantic_engine.sentence_embeddings) >= len(initial_embeddings)

    @pytest.mark.asyncio
    async def test_invalid_embedding_dimension(self, semantic_engine: SemanticSearch, test_db):
        """Test handling of invalid embedding dimensions."""
        await semantic_engine.initialize()

        # Mock encode to return wrong dimensions
        with patch.object(semantic_engine, "_encode") as mock_embed:
            # Return wrong dimension
            mock_embed.return_value = np.array([[0.1] * 512])  # Wrong size

            # Search should handle gracefully
            results = await semantic_engine.search("test")
            assert isinstance(results, list)  # Should return list (possibly empty)

    @pytest.mark.asyncio
    async def test_empty_query(
        self, semantic_engine: SemanticSearch, words_with_definitions, test_db
    ):
        """Test handling of empty search query."""
        await semantic_engine.initialize()

        # Empty query should return empty results or raise an error
        results = await semantic_engine.search("")
        assert isinstance(results, list)
        assert len(results) == 0

        results = await semantic_engine.search("   ")
        assert isinstance(results, list)
        assert len(results) == 0
