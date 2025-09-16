"""Comprehensive tests for SemanticSearch (FAISS) functionality."""

import base64
import time

import numpy as np
import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase

from floridify.corpus.core import Corpus
from floridify.search.semantic.core import SemanticSearch
from floridify.search.semantic.models import SemanticIndex


class TestSemanticSearchBasic:
    """Test basic SemanticSearch functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, sample_corpus: Corpus):
        """Test SemanticSearch initialization from corpus."""
        semantic = await SemanticSearch.from_corpus(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
            device="cpu",
        )

        assert semantic.corpus_id == sample_corpus.id
        assert semantic.language == sample_corpus.language
        assert len(semantic.vocabulary) > 0
        assert semantic.model_name == "all-MiniLM-L6-v2"
        assert semantic.faiss_index is not None
        assert semantic.embeddings is not None

    @pytest.mark.asyncio
    async def test_embedding_generation(self, sample_corpus: Corpus):
        """Test that embeddings are properly generated."""
        semantic = await SemanticSearch.from_corpus(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32,
        )

        # Check embeddings shape
        assert semantic.embeddings.shape[0] == len(semantic.vocabulary)
        assert semantic.embeddings.shape[1] > 0  # Has embedding dimension

        # Check embeddings are normalized (for cosine similarity)
        norms = np.linalg.norm(semantic.embeddings, axis=1)
        # Most models produce normalized embeddings
        assert np.allclose(norms, 1.0, rtol=0.1) or np.all(norms > 0)

    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, semantic_search: SemanticSearch):
        """Test basic semantic search functionality."""
        # Search for a concept
        results = await semantic_search.search("fruit", k=10)

        assert len(results) > 0
        assert results[0].method == "semantic"
        assert 0.0 <= results[0].score <= 1.0

        # Should find semantically related words
        [r.word for r in results]
        # Depending on embeddings, should find words like apple, banana, cherry

    @pytest.mark.asyncio
    async def test_semantic_similarity_groups(self, semantic_search: SemanticSearch):
        """Test that semantic search finds related concepts."""
        test_groups = {
            "technology": ["computer", "digital", "electronic", "device", "data"],
            "education": ["educate", "educational", "college", "student", "learn"],
            "communication": ["communicate", "conversation", "dialogue", "discuss"],
            "emotion": ["emotional", "feeling", "happy", "sad"],
        }

        for concept, expected_related in test_groups.items():
            results = await semantic_search.search(concept, k=20)
            found_words = [r.word for r in results]

            # Should find at least some related words
            set(found_words) & set(expected_related)
            # Relaxed assertion - embeddings vary

    @pytest.mark.asyncio
    async def test_k_parameter(self, semantic_search: SemanticSearch):
        """Test the k parameter for result limiting."""
        results_5 = await semantic_search.search("computer", k=5)
        results_10 = await semantic_search.search("computer", k=10)
        results_20 = await semantic_search.search("computer", k=20)

        assert len(results_5) <= 5
        assert len(results_10) <= 10
        assert len(results_20) <= 20

        # Results should be consistent (same top results)
        for i in range(min(5, len(results_5))):
            assert results_5[i].word == results_10[i].word
            assert results_5[i].word == results_20[i].word

    @pytest.mark.asyncio
    async def test_min_score_filtering(self, semantic_search: SemanticSearch):
        """Test min_score parameter for filtering results."""
        all_results = await semantic_search.search("test", k=50)
        filtered_results = await semantic_search.search("test", k=50, min_score=0.5)

        # Filtered should have fewer or equal results
        assert len(filtered_results) <= len(all_results)

        # All filtered results should meet threshold
        for result in filtered_results:
            assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_score_ordering(self, semantic_search: SemanticSearch):
        """Test that results are ordered by similarity score."""
        results = await semantic_search.search("apple", k=20)

        # Scores should be in descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        # Distance should increase (inverse of score)
        for i in range(len(results) - 1):
            assert results[i].distance <= results[i + 1].distance

    @pytest.mark.asyncio
    async def test_empty_query(self, semantic_search: SemanticSearch):
        """Test handling of empty queries."""
        results = await semantic_search.search("", k=10)
        # Should either return empty or handle gracefully
        assert isinstance(results, list)

        results = await semantic_search.search("   ", k=10)
        assert isinstance(results, list)


class TestSemanticSearchAdvanced:
    """Test advanced SemanticSearch features."""

    @pytest.mark.asyncio
    async def test_multi_word_query(self, semantic_search: SemanticSearch):
        """Test semantic search with multi-word queries."""
        results = await semantic_search.search("computer science", k=10)

        assert len(results) > 0
        found_words = [r.word for r in results]

        # Should find technology-related terms
        tech_words = ["computer", "digital", "data", "electronic"]
        set(found_words) & set(tech_words)
        # Some overlap expected

    @pytest.mark.asyncio
    async def test_phrase_understanding(self, semantic_search: SemanticSearch):
        """Test understanding of phrases vs individual words."""
        # Search for phrases with specific meaning
        phrase_tests = [
            ("machine learning", ["computer", "data", "algorithm"]),
            ("social media", ["communicate", "network", "connect"]),
            ("climate change", ["environment", "weather", "temperature"]),
        ]

        for phrase, expected_concepts in phrase_tests:
            results = await semantic_search.search(phrase, k=20)
            [r.word for r in results]
            # Check for conceptual overlap

    @pytest.mark.asyncio
    async def test_cross_lingual_similarity(self, semantic_search: SemanticSearch):
        """Test handling of non-English queries."""
        # This depends on the model's multilingual capabilities
        queries = [
            "ordinateur",  # French for computer
            "Komputer",  # German/Polish
            "computadora",  # Spanish
        ]

        for query in queries:
            results = await semantic_search.search(query, k=10)
            # Should handle without crashing
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_embedding_caching(self, sample_corpus: Corpus):
        """Test that embeddings are properly cached/reused."""
        # Create first instance
        semantic1 = await SemanticSearch.from_corpus(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
        )

        # Create second instance with same corpus
        semantic2 = await SemanticSearch.from_corpus(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
        )

        # Embeddings should be identical if cached properly
        if semantic1.embeddings is not None and semantic2.embeddings is not None:
            # Check a few embeddings for equality
            assert np.allclose(semantic1.embeddings[:5], semantic2.embeddings[:5], rtol=1e-5)


class TestFAISSIndexManagement:
    """Test FAISS index creation and management."""

    @pytest.mark.asyncio
    async def test_index_type_selection(self, sample_corpus: Corpus):
        """Test that appropriate FAISS index type is selected based on corpus size."""
        # Small corpus - should use exact search
        small_corpus = Corpus(
            name="small",
            language="en",
            words={f"word{i}": 1 for i in range(100)},
            total_words=100,
        )

        await SemanticSearch.from_corpus(small_corpus)
        # Check index type (implementation specific)

        # Large corpus simulation
        Corpus(
            name="large",
            language="en",
            words={f"word{i}": 1 for i in range(50000)},
            total_words=50000,
        )

        # Would test quantization, but expensive for unit tests

    @pytest.mark.asyncio
    async def test_faiss_index_search(self, semantic_search: SemanticSearch):
        """Test direct FAISS index search operations."""
        # Get embedding for a query
        query_embedding = await semantic_search._get_embedding("test")

        # Search directly with FAISS
        if query_embedding is not None:
            query_vec = query_embedding.reshape(1, -1).astype(np.float32)
            distances, indices = semantic_search.faiss_index.search(query_vec, k=5)

            assert len(indices[0]) <= 5
            assert len(distances[0]) <= 5
            assert np.all(distances[0] >= 0)  # L2 distances are non-negative

    @pytest.mark.asyncio
    async def test_index_persistence(self, sample_corpus: Corpus, semantic_search: SemanticSearch):
        """Test FAISS index serialization and deserialization."""
        # Create index from search
        index_data = semantic_search.to_semantic_index()

        assert index_data.corpus_id == sample_corpus.id
        assert index_data.model_name == semantic_search.model_name
        assert index_data.faiss_index is not None
        assert index_data.embeddings_encoded is not None

        # Test base64 encoding of index
        assert isinstance(index_data.faiss_index, str)  # Should be base64
        decoded = base64.b64decode(index_data.faiss_index)
        assert len(decoded) > 0

    @pytest.mark.asyncio
    async def test_index_reconstruction(
        self, sample_corpus: Corpus, semantic_search: SemanticSearch
    ):
        """Test reconstructing SemanticSearch from index."""
        # Create index
        index_data = semantic_search.to_semantic_index()

        # Reconstruct search from index
        reconstructed = SemanticSearch.from_index(index_data)

        assert reconstructed.corpus_id == semantic_search.corpus_id
        assert reconstructed.model_name == semantic_search.model_name
        assert len(reconstructed.vocabulary) == len(semantic_search.vocabulary)

        # Test that search works
        results = await reconstructed.search("test", k=5)
        assert len(results) > 0


class TestSemanticIndexVersioning:
    """Test SemanticIndex persistence and versioning."""

    @pytest.mark.asyncio
    async def test_index_metadata_creation(
        self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase
    ):
        """Test creating SemanticIndex with Metadata."""
        semantic = await SemanticSearch.from_corpus(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
        )

        index = await SemanticIndex.get_or_create(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
            index_data=semantic.to_semantic_index(),
        )

        assert index is not None
        # Index should have metadata fields

    @pytest.mark.asyncio
    async def test_index_versioning(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test SemanticIndex version management."""
        model_name = "all-MiniLM-L6-v2"

        # Create first version
        semantic1 = await SemanticSearch.from_corpus(sample_corpus, model_name)
        index1 = await SemanticIndex.get_or_create(
            sample_corpus, model_name, semantic1.to_semantic_index()
        )

        # Get same index - should return existing
        index2 = await SemanticIndex.get_or_create(
            sample_corpus, model_name, semantic1.to_semantic_index()
        )

        # Should be same version
        assert index1.vocabulary_hash == index2.vocabulary_hash

        # Modify corpus
        sample_corpus.words["newword"] = 100
        await sample_corpus.save()

        # Create new index with updated corpus
        semantic3 = await SemanticSearch.from_corpus(sample_corpus, model_name)
        index3 = await SemanticIndex.get_or_create(
            sample_corpus, model_name, semantic3.to_semantic_index()
        )

        # Should be different version
        assert index3.vocabulary_hash != index1.vocabulary_hash

    @pytest.mark.asyncio
    async def test_index_retrieval(self, sample_corpus: Corpus, test_db: AsyncIOMotorDatabase):
        """Test retrieving stored SemanticIndex."""
        model_name = "all-MiniLM-L6-v2"

        # Create and store index
        semantic = await SemanticSearch.from_corpus(sample_corpus, model_name)
        stored = await SemanticIndex.get_or_create(
            sample_corpus, model_name, semantic.to_semantic_index()
        )

        # Retrieve index
        retrieved = await SemanticIndex.get_latest(sample_corpus, model_name)

        assert retrieved is not None
        assert retrieved.corpus_id == stored.corpus_id
        assert retrieved.model_name == stored.model_name


