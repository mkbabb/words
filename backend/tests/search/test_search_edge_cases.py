"""Edge cases -- empty corpus, max_results=0, degenerate inputs, index build perf."""

from __future__ import annotations

import pytest

from tests.search.conftest import (
    _fmt,
    _label,
    _make_corpus,
    _make_engine,
    _run_timed_async,
)


@pytest.mark.asyncio
class TestEdgeCases:
    """Edge cases that could crash or produce nonsensical results."""

    async def test_single_word_corpus(self, test_db):
        corpus = await _make_corpus(test_db, "edge_single", ["apple"])
        engine = await _make_engine(corpus)
        results = engine.search_exact("apple")
        assert len(results) == 1
        assert results[0].word.lower() == "apple"

    async def test_single_word_corpus_fuzzy(self, test_db):
        corpus = await _make_corpus(test_db, "edge_single_fz", ["apple"])
        engine = await _make_engine(corpus)
        results = engine.search_fuzzy("aple", max_results=5)
        assert len(results) >= 1
        assert results[0].word.lower() == "apple"

    async def test_max_results_zero_exact(self, small_engine):
        results = small_engine.search_exact("apple")
        # Exact always returns 0 or 1, no max_results param; just verify no crash
        assert isinstance(results, list)

    async def test_max_results_one(self, small_engine):
        results = small_engine.search_fuzzy("apple", max_results=1)
        assert len(results) <= 1

    async def test_duplicate_vocabulary_handled(self, test_db):
        """Corpus with duplicate words should deduplicate in create()."""
        corpus = await _make_corpus(
            test_db, "edge_dupes", ["apple", "apple", "banana", "banana", "cherry"]
        )
        assert len(set(corpus.vocabulary)) == len(corpus.vocabulary), "Vocabulary has duplicates"

    async def test_all_same_length_words(self, test_db):
        """Corpus where all words are same length -- length buckets degenerate case."""
        vocab = ["cat", "bat", "hat", "mat", "rat", "sat", "pat", "fat", "vat", "tab"]
        corpus = await _make_corpus(test_db, "edge_samelength", vocab)
        engine = await _make_engine(corpus)
        results = engine.search_fuzzy("cap", max_results=5)
        assert len(results) >= 1
        # Should find cat (edit distance 1)
        words = [r.word.lower() for r in results]
        assert "cat" in words, f"Expected 'cat' for typo 'cap', got {words}"

    async def test_very_long_word_in_corpus(self, test_db):
        """Corpus with 200+ char word should not crash."""
        long_word = "a" * 200
        corpus = await _make_corpus(test_db, "edge_longword", [long_word, "apple"])
        engine = await _make_engine(corpus)
        results = engine.search_exact(long_word)
        assert len(results) == 1

    async def test_transposition_typo(self, small_engine):
        """Adjacent letter swap 'appel' should find 'apple'."""
        results = small_engine.search_fuzzy("appel", max_results=5)
        words = [r.word.lower() for r in results]
        assert "apple" in words, f"Transposition 'appel' should find 'apple', got {words}"

    async def test_double_letter_typo(self, small_engine):
        """Double letter 'appple' should find 'apple'."""
        results = small_engine.search_fuzzy("appple", max_results=5)
        words = [r.word.lower() for r in results]
        assert "apple" in words, f"Double letter 'appple' should find 'apple', got {words}"

    async def test_missing_letter_typo(self, small_engine):
        """Missing letter 'aple' should find 'apple'."""
        results = small_engine.search_fuzzy("aple", max_results=5)
        words = [r.word.lower() for r in results]
        assert "apple" in words

    async def test_substitution_typo(self, small_engine):
        """Substitution 'azple' should find 'apple'."""
        results = small_engine.search_fuzzy("azple", max_results=5)
        words = [r.word.lower() for r in results]
        assert "apple" in words, f"Substitution 'azple' should find 'apple', got {words}"


@pytest.mark.asyncio
class TestTrieIndexBuild:
    """Index build timing tests."""

    async def test_build_small(self, small_corpus):
        async def build():
            return await _make_engine(small_corpus)

        stats, _ = await _run_timed_async(build, iterations=10, warmup=1)
        print(f"\n  BUILD  {_label(small_corpus):>5}: {_fmt(stats)}")

    async def test_build_medium(self, medium_corpus):
        async def build():
            return await _make_engine(medium_corpus)

        stats, _ = await _run_timed_async(build, iterations=5, warmup=1)
        print(f"\n  BUILD {_label(medium_corpus):>5}: {_fmt(stats)}")

    async def test_build_large(self, large_corpus):
        async def build():
            return await _make_engine(large_corpus)

        stats, _ = await _run_timed_async(build, iterations=3, warmup=1)
        print(f"\n  BUILD {_label(large_corpus):>5}: {_fmt(stats)}")
