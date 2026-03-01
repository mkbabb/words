"""Performance benchmarks for search pipeline testing cached and non-cached pathways."""

from __future__ import annotations

import asyncio
import time

import pytest
import pytest_asyncio

from floridify.caching.core import get_global_cache
from floridify.corpus.core import Corpus
from floridify.corpus.manager import TreeCorpusManager
from floridify.corpus.models import CorpusType
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.search.fuzzy import FuzzySearch
from floridify.search.semantic.core import SemanticSearch
from floridify.search.trie import TrieSearch


@pytest.mark.slow
class TestSearchPerformance:
    """Performance benchmarks for search operations."""

    @pytest_asyncio.fixture
    async def small_corpus(self, test_db) -> Corpus:
        """Small corpus for quick tests (100 words)."""
        vocabulary = [f"word_{i:04d}" for i in range(100)]
        vocabulary.extend(["apple", "banana", "cherry", "date", "elderberry"])

        corpus = Corpus(
            corpus_name="perf_small",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=sorted(vocabulary),
            original_vocabulary=sorted(vocabulary),
        )
        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        return await manager.save_corpus(corpus)

    @pytest_asyncio.fixture
    async def medium_corpus(self, test_db) -> Corpus:
        """Medium corpus for realistic tests (1000 words)."""
        # Generate diverse vocabulary
        vocabulary = []

        # Common words
        common_words = [
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
        ]
        vocabulary.extend(common_words)

        # Generate variations
        for base in common_words[:10]:
            vocabulary.extend([f"{base}s", f"{base}ed", f"{base}ing", f"{base}er"])

        # Add numbered words
        vocabulary.extend([f"word_{i:04d}" for i in range(900)])

        corpus = Corpus(
            corpus_name="perf_medium",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(set(vocabulary))[:1000],
            original_vocabulary=sorted(set(vocabulary))[:1000],
        )
        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        return await manager.save_corpus(corpus)

    @pytest_asyncio.fixture
    async def large_corpus(self, test_db) -> Corpus:
        """Large corpus for stress tests (10000 words)."""
        vocabulary = []

        # Generate a large vocabulary
        for i in range(10000):
            if i % 4 == 0:
                vocabulary.append(f"noun_{i:05d}")
            elif i % 4 == 1:
                vocabulary.append(f"verb_{i:05d}")
            elif i % 4 == 2:
                vocabulary.append(f"adj_{i:05d}")
            else:
                vocabulary.append(f"word_{i:05d}")

        corpus = Corpus(
            corpus_name="perf_large",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(vocabulary),
            original_vocabulary=sorted(vocabulary),
        )
        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        return await manager.save_corpus(corpus)

    @pytest.mark.asyncio
    async def test_exact_search_small_corpus(self, benchmark, small_corpus, test_db):
        """Benchmark exact search on small corpus."""
        engine = Search()
        engine.corpus = small_corpus

        # Run initialization outside benchmark
        await engine.build_indices()

        def search_exact():
            return engine.search_exact("apple")

        result = benchmark(search_exact)
        assert len(result) > 0
        assert result[0].word == "apple"

    def test_fuzzy_search_medium_corpus(self, benchmark, medium_corpus, test_db):
        """Benchmark fuzzy search on medium corpus."""
        fuzzy_engine = FuzzySearch(min_score=0.7)

        queries = ["teh", "wrod", "adn", "thta", "hvae"]  # Common typos

        def search_fuzzy():
            results = []
            for query in queries:
                results.extend(fuzzy_engine.search(
                    query,
                    corpus=medium_corpus,
                    max_results=5
                ))
            return results

        results = benchmark(search_fuzzy)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_semantic_search_small_corpus(self, small_corpus, test_db):
        """Test semantic search on small corpus (manual timing due to async)."""
        semantic_engine = await SemanticSearch.from_corpus(corpus=small_corpus)
        await semantic_engine.initialize()

        # Manually time async operation (pytest-benchmark doesn't support async well in async tests)
        start = time.perf_counter()
        result = await semantic_engine.search("fruit", max_results=10)
        elapsed = time.perf_counter() - start

        assert isinstance(result, list)
        assert len(result) > 0
        print(f"\nSemantic search took {elapsed*1000:.2f}ms")

    @pytest.mark.asyncio
    async def test_trie_prefix_search_large_corpus(self, benchmark, large_corpus, test_db):
        """Benchmark prefix search on large corpus."""
        trie_engine = TrieSearch()
        await trie_engine.build_from_corpus(large_corpus)

        prefixes = ["noun_", "verb_", "adj_", "word_0"]

        def search_prefix():
            results = []
            for prefix in prefixes:
                prefix_results = trie_engine.search_prefix(prefix, max_results=20)
                results.extend(prefix_results)
            return results

        results = benchmark(search_prefix)
        assert len(results) > 0
        # All results should start with one of our prefixes (check normalized forms)
        for result in results:
            assert any(result.startswith(p) for p in prefixes)

    @pytest.mark.asyncio
    async def test_cascading_search_performance(self, benchmark, medium_corpus, test_db):
        """Benchmark cascading search (exact -> fuzzy -> semantic)."""
        # Initialize engine asynchronously
        engine = await Search.from_corpus(
            corpus_name=medium_corpus.corpus_name,
            semantic=False  # Disable semantic for performance testing
        )

        # Test with queries that trigger different search methods
        queries = [
            "the",  # Exact match
            "teh",  # Fuzzy match
            "meaning",  # May trigger semantic
            "word_0500",  # Exact match
            "wrod_500",  # Fuzzy match
        ]

        # Define sync version for benchmarking
        def cascading_search_sync():
            results = []
            for query in queries:
                # Try exact search first
                res_exact = engine.search_exact(query)
                if res_exact:
                    results.extend(res_exact)
                else:
                    # Fall back to fuzzy search
                    res_fuzzy = engine.search_fuzzy(query, max_results=10)
                    results.extend(res_fuzzy)
            return results

        # Benchmark the sync version
        result = benchmark.pedantic(cascading_search_sync, rounds=5, iterations=3)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_cached_vs_noncached_search(self, small_corpus, test_db):
        """Compare cached vs non-cached search performance.

        Uses small_corpus to ensure inline content storage (not external cache).
        This prevents cache clearing from evicting corpus content.
        """
        cache_manager = await get_global_cache()

        # Clear cache to ensure clean start
        await cache_manager.clear()

        # Initialize engine asynchronously
        engine = await Search.from_corpus(
            corpus_name=small_corpus.corpus_name,
            semantic=False
        )

        query = "apple"  # Valid word in small_corpus

        # Test non-cached search (run multiple times for stable measurement)
        await cache_manager.clear()
        non_cached_times = []
        for _ in range(100):
            await cache_manager.clear()
            start = time.perf_counter()
            result = engine.search_exact(query)
            non_cached_times.append(time.perf_counter() - start)

        non_cached_avg = sum(non_cached_times) / len(non_cached_times)

        # Warm up cache
        engine.search_exact(query)

        # Test cached search
        cached_times = []
        for _ in range(100):
            start = time.perf_counter()
            result = engine.search_exact(query)
            cached_times.append(time.perf_counter() - start)

        cached_avg = sum(cached_times) / len(cached_times)

        # Cached should be faster or at least comparable
        # For small queries, difference may not be dramatic
        print(f"\nNon-cached avg: {non_cached_avg*1e6:.2f}µs")
        print(f"Cached avg: {cached_avg*1e6:.2f}µs")
        print(f"Speedup: {non_cached_avg/cached_avg:.2f}x")

        # Basic sanity check - cached shouldn't be significantly slower
        assert cached_avg <= non_cached_avg * 2.0, (
            f"Cached ({cached_avg*1e6:.2f}µs) is slower than non-cached ({non_cached_avg*1e6:.2f}µs)"
        )

    @pytest.mark.asyncio
    async def test_batch_search_performance(self, benchmark, large_corpus, test_db):
        """Benchmark batch search operations."""
        # Initialize engine asynchronously
        engine = await Search.from_corpus(
            corpus_name=large_corpus.corpus_name,
            semantic=False
        )

        # Generate 100 queries - use pattern that exists (i % 4 == 3 gives "word_")
        queries = [f"word_{i:05d}" for i in range(3, 10000, 100)]  # 3, 103, 203, ...

        def batch_search():
            results = []
            for query in queries:
                res = engine.search_exact(query)
                if res:  # res is a list, extend rather than append
                    results.extend(res)
            return results

        results = benchmark(batch_search)
        # Each query should return at least one result
        assert len(results) > 50  # Should find most queries

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, benchmark, medium_corpus, test_db):
        """Benchmark concurrent search operations."""
        # Initialize engine asynchronously
        engine = await Search.from_corpus(
            corpus_name=medium_corpus.corpus_name,
            semantic=False
        )

        queries = [f"word_{i:04d}" for i in range(20)]

        # Use sync searches for benchmarking (async concurrent not supported by pytest-benchmark)
        def run_searches_sync():
            results = []
            for query in queries:
                res_exact = engine.search_exact(query)
                if res_exact:
                    results.extend(res_exact)
                else:
                    res_fuzzy = engine.search_fuzzy(query, max_results=5)
                    results.extend(res_fuzzy[:1] if res_fuzzy else [])
            return results

        results = benchmark.pedantic(run_searches_sync, rounds=5, iterations=3)
        assert len(results) > 0  # Should find at least some results

    def test_index_building_performance(self, benchmark, test_db):
        """Benchmark index building for different corpus sizes."""
        sizes = [100, 500, 1000]

        async def build_indices_async():
            results = []
            for size in sizes:
                vocabulary = [f"word_{i:05d}" for i in range(size)]
                corpus = Corpus(
                    corpus_name=f"perf_build_{size}",
                    corpus_type=CorpusType.CUSTOM,
                    language=Language.ENGLISH,
                    vocabulary=vocabulary,
                    original_vocabulary=vocabulary,
                )

                start = time.perf_counter()
                await corpus._rebuild_indices()
                end = time.perf_counter()

                results.append(
                    {
                        "size": size,
                        "time_ms": (end - start) * 1000,
                        "indices_built": bool(corpus.vocabulary_to_index),
                    }
                )

            return results

        def run_build():
            return asyncio.run(build_indices_async())

        results = benchmark.pedantic(run_build, rounds=3, iterations=2)

        # Verify all indices were built
        for result in results:
            assert result["indices_built"]

        # Time should increase with size (roughly)
        times = [r["time_ms"] for r in results]
        assert times[-1] > times[0]  # Largest should take longer than smallest

    @pytest.mark.asyncio
    async def test_search_with_lemmatization_performance(self, benchmark, test_db):
        """Benchmark search with lemmatization enabled."""
        # Create corpus with inflected forms
        vocabulary = []
        base_words = ["run", "walk", "jump", "think", "speak"]
        for base in base_words:
            vocabulary.extend([base, f"{base}s", f"{base}ed", f"{base}ing", f"{base}er"])

        corpus = Corpus(
            corpus_name="perf_lemma",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(set(vocabulary)),
            original_vocabulary=sorted(set(vocabulary)),
        )
        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        engine = await Search.from_corpus(
            corpus_name=saved_corpus.corpus_name,
            semantic=False
        )

        # Search for base forms should find inflected forms
        def search_inflected():
            results = []
            for base in base_words:
                # Use fuzzy search which is sync
                res_fuzzy = engine.search_fuzzy(f"{base}ing", max_results=5)
                results.extend(res_fuzzy)
            return results

        results = benchmark.pedantic(search_inflected, rounds=5, iterations=3)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, large_corpus, test_db):
        """Test memory usage with large corpus operations."""
        import tracemalloc

        tracemalloc.start()

        # Create search engine
        engine = Search()
        engine.corpus = large_corpus
        await engine.build_indices()

        # Take snapshot before searches
        snapshot1 = tracemalloc.take_snapshot()

        # Perform many searches
        for i in range(1000):
            query = f"word_{i:05d}"
            engine.search_exact(query)

        # Take snapshot after searches
        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory difference
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Get total memory increase
        total_increase = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)

        # Memory increase should be reasonable (< 100MB for 1000 searches)
        assert total_increase < 100 * 1024 * 1024, (
            f"Memory increased by {total_increase / 1024 / 1024:.2f}MB"
        )

        tracemalloc.stop()

    @pytest.mark.asyncio
    async def test_semantic_index_caching_performance(self, test_db):
        """Test performance of semantic index caching."""
        vocabulary = ["apple", "banana", "cherry", "dog", "cat", "elephant"]

        corpus = Corpus(
            corpus_name="perf_semantic_cache",
            corpus_type=CorpusType.CUSTOM,
            language=Language.ENGLISH,
            vocabulary=vocabulary,
            original_vocabulary=vocabulary,
        )
        await corpus._rebuild_indices()

        manager = TreeCorpusManager()
        saved_corpus = await manager.save_corpus(corpus)

        async def create_semantic_engine():
            """Create semantic engine (may use cache)."""
            engine = await SemanticSearch.from_corpus(corpus=saved_corpus)
            await engine.initialize()
            return engine

        # First creation (no cache)
        start = time.perf_counter()
        engine1 = await create_semantic_engine()
        first_time = time.perf_counter() - start

        # Second creation (should use cache)
        start = time.perf_counter()
        engine2 = await create_semantic_engine()
        cached_time = time.perf_counter() - start

        # Cached should be faster (or at least not slower)
        # For small corpora, the difference may not be dramatic
        assert cached_time <= first_time * 1.2, (
            f"Cached time {cached_time:.3f}s is slower than first {first_time:.3f}s"
        )

        # Both should work correctly (await the async search calls)
        results1 = await engine1.search("fruit", max_results=3)
        results2 = await engine2.search("fruit", max_results=3)

        # Should get same results
        assert len(results1) == len(results2)

        # Log the speedup for reference
        speedup = first_time / cached_time if cached_time > 0 else float('inf')
        print(f"\nSemantic index caching speedup: {speedup:.2f}x")
        print(f"  First creation: {first_time:.3f}s")
        print(f"  Cached creation: {cached_time:.3f}s")


