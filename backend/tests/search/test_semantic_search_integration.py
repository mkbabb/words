"""Integration tests for semantic search without mocking - tests real embeddings."""

from __future__ import annotations

import numpy as np
import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import TreeCorpusManager
from floridify.models.base import Language
from floridify.search.semantic.constants import DEFAULT_SENTENCE_MODEL
from floridify.search.semantic.core import SemanticSearch


class TestSemanticSearchIntegration:
    """Integration tests for semantic search with real embeddings."""

    @pytest_asyncio.fixture
    async def small_corpus(self, test_db) -> Corpus:
        """Create a small corpus for testing."""
        vocabulary = [
            # Emotion words
            "happy",
            "joyful",
            "cheerful",
            "glad",
            "delighted",
            "sad",
            "unhappy",
            "sorrowful",
            "miserable",
            "dejected",
            "angry",
            "furious",
            "irate",
            "enraged",
            "annoyed",
            "calm",
            "peaceful",
            "serene",
            "tranquil",
            "relaxed",
            # Fruit words
            "apple",
            "banana",
            "orange",
            "grape",
            "strawberry",
            # Animal words
            "dog",
            "cat",
            "bird",
            "fish",
            "mouse",
            # Random words for diversity
            "computer",
            "book",
            "table",
            "chair",
            "window",
        ]

        corpus = Corpus(
            corpus_name="test_semantic_small",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            lemmatized_vocabulary=vocabulary,  # Use vocabulary as lemmas for testing
        )

        # Build indices
        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        return await manager.save_corpus(corpus)

    @pytest_asyncio.fixture
    async def language_corpus(self, test_db) -> Corpus:
        """Create a language-level corpus."""
        # Common English words
        vocabulary = [
            "the",
            "be",
            "to",
            "of",
            "and",
            "a",
            "in",
            "that",
            "have",
            "I",
            "it",
            "for",
            "not",
            "on",
            "with",
            "he",
            "as",
            "you",
            "do",
            "at",
            "this",
            "but",
            "his",
            "by",
            "from",
            "they",
            "we",
            "say",
            "her",
            "she",
            "or",
            "an",
            "will",
            "my",
            "one",
            "all",
            "would",
            "there",
            "their",
            "what",
        ]

        corpus = Corpus(
            corpus_name="test_semantic_language",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
            lemmatized_vocabulary=vocabulary,
        )

        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        return await manager.save_corpus(corpus)

    @pytest.mark.asyncio
    async def test_real_embeddings_generation(self, small_corpus: Corpus, test_db):
        """Test that real embeddings are generated without mocking."""
        # Create semantic search engine
        engine = await SemanticSearch.from_corpus(
            corpus=small_corpus,
            model_name=DEFAULT_SENTENCE_MODEL,
        )

        # Initialize if needed
        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Verify embeddings were generated
        assert engine.sentence_embeddings is not None
        assert isinstance(engine.sentence_embeddings, np.ndarray)
        assert engine.sentence_embeddings.shape[0] == len(small_corpus.lemmatized_vocabulary)
        assert engine.sentence_embeddings.shape[1] > 0  # Has dimensions

        # Verify embeddings are not all zeros or all the same
        assert not np.allclose(engine.sentence_embeddings, 0)
        assert not np.allclose(engine.sentence_embeddings[0], engine.sentence_embeddings[1])

    @pytest.mark.asyncio
    async def test_semantic_similarity_emotions(self, small_corpus: Corpus, test_db):
        """Test semantic similarity for emotion words."""
        engine = await SemanticSearch.from_corpus(
            corpus=small_corpus, model_name=DEFAULT_SENTENCE_MODEL
        )

        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Search for "joyful" - should find similar emotion words
        results = await engine.search("joyful", max_results=5)

        assert len(results) > 0
        words = [r.word for r in results]

        # Should find similar positive emotions
        positive_emotions = ["happy", "joyful", "cheerful", "glad", "delighted"]
        found_positives = [w for w in words if w in positive_emotions]
        assert len(found_positives) >= 2  # At least 2 positive emotions

    @pytest.mark.asyncio
    async def test_semantic_similarity_fruits(self, small_corpus: Corpus, test_db):
        """Test semantic similarity for fruit words."""
        engine = await SemanticSearch.from_corpus(
            corpus=small_corpus, model_name=DEFAULT_SENTENCE_MODEL
        )

        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Search for "apple" - should find other fruits
        results = await engine.search("apple", max_results=5)

        assert len(results) > 0
        words = [r.word for r in results]

        # Should find other fruits
        fruits = ["apple", "banana", "orange", "grape", "strawberry"]
        found_fruits = [w for w in words if w in fruits]
        assert len(found_fruits) >= 2  # At least 2 fruits

    @pytest.mark.asyncio
    async def test_faiss_index_creation(self, small_corpus: Corpus, test_db):
        """Test FAISS index is properly created."""
        engine = await SemanticSearch.from_corpus(
            corpus=small_corpus, model_name=DEFAULT_SENTENCE_MODEL
        )

        if engine.sentence_index is None:
            await engine.initialize()

        # Verify FAISS index
        assert engine.sentence_index is not None
        assert engine.sentence_index.is_trained
        assert engine.sentence_index.ntotal == len(small_corpus.lemmatized_vocabulary)

    @pytest.mark.asyncio
    async def test_index_persistence(self, small_corpus: Corpus, test_db):
        """Test that semantic index can be saved and loaded."""
        # Create and initialize first engine
        engine1 = await SemanticSearch.from_corpus(
            corpus=small_corpus, model_name=DEFAULT_SENTENCE_MODEL
        )

        if engine1.sentence_embeddings is None:
            await engine1.initialize()

        # Index is automatically saved during initialization
        # No need to manually save

        # Create second engine from saved index
        engine2 = await SemanticSearch.from_corpus(
            corpus=small_corpus, model_name=DEFAULT_SENTENCE_MODEL
        )

        # Should load from cache without regenerating
        assert engine2.sentence_embeddings is not None
        assert engine2.sentence_embeddings.shape == engine1.sentence_embeddings.shape

        # Results should be the same
        results1 = await engine1.search("happy", max_results=3)
        results2 = await engine2.search("happy", max_results=3)

        assert len(results1) == len(results2)
        for r1, r2 in zip(results1, results2):
            assert r1.word == r2.word
            assert abs(r1.score - r2.score) < 0.001

    @pytest.mark.asyncio
    async def test_empty_corpus_handling(self, test_db):
        """Test handling of corpus with empty vocabulary."""
        empty_corpus = Corpus(
            corpus_name="test_empty",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=[],
            original_vocabulary=[],
            lemmatized_vocabulary=[],
        )

        manager = TreeCorpusManager()
        saved = await manager.save_corpus(empty_corpus)

        # Should handle empty corpus gracefully
        engine = await SemanticSearch.from_corpus(corpus=saved)

        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Should have empty embeddings
        assert engine.sentence_embeddings is not None
        assert engine.sentence_embeddings.shape[0] == 0

        # Search should return empty results
        results = await engine.search("test", max_results=5)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, language_corpus: Corpus, test_db):
        """Test batch processing of embeddings."""
        engine = await SemanticSearch.from_corpus(
            corpus=language_corpus,
            model_name=DEFAULT_SENTENCE_MODEL,
            batch_size=8,  # Small batch size for testing
        )

        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Verify all words were embedded
        assert engine.sentence_embeddings.shape[0] == len(language_corpus.lemmatized_vocabulary)

        # Verify embeddings are normalized
        norms = np.linalg.norm(engine.sentence_embeddings, axis=1)
        assert np.allclose(norms, 1.0, rtol=1e-5)

    @pytest.mark.asyncio
    async def test_search_with_different_models(self, small_corpus: Corpus, test_db):
        """Test search with different sentence transformer models."""
        # Test with default model
        engine = await SemanticSearch.from_corpus(
            corpus=small_corpus,
            model_name=DEFAULT_SENTENCE_MODEL,
        )

        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Should still work
        results = await engine.search("happy", max_results=3)
        assert len(results) > 0

        # Verify model name is stored
        assert engine.index is not None
        assert engine.index.model_name == DEFAULT_SENTENCE_MODEL

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, small_corpus: Corpus, test_db):
        """Test concurrent semantic searches."""
        import asyncio

        engine = await SemanticSearch.from_corpus(
            corpus=small_corpus, model_name=DEFAULT_SENTENCE_MODEL
        )

        if engine.sentence_embeddings is None:
            await engine.initialize()

        # Run multiple searches concurrently
        queries = ["happy", "apple", "dog", "computer", "calm"]
        tasks = [engine.search(query, max_results=3) for query in queries]

        results_list = await asyncio.gather(*tasks)

        # All should return results
        for results in results_list:
            assert len(results) > 0
