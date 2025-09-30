"""Test search performance and correctness with very large corpora (100k+ words)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import CorpusManager
from floridify.models.base import Language
from floridify.search.core import Search
from floridify.search.fuzzy import FuzzySearch


@pytest.mark.slow
class TestLargeCorpusSearch:
    """Test search operations on very large corpora."""

    @pytest_asyncio.fixture
    async def large_corpus_100k(self, test_db) -> Corpus:
        """Large corpus with 100k words."""
        # Generate diverse vocabulary
        vocabulary = []

        # Common English words (simulate frequency distribution)
        common_prefixes = ["pre", "post", "anti", "un", "re", "de", "dis", "mis", "over", "under"]
        common_roots = ["act", "form", "struct", "port", "dict", "ject", "duct", "vene", "cede", "mit"]
        common_suffixes = ["ing", "ed", "er", "est", "ly", "ness", "ment", "tion", "able", "ful"]

        # Generate 100k words with patterns
        for i in range(100000):
            if i < 1000:
                # Very common words (top 1000)
                vocabulary.append(f"common_{i:04d}")
            elif i < 10000:
                # Common words (top 10k)
                prefix = common_prefixes[i % len(common_prefixes)]
                root = common_roots[(i // 10) % len(common_roots)]
                vocabulary.append(f"{prefix}{root}_{i:05d}")
            elif i < 50000:
                # Medium frequency words
                root = common_roots[i % len(common_roots)]
                suffix = common_suffixes[(i // 100) % len(common_suffixes)]
                vocabulary.append(f"{root}{suffix}_{i:05d}")
            else:
                # Rare words
                vocabulary.append(f"rare_word_{i:06d}")

        corpus = Corpus(
            corpus_name="test_large_100k",
            corpus_type=CorpusType.LANGUAGE,
            language=Language.ENGLISH,
            vocabulary=sorted(vocabulary),
            original_vocabulary=sorted(vocabulary),
        )

        # Add frequency data (simulate real distribution)
        word_frequencies = {}
        for idx, word in enumerate(vocabulary):
            if idx < 1000:
                freq = 10000 - idx * 9  # High frequency for common words
            elif idx < 10000:
                freq = 1000 - (idx - 1000) // 10
            elif idx < 50000:
                freq = 100 - (idx - 10000) // 500
            else:
                freq = max(1, 10 - (idx - 50000) // 10000)
            word_frequencies[word] = freq

        corpus.word_frequencies = word_frequencies

        await corpus._rebuild_indices()

        manager = CorpusManager()
        return await manager.save_corpus(corpus)

    @pytest.mark.asyncio
    async def test_exact_search_large_corpus(self, large_corpus_100k, test_db):
        """Test that exact search scales to 100k words."""
        engine = await Search.from_corpus(
            corpus_name=large_corpus_100k.corpus_name,
            semantic=False,
        )

        # Test exact search for various positions in vocabulary
        test_words = [
            "common_0001",  # Very common
            "preact_05123",  # Medium frequency
            "rare_word_099999",  # Rare word
        ]

        for word in test_words:
            if word in large_corpus_100k.vocabulary:
                results = engine.search_exact(word)
                assert len(results) > 0, f"Failed to find {word}"
                assert results[0].word == word

    @pytest.mark.asyncio
    async def test_fuzzy_search_uses_frequency_weighted_sampling(self, large_corpus_100k, test_db):
        """Test that fuzzy search on large corpus uses frequency-weighted sampling."""
        fuzzy_engine = FuzzySearch(min_score=0.7)

        # Search for a typo that should match a common word
        results = fuzzy_engine.search(
            "comon_0001",  # Typo of "common_0001"
            corpus=large_corpus_100k,
            max_results=10,
        )

        # Should find results (frequency-weighted sampling should include common words)
        assert len(results) > 0

        # The algorithm should favor common words due to frequency weighting
        # We added word_frequencies to the corpus, so weighted sampling should work
        words = [r.word for r in results]
        assert any("common_" in w for w in words), (
            "Frequency-weighted sampling should prefer common words"
        )

    @pytest.mark.asyncio
    async def test_prefix_search_large_corpus(self, large_corpus_100k, test_db):
        """Test prefix search efficiency on large corpus."""
        engine = await Search.from_corpus(
            corpus_name=large_corpus_100k.corpus_name,
            semantic=False,
        )

        # Test prefix searches
        prefix_tests = [
            ("common_", 1000),  # Should find ~1000 matches
            ("preact_", 100),  # Moderate number
            ("rare_word_09", 10),  # Small number
        ]

        for prefix, expected_min in prefix_tests:
            results = engine.search_prefix(prefix, max_results=expected_min)
            assert len(results) > 0, f"No results for prefix '{prefix}'"
            assert all(r.startswith(prefix) for r in results), (
                f"All results should start with '{prefix}'"
            )

    @pytest.mark.asyncio
    async def test_corpus_index_integrity_100k(self, large_corpus_100k, test_db):
        """Test that corpus indices remain consistent at 100k scale."""
        # Check vocabulary size
        assert len(large_corpus_100k.vocabulary) == 100000

        # Check index consistency
        assert len(large_corpus_100k.vocabulary_to_index) == 100000

        # Verify bidirectional mapping
        for i in range(0, 100000, 1000):  # Sample every 1000th word
            word = large_corpus_100k.vocabulary[i]
            idx = large_corpus_100k.vocabulary_to_index[word]
            assert idx == i, f"Index mismatch for {word}: expected {i}, got {idx}"
            assert large_corpus_100k.vocabulary[idx] == word

    @pytest.mark.asyncio
    async def test_memory_efficiency_100k(self, large_corpus_100k, test_db):
        """Test that 100k corpus doesn't cause excessive memory usage."""
        import sys

        # Get corpus size in memory
        corpus_size = sys.getsizeof(large_corpus_100k.vocabulary)

        # Should be reasonable for 100k strings (rough estimate: <50MB for vocabulary list)
        # Each word ~50 chars avg = 5MB raw + Python overhead
        max_reasonable_size = 50 * 1024 * 1024  # 50MB

        assert corpus_size < max_reasonable_size, (
            f"Corpus vocabulary uses {corpus_size / 1024 / 1024:.2f}MB, "
            f"expected < {max_reasonable_size / 1024 / 1024:.2f}MB"
        )

    @pytest.mark.asyncio
    async def test_concurrent_access_large_corpus(self, large_corpus_100k, test_db):
        """Test that large corpus can handle concurrent searches."""
        engine = await Search.from_corpus(
            corpus_name=large_corpus_100k.corpus_name,
            semantic=False,
        )

        # Simulate concurrent searches (in sequence due to Python GIL)
        queries = [
            "common_0001",
            "preact_05123",
            "formtion_25000",
            "rare_word_099999",
        ]

        results_batch = []
        for query in queries:
            if query in large_corpus_100k.vocabulary:
                results = engine.search_exact(query)
                results_batch.append(results)
            else:
                results = engine.search_fuzzy(query, max_results=5)
                results_batch.append(results)

        # All queries should return results
        assert all(len(r) > 0 for r in results_batch)

    @pytest.mark.asyncio
    @pytest.mark.timeout(30)  # Should complete within 30 seconds
    async def test_search_performance_100k(self, large_corpus_100k, test_db):
        """Test that search operations complete in reasonable time on 100k corpus."""
        import time

        engine = await Search.from_corpus(
            corpus_name=large_corpus_100k.corpus_name,
            semantic=False,
        )

        # Test exact search performance (should be O(1) hash lookup)
        start = time.perf_counter()
        results = engine.search_exact("common_0100")
        exact_time = time.perf_counter() - start

        # Exact search should be very fast (<10ms even on 100k corpus)
        assert exact_time < 0.01, f"Exact search took {exact_time*1000:.2f}ms, expected <10ms"

        # Test prefix search performance
        start = time.perf_counter()
        results = engine.search_prefix("common_", max_results=100)
        prefix_time = time.perf_counter() - start

        # Prefix search should be fast (<100ms)
        assert prefix_time < 0.1, f"Prefix search took {prefix_time*1000:.2f}ms, expected <100ms"

        # Test fuzzy search performance (more expensive)
        start = time.perf_counter()
        results = engine.search_fuzzy("comon_0100", max_results=10)
        fuzzy_time = time.perf_counter() - start

        # Fuzzy search with sampling should complete in reasonable time (<2s)
        assert fuzzy_time < 2.0, f"Fuzzy search took {fuzzy_time:.2f}s, expected <2s"