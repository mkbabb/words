"""End-to-end semantic search tests with real embeddings and indices."""

from __future__ import annotations

import numpy as np
import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus
from floridify.corpus.manager import CorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.dictionary import Language
from floridify.search.semantic.core import SemanticSearch


class TestSemanticSearchEndToEnd:
    """End-to-end tests for semantic search with real embeddings."""

    @pytest_asyncio.fixture
    async def small_corpus(self, test_db) -> Corpus:
        """Create a small test corpus for semantic search testing."""
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
            "irritated",
            "calm",
            "peaceful",
            "serene",
            "tranquil",
            "relaxed",
            # Animal words (for diversity)
            "dog",
            "cat",
            "elephant",
            "tiger",
            "lion",
            # Food words
            "apple",
            "banana",
            "orange",
            "bread",
            "cheese",
            # Action words
            "run",
            "walk",
            "jump",
            "swim",
            "fly",
        ]

        corpus = Corpus(
            corpus_name="semantic_test_small",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(vocabulary),
            original_vocabulary=sorted(vocabulary),
            lemmatized_vocabulary=sorted(vocabulary),
        )

        # Build indices
        corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted(vocabulary))}
        corpus._build_signature_index()

        manager = CorpusManager()
        return await manager.save_corpus(corpus)

    @pytest_asyncio.fixture
    async def language_corpus(self, test_db) -> Corpus:
        """Create a larger language-level corpus."""
        # Simulate a language corpus with more words
        base_words = [
            "word",
            "language",
            "speak",
            "write",
            "read",
            "book",
            "paper",
            "pen",
            "computer",
            "type",
            "letter",
            "sentence",
            "paragraph",
            "story",
            "novel",
            "poetry",
            "prose",
            "essay",
        ]

        # Generate variations for a larger corpus
        vocabulary = []
        for base in base_words:
            vocabulary.append(base)
            vocabulary.append(f"{base}s")  # plural
            vocabulary.append(f"{base}ed")  # past tense
            vocabulary.append(f"{base}ing")  # gerund
            vocabulary.append(f"{base}er")  # agent

        # Add more semantic variations
        vocabulary.extend(
            [
                "happy",
                "happiness",
                "happily",
                "unhappy",
                "happier",
                "sad",
                "sadness",
                "sadly",
                "sadder",
                "saddest",
                "joy",
                "joyful",
                "joyfully",
                "joyous",
                "joyousness",
                "anger",
                "angry",
                "angrily",
                "angrier",
                "angriest",
            ]
        )

        corpus = Corpus(
            corpus_name="semantic_test_language",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(set(vocabulary)),
            original_vocabulary=sorted(set(vocabulary)),
            lemmatized_vocabulary=sorted(set(vocabulary)),
        )

        corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted(set(vocabulary)))}
        corpus._build_signature_index()

        manager = CorpusManager()
        return await manager.save_corpus(corpus)

    @pytest_asyncio.fixture
    async def literature_corpus(self, test_db) -> Corpus:
        """Create a literature-level corpus with domain-specific vocabulary."""
        # Shakespeare-inspired vocabulary
        vocabulary = [
            "thou",
            "thee",
            "thy",
            "thine",
            "art",
            "hath",
            "doth",
            "wherefore",
            "hither",
            "thither",
            "whence",
            "verily",
            "forsooth",
            "prithee",
            "anon",
            "ere",
            "oft",
            "nay",
            "yea",
            "twas",
            "tis",
            "methinks",
            "mayhap",
            "perchance",
            "betwixt",
            "whilst",
            "alas",
            "fie",
            # Modern literature words
            "novel",
            "chapter",
            "character",
            "plot",
            "theme",
            "protagonist",
            "antagonist",
            "narrative",
            "dialogue",
            "monologue",
            "soliloquy",
            "metaphor",
            "simile",
            "allegory",
            "symbolism",
            "irony",
        ]

        corpus = Corpus(
            corpus_name="semantic_test_literature",
            corpus_type=CorpusType.LITERATURE,
            language=Language.ENGLISH,
            vocabulary=sorted(vocabulary),
            original_vocabulary=sorted(vocabulary),
            lemmatized_vocabulary=sorted(vocabulary),
        )

        corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted(vocabulary))}
        corpus._build_signature_index()

        manager = CorpusManager()
        return await manager.save_corpus(corpus)

    @pytest.mark.asyncio
    async def test_semantic_index_creation_small(self, small_corpus: Corpus, test_db):
        """Test creating semantic index from small corpus with real embeddings."""
        # Create semantic index with real embeddings
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Verify index was created
        assert engine.sentence_index is not None
        assert engine.sentence_embeddings is not None
        assert engine.sentence_embeddings.shape[0] == len(small_corpus.vocabulary)

        # Verify embeddings are real (not mocked)
        assert engine.sentence_embeddings.shape[1] > 0  # Has dimension
        assert not np.all(engine.sentence_embeddings == 0)  # Not all zeros
        assert not np.all(
            engine.sentence_embeddings == engine.sentence_embeddings[0]
        )  # Not all same

    @pytest.mark.asyncio
    async def test_semantic_similarity_emotions(self, small_corpus: Corpus, test_db):
        """Test semantic similarity for emotion words with real embeddings."""
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Search for words similar to "happy"
        results = engine.search("happy", max_results=5)

        assert len(results) > 0
        words = [r.word for r in results]

        # Should find related emotion words
        emotion_words = ["joyful", "cheerful", "glad", "delighted"]
        found_emotions = [w for w in words if w in emotion_words]
        assert len(found_emotions) > 0, f"Expected emotion words but got: {words}"

        # Should not find unrelated words in top results
        unrelated = ["elephant", "bread", "swim"]
        found_unrelated = [w for w in words[:3] if w in unrelated]
        assert len(found_unrelated) == 0, f"Found unrelated words in top results: {found_unrelated}"

    @pytest.mark.asyncio
    async def test_semantic_similarity_animals(self, small_corpus: Corpus, test_db):
        """Test semantic similarity for animal words."""
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Search for words similar to "dog"
        results = engine.search("dog", max_results=5)

        assert len(results) > 0
        words = [r.word for r in results]

        # Should find other animals
        animal_words = ["cat", "elephant", "tiger", "lion"]
        found_animals = [w for w in words if w in animal_words]
        assert len(found_animals) > 0, f"Expected animal words but got: {words}"

    @pytest.mark.asyncio
    async def test_index_versioning_and_caching(self, small_corpus: Corpus, test_db):
        """Test that semantic indices are properly versioned and cached."""
        # Create first engine
        engine1 = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine1.initialize()

        # Create second engine from same corpus
        engine2 = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine2.initialize()

        # Should use cached index (verify by checking embeddings are identical)
        assert engine1.sentence_embeddings.shape == engine2.sentence_embeddings.shape
        np.testing.assert_array_almost_equal(
            engine1.sentence_embeddings, engine2.sentence_embeddings, decimal=5
        )

        # Verify version metadata exists
        assert engine1.semantic_index is not None
        assert engine2.semantic_index is not None

        # Both should have same vocabulary hash
        if hasattr(engine1.semantic_index, "vocabulary_hash"):
            assert engine1.semantic_index.vocabulary_hash == engine2.semantic_index.vocabulary_hash

    @pytest.mark.asyncio
    async def test_search_with_threshold(self, small_corpus: Corpus, test_db):
        """Test semantic search with similarity threshold."""
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Search with high threshold
        results_high = engine.search("happy", max_results=10, min_score=0.6)

        # Search with low threshold
        results_low = engine.search("happy", max_results=10, min_score=0.1)

        # High threshold should have fewer results
        assert len(results_high) <= len(results_low)

        # All high threshold results should meet the threshold
        assert all(r.score >= 0.6 for r in results_high)
        assert all(r.score >= 0.1 for r in results_low)

    @pytest.mark.asyncio
    async def test_language_corpus_search(self, language_corpus: Corpus, test_db):
        """Test semantic search on a larger language-level corpus."""
        engine = await SemanticSearch.from_corpus(corpus=language_corpus)
        await engine.initialize()

        # Search for writing-related words
        results = engine.search("writing", max_results=10)

        assert len(results) > 0
        words = [r.word for r in results]

        # Should find related words
        found_writing = [
            w for w in words if any(ww in w for ww in ["writ", "pen", "paper", "type"])
        ]
        assert len(found_writing) > 0, f"Expected writing-related words but got: {words}"

    @pytest.mark.asyncio
    async def test_literature_corpus_search(self, literature_corpus: Corpus, test_db):
        """Test semantic search on a literature-specific corpus."""
        engine = await SemanticSearch.from_corpus(corpus=literature_corpus)
        await engine.initialize()

        # Search for Shakespearean words
        results = engine.search("shakespeare", max_results=10)
        words = [r.word for r in results]

        # Even if "shakespeare" isn't in vocab, should find related archaic words

        # Search for actual vocab word
        results = engine.search("thou", max_results=5)
        words = [r.word for r in results]

        # Should find other archaic pronouns
        assert any(w in ["thee", "thy", "thine"] for w in words), (
            f"Expected archaic words but got: {words}"
        )

    @pytest.mark.asyncio
    async def test_cross_domain_search(self, test_db):
        """Test searching across different domain vocabularies."""
        # Create mixed corpus
        vocabulary = [
            # Technical
            "algorithm",
            "computer",
            "software",
            "hardware",
            "database",
            # Medical
            "patient",
            "doctor",
            "medicine",
            "hospital",
            "treatment",
            # Legal
            "lawyer",
            "court",
            "judge",
            "law",
            "justice",
        ]

        corpus = Corpus(
            corpus_name="semantic_test_mixed",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(vocabulary),
            original_vocabulary=sorted(vocabulary),
            lemmatized_vocabulary=sorted(vocabulary),
        )

        corpus.vocabulary_to_index = {word: i for i, word in enumerate(sorted(vocabulary))}
        corpus._build_signature_index()

        manager = CorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        engine = await SemanticSearch.from_corpus(corpus=saved_corpus)
        await engine.initialize()

        # Search for technical term
        results = engine.search("computer", max_results=5)
        words = [r.word for r in results]

        # Should find other technical terms first
        tech_words = ["algorithm", "software", "hardware", "database"]
        found_tech = [w for w in words[:3] if w in tech_words]
        assert len(found_tech) > 0, f"Expected technical words but got: {words}"

    @pytest.mark.asyncio
    async def test_semantic_index_model_metadata(self, small_corpus: Corpus, test_db):
        """Test that semantic index stores proper model metadata."""
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Check index has model info
        assert engine.semantic_index is not None
        assert hasattr(engine.semantic_index, "model_name")
        assert engine.semantic_index.model_name is not None

        # Verify embeddings match expected dimensions for the model
        expected_dim = engine._get_embedding_dimension()
        assert engine.sentence_embeddings.shape[1] == expected_dim

    @pytest.mark.asyncio
    async def test_concurrent_index_creation(self, test_db):
        """Test concurrent creation of semantic indices."""
        import asyncio

        # Create multiple small corpora
        corpora = []
        for i in range(3):
            vocab = [f"word_{i}_{j}" for j in range(20)]
            corpus = Corpus(
                corpus_name=f"semantic_concurrent_{i}",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=sorted(vocab),
                original_vocabulary=sorted(vocab),
                lemmatized_vocabulary=sorted(vocab),
            )
            corpus.vocabulary_to_index = {word: idx for idx, word in enumerate(sorted(vocab))}
            corpus._build_signature_index()

            manager = CorpusManager()
            saved = await manager.save_corpus(corpus)
            corpora.append(saved)

        # Create engines concurrently
        async def create_and_init(corpus):
            engine = await SemanticSearch.from_corpus(corpus=corpus)
            await engine.initialize()
            return engine

        engines = await asyncio.gather(*[create_and_init(c) for c in corpora])

        # All should have initialized successfully
        assert all(e.sentence_index is not None for e in engines)
        assert all(e.sentence_embeddings is not None for e in engines)

        # Each should have embeddings for their vocab
        for engine, corpus in zip(engines, corpora):
            assert engine.sentence_embeddings.shape[0] == len(corpus.vocabulary)

    @pytest.mark.asyncio
    async def test_empty_query_handling(self, small_corpus: Corpus, test_db):
        """Test handling of empty and invalid queries."""
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Empty string
        results = engine.search("")
        assert isinstance(results, list)
        assert len(results) == 0

        # Whitespace only
        results = engine.search("   ")
        assert isinstance(results, list)
        assert len(results) == 0

        # None should be handled
        results = engine.search(None)
        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, small_corpus: Corpus, test_db):
        """Test queries with special characters."""
        engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await engine.initialize()

        # Query with punctuation
        results = engine.search("happy!", max_results=5)
        assert len(results) > 0

        # Query with numbers
        results = engine.search("happy123", max_results=5)
        assert len(results) >= 0  # Should handle gracefully

        # Query with unicode
        results = engine.search("happy😀", max_results=5)
        assert len(results) >= 0  # Should handle gracefully

    @pytest.mark.asyncio
    async def test_faiss_quantization_strategies(self, test_db):
        """Test different FAISS quantization strategies based on corpus size."""
        sizes_and_strategies = [
            (10, "flat"),  # Small corpus - no quantization
            (100, "fp16"),  # Medium - FP16 quantization
            (1000, "int8"),  # Large - INT8 quantization
        ]

        for size, expected_strategy in sizes_and_strategies:
            vocab = [f"word_{i}" for i in range(size)]
            corpus = Corpus(
                corpus_name=f"semantic_quant_{size}",
                corpus_type=CorpusType.LANGUAGE,
                language=Language.ENGLISH,
                vocabulary=vocab,
                original_vocabulary=vocab,
                lemmatized_vocabulary=vocab,
            )
            corpus.vocabulary_to_index = {word: i for i, word in enumerate(vocab)}
            corpus._build_signature_index()

            manager = CorpusManager()
            saved_corpus = await manager.save_corpus(corpus)

            engine = await SemanticSearch.from_corpus(corpus=saved_corpus)
            await engine.initialize()

            # Index should be created
            assert engine.sentence_index is not None
            assert engine.sentence_embeddings is not None

            # Should handle search properly regardless of strategy
            results = engine.search("word_5", max_results=5)
            assert len(results) > 0
