"""Semantic vocab embedding lookup -- correctness, diacritics, and performance."""

from __future__ import annotations

import time

import numpy as np
import pytest

from tests.search.conftest import (
    SEMANTIC_QUERIES,
    VOCAB_TINY,
    _fmt,
    _label,
    _make_corpus,
    _make_engine,
    _run_timed_async,
)


@pytest.mark.asyncio
class TestSemanticVocabLookup:
    """Verify the vocabulary embedding lookup optimization."""

    async def test_in_vocab_returns_embedding(self, test_db):
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat", "apple", "banana"]
        corpus = await _make_corpus(test_db, "sem_invocab", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb = search._lookup_vocab_embedding("happy")
        assert emb is not None, "In-vocab 'happy' should return embedding"
        assert isinstance(emb, np.ndarray)
        assert emb.shape[0] > 0

    async def test_case_insensitive_lookup(self, test_db):
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["happy", "sad", "dog"]
        corpus = await _make_corpus(test_db, "sem_case", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        # "Happy" (capitalized) should still hit the fast path
        emb = search._lookup_vocab_embedding("Happy")
        assert emb is not None, "Case-insensitive lookup failed for 'Happy'"

    async def test_oov_returns_none(self, test_db):
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat"]
        corpus = await _make_corpus(test_db, "sem_oov", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        assert search._lookup_vocab_embedding("xylophone") is None

    async def test_correct_shape(self, test_db):
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat"]
        corpus = await _make_corpus(test_db, "sem_shape", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb = search._lookup_vocab_embedding("dog")
        if emb is not None and search.sentence_embeddings is not None:
            assert emb.shape == (search.sentence_embeddings.shape[1],)

    async def test_no_corpus_returns_none(self):
        from floridify.search.semantic.search import SemanticSearch

        search = SemanticSearch()
        assert search._lookup_vocab_embedding("anything") is None

    async def test_embeddings_differ_for_different_words(self, test_db):
        """Distinct words should have distinct pre-computed embeddings."""
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["happy", "sad", "dog", "cat", "mountain", "river"]
        corpus = await _make_corpus(test_db, "sem_distinct", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb_happy = search._lookup_vocab_embedding("happy")
        emb_dog = search._lookup_vocab_embedding("dog")
        assert emb_happy is not None and emb_dog is not None
        # Cosine distance should be non-trivial
        cos_sim = float(
            np.dot(emb_happy, emb_dog) / (np.linalg.norm(emb_happy) * np.linalg.norm(emb_dog))
        )
        assert cos_sim < 0.99, f"'happy' and 'dog' embeddings too similar: {cos_sim:.4f}"


@pytest.mark.asyncio
class TestSemanticSearchPerf:
    """Semantic search performance tests.

    These use function-scoped test_db because SemanticSearch.initialize()
    persists embeddings to MongoDB via _save_embeddings_to_index().
    """

    async def test_semantic_uncached_small(self, test_db):
        from floridify.search.semantic.search import SemanticSearch

        corpus = await _make_corpus(test_db, "sem_perf_uncached", VOCAB_TINY)
        engine = await _make_engine(corpus)

        semantic = await SemanticSearch.from_corpus(corpus=corpus)
        await semantic.initialize()
        engine.semantic_search = semantic
        engine._semantic_ready = True

        # Warm model, clear cache
        await engine.search_semantic("warmup", max_results=10)
        semantic.result_cache.clear()
        semantic.result_cache_order.clear()

        async def run():
            results = []
            for q in SEMANTIC_QUERIES:
                unique_q = f"{q}_{time.perf_counter_ns()}"
                r = await engine.search_semantic(unique_q, max_results=10)
                results.extend(r)
            return results

        stats, _ = await _run_timed_async(run, iterations=10, warmup=2)
        print(
            f"\n  SEMANTIC uncached {_label(corpus):>5} ({len(SEMANTIC_QUERIES)}q): {_fmt(stats)}"
        )

    async def test_semantic_cached_small(self, test_db):
        from floridify.search.semantic.search import SemanticSearch

        corpus = await _make_corpus(test_db, "sem_perf_cached", VOCAB_TINY)
        engine = await _make_engine(corpus)

        semantic = await SemanticSearch.from_corpus(corpus=corpus)
        await semantic.initialize()
        engine.semantic_search = semantic
        engine._semantic_ready = True

        # Populate cache
        for q in SEMANTIC_QUERIES:
            await engine.search_semantic(q, max_results=10)

        async def run():
            return [await engine.search_semantic(q, max_results=10) for q in SEMANTIC_QUERIES]

        stats, _ = await _run_timed_async(run, iterations=50, warmup=5)
        print(
            f"\n  SEMANTIC cached   {_label(corpus):>5} ({len(SEMANTIC_QUERIES)}q): {_fmt(stats)}"
        )


@pytest.mark.asyncio
class TestSemanticVocabLookupDiacritics:
    """Verify the O(1) vocab embedding lookup handles diacritics correctly."""

    async def test_diacriticized_query_hits_fast_path(self, test_db):
        """Query 'cafe' should hit O(1) lookup for 'cafe' in vocabulary."""
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["cafe\u0301", "nai\u0308ve", "happy", "sad", "dog"]
        corpus = await _make_corpus(test_db, "sem_diacritics", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        # "cafe" normalizes to "cafe" which is in vocabulary
        emb = search._lookup_vocab_embedding("cafe\u0301")
        assert emb is not None, "Diacriticized 'cafe' should hit O(1) fast path"

    async def test_combining_character_query_hits_fast_path(self, test_db):
        """Query with combining acute (e + U+0301) should hit fast path."""
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["cafe\u0301", "happy", "sad"]
        corpus = await _make_corpus(test_db, "sem_combining", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        # "cafe\u0301" = "cafe" with combining character -> normalizes to "cafe"
        emb = search._lookup_vocab_embedding("cafe\u0301")
        assert emb is not None, "Combining char query should hit O(1) fast path"

    async def test_uppercase_diacriticized_query(self, test_db):
        """Query 'CAFE' should hit O(1) fast path."""
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["cafe\u0301", "happy"]
        corpus = await _make_corpus(test_db, "sem_upper_dia", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        emb = search._lookup_vocab_embedding("CAFE\u0301")
        assert emb is not None, "Uppercase diacriticized 'CAFE' should hit fast path"

    async def test_multi_word_query_misses_fast_path(self, test_db):
        """Multi-word query like 'ice cream' should return None (not in single-word vocab)."""
        from floridify.search.semantic.search import SemanticSearch

        vocab = ["ice", "cream", "happy"]
        corpus = await _make_corpus(test_db, "sem_multiword", vocab)

        search = await SemanticSearch.from_corpus(corpus=corpus)
        await search.initialize()

        # "ice cream" is not a single vocab entry
        emb = search._lookup_vocab_embedding("ice cream")
        assert emb is None, "Multi-word should miss fast path (falls through to encoder)"

        # But individual words should hit
        emb_ice = search._lookup_vocab_embedding("ice")
        assert emb_ice is not None