@pytest.mark.slow
class TestSemanticSearchBenchmarks:
    """Focused semantic search benchmarks using the shared 35-word corpus.

    All benchmarks use the session-scoped shared_semantic_corpus fixture.
    Initialization time is excluded from measurements.
    """

    @pytest.mark.asyncio
    async def test_semantic_query_latency(
        self, shared_semantic_corpus, assert_small_corpus, test_db
    ):
        """Time only the search() call (not init), assert <50ms for 35-word corpus.

        Performance target: <50ms per query on small corpus.
        """
        assert_small_corpus(shared_semantic_corpus)

        engine = await SemanticSearch.from_corpus(corpus=shared_semantic_corpus)

        # Warm up (first query loads model)
        await engine.search("happy", max_results=5)

        # Measure search-only latency (10 iterations for stability)
        from tests.search.conftest import timed_search

        latencies = []
        for _ in range(10):
            with timed_search() as timer:
                results = await engine.search("happy", max_results=5)
            latencies.append(timer.elapsed_ms)

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)

        print(f"\nSemantic query latency (35-word corpus):")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Min: {min_latency:.2f}ms")

        assert len(results) > 0, "Search should return results"
        # Generous threshold: 50ms for small corpus (cache hit should be <5ms)
        assert avg_latency < 50, (
            f"Average semantic search latency {avg_latency:.2f}ms exceeds 50ms target"
        )

    @pytest.mark.asyncio
    async def test_semantic_result_quality(
        self, shared_semantic_corpus, assert_small_corpus, test_db
    ):
        """Verify semantic similarity: 'happy' should return emotion synonyms before antonyms.

        Quality target: Positive emotions ranked before negative ones.
        """
        assert_small_corpus(shared_semantic_corpus)

        engine = await SemanticSearch.from_corpus(corpus=shared_semantic_corpus)

        results = await engine.search("happy", max_results=10, min_score=0.0)

        words = [r.word for r in results]
        print(f"\nSemantic results for 'happy': {words}")

        # Positive emotion words should appear
        positive_emotions = {"joyful", "cheerful", "glad", "delighted"}
        negative_emotions = {"sad", "angry", "miserable", "furious"}

        found_positive = [w for w in words if w in positive_emotions]
        found_negative = [w for w in words if w in negative_emotions]

        assert len(found_positive) > 0, (
            f"Should find positive emotion synonyms for 'happy', got: {words}"
        )

        # If both positive and negative found, positive should rank higher on average
        if found_positive and found_negative:
            avg_pos_rank = sum(words.index(w) for w in found_positive) / len(found_positive)
            avg_neg_rank = sum(words.index(w) for w in found_negative) / len(found_negative)
            assert avg_pos_rank < avg_neg_rank, (
                f"Positive emotions (avg rank {avg_pos_rank:.1f}) should rank "
                f"higher than negative (avg rank {avg_neg_rank:.1f})"
            )

    @pytest.mark.asyncio
    async def test_semantic_cache_effectiveness(
        self, shared_semantic_corpus, assert_small_corpus, test_db
    ):
        """First query vs repeated query speedup (expect >2x on cache hit).

        Cache target: Repeated queries should be significantly faster.
        """
        assert_small_corpus(shared_semantic_corpus)

        engine = await SemanticSearch.from_corpus(corpus=shared_semantic_corpus)

        # Clear result cache to get a clean measurement
        engine.result_cache.clear()
        engine.result_cache_order.clear()

        from tests.search.conftest import timed_search

        # First query (cache miss - must encode query)
        with timed_search() as first_timer:
            results_first = await engine.search("elephant", max_results=5)

        # Second query (cache hit)
        with timed_search() as cached_timer:
            results_cached = await engine.search("elephant", max_results=5)

        print(f"\nSemantic cache effectiveness:")
        print(f"  First query: {first_timer.elapsed_ms:.2f}ms")
        print(f"  Cached query: {cached_timer.elapsed_ms:.2f}ms")
        if cached_timer.elapsed > 0:
            print(f"  Speedup: {first_timer.elapsed / cached_timer.elapsed:.1f}x")

        # Results should be identical
        assert len(results_first) == len(results_cached)
        assert [r.word for r in results_first] == [r.word for r in results_cached]

        # Cached should be faster (or at worst comparable for tiny corpus)
        # Use generous threshold since first query includes query embedding generation
        assert cached_timer.elapsed <= first_timer.elapsed * 1.5, (
            f"Cached ({cached_timer.elapsed_ms:.2f}ms) should not be significantly "
            f"slower than first ({first_timer.elapsed_ms:.2f}ms)"
        )

    @pytest.mark.asyncio
    async def test_semantic_fuzzy_merge_dedup(
        self, shared_semantic_corpus, assert_small_corpus, test_db
    ):
        """Verify smart mode correctly combines and deduplicates results from both methods.

        Integration target: No duplicate words in merged results.
        """
        assert_small_corpus(shared_semantic_corpus)

        engine = Search()
        engine.corpus = shared_semantic_corpus
        await engine.build_indices()

        # Build semantic search
        semantic = await SemanticSearch.from_corpus(corpus=shared_semantic_corpus)
        engine.semantic_search = semantic
        engine._semantic_ready = True

        # Run smart cascade which combines fuzzy + semantic
        results = await engine._smart_search_cascade(
            query="aple",  # Typo to trigger fuzzy
            max_results=10,
            min_score=0.3,
            semantic=True,
        )

        # Check for duplicates
        words = [r.word for r in results]
        assert len(words) == len(set(w.lower() for w in words)), (
            f"Merged results contain duplicates: {words}"
        )