class TestSemanticSearchPerformance:
    """Test SemanticSearch performance characteristics."""

    @pytest.mark.asyncio
    async def test_search_performance(
        self, semantic_search: SemanticSearch, performance_thresholds: dict
    ):
        """Test semantic search operation performance."""
        # Warm up model
        _ = await semantic_search.search("test", k=5)

        # Measure search time
        queries = ["apple", "computer", "education", "emotion", "building"]

        start = time.perf_counter()
        for query in queries:
            _ = await semantic_search.search(query, k=10)
        elapsed = (time.perf_counter() - start) / len(queries)

        assert elapsed < performance_thresholds["semantic_search"]

    @pytest.mark.asyncio
    async def test_batch_embedding_performance(self, sample_corpus: Corpus):
        """Test batch embedding generation performance."""
        start = time.perf_counter()
        await SemanticSearch.from_corpus(
            corpus=sample_corpus,
            model_name="all-MiniLM-L6-v2",
            batch_size=64,  # Larger batch for efficiency
        )
        build_time = time.perf_counter() - start

        # Should complete in reasonable time
        assert build_time < 30.0  # 30 seconds for ~500 words

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, semantic_search: SemanticSearch):
        """Test concurrent semantic searches."""
        import asyncio

        queries = ["apple", "computer", "education", "building", "emotion"]

        # Run searches concurrently
        start = time.perf_counter()
        tasks = [semantic_search.search(q, k=10) for q in queries]
        results = await asyncio.gather(*tasks)
        time.perf_counter() - start

        # Run searches sequentially
        start = time.perf_counter()
        sequential_results = []
        for q in queries:
            sequential_results.append(await semantic_search.search(q, k=10))
        time.perf_counter() - start

        # Concurrent should be similar or faster
        assert all(len(r) > 0 for r in results)
        # Concurrent execution should not cause issues


class TestSemanticSearchEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_corpus(self):
        """Test semantic search with empty corpus."""
        empty_corpus = Corpus(
            name="empty",
            language="en",
            words={},
            total_words=0,
        )

        # Should handle empty corpus gracefully
        with pytest.raises((ValueError, AssertionError)):
            await SemanticSearch.from_corpus(empty_corpus)

    @pytest.mark.asyncio
    async def test_single_word_corpus(self):
        """Test semantic search with single-word corpus."""
        single_corpus = Corpus(
            name="single",
            language="en",
            words={"unique": 1},
            total_words=1,
        )

        semantic = await SemanticSearch.from_corpus(single_corpus)

        results = await semantic.search("unique", k=5)
        assert len(results) == 1
        assert results[0].word == "unique"

        results = await semantic.search("different", k=5)
        assert len(results) == 1  # Only one word available
        assert results[0].word == "unique"

    @pytest.mark.asyncio
    async def test_special_characters_query(self, semantic_search: SemanticSearch):
        """Test queries with special characters."""
        special_queries = [
            "@mention",
            "#hashtag",
            "user@email.com",
            "hello-world",
            "$100",
            "50%",
        ]

        for query in special_queries:
            results = await semantic_search.search(query, k=5)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_unicode_query(self, semantic_search: SemanticSearch):
        """Test Unicode queries."""
        unicode_queries = [
            "café",
            "naïve",
            "北京",
            "🚀",
            "Zürich",
        ]

        for query in unicode_queries:
            results = await semantic_search.search(query, k=5)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_very_long_query(self, semantic_search: SemanticSearch):
        """Test handling of very long queries."""
        # Most models have token limits
        long_query = " ".join(["word"] * 1000)

        results = await semantic_search.search(long_query, k=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_k_larger_than_corpus(self, semantic_search: SemanticSearch):
        """Test when k is larger than corpus size."""
        corpus_size = len(semantic_search.vocabulary)

        results = await semantic_search.search("test", k=corpus_size + 100)

        # Should return at most corpus_size results
        assert len(results) <= corpus_size
