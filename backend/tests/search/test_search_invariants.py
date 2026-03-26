"""Search invariants -- get_candidates, lemma index, and trie index sort correctness."""

from __future__ import annotations

import pytest

from floridify.search.trie.index import TrieIndex

from tests.search.conftest import (
    EXACT_QUERIES,
    EXACT_QUERIES_LARGE,
    FUZZY_QUERIES,
    _SEED_WORDS,
    _label,
    _make_corpus,
    VOCAB_TINY,
)


@pytest.mark.asyncio
class TestGetCandidates:
    """Verify get_candidates() collects from ALL four stages at every corpus size."""

    # --- Invariant: length buckets always contribute ---

    async def test_length_buckets_always_present_tiny(self, tiny_corpus):
        cands = tiny_corpus.get_candidates("aple", max_results=100)
        words = set(tiny_corpus.get_words_by_indices(cands))
        assert len(cands) > 0
        assert any(3 <= len(w) <= 6 for w in words), f"No similar-length words: {words}"

    async def test_length_buckets_always_present_large(self, large_corpus):
        cands = large_corpus.get_candidates("aple", max_results=300)
        words = set(large_corpus.get_words_by_indices(cands))
        assert len(cands) > 0
        assert any(3 <= len(w) <= 6 for w in words)

    # --- Invariant: direct matches always included ---

    @pytest.mark.parametrize("word", EXACT_QUERIES[:5])
    async def test_direct_match_in_candidates_small(self, small_corpus, word):
        cands = small_corpus.get_candidates(word, max_results=50)
        words = set(small_corpus.get_words_by_indices(cands))
        assert word in words, f"Direct match '{word}' missing from candidates"

    @pytest.mark.parametrize("word", EXACT_QUERIES[:5] + EXACT_QUERIES_LARGE[:3])
    async def test_direct_match_in_candidates_large(self, large_corpus, word):
        cands = large_corpus.get_candidates(word, max_results=50)
        words = set(large_corpus.get_words_by_indices(cands))
        assert word in words, (
            f"Direct match '{word}' evicted from candidates at 278K "
            f"(got {len(cands)} candidates, sample: {list(words)[:5]})"
        )

    # --- Invariant: max_results cap is respected ---

    @pytest.mark.parametrize("cap", [1, 5, 20, 50])
    async def test_max_results_cap_small(self, small_corpus, cap):
        cands = small_corpus.get_candidates("test", max_results=cap)
        assert len(cands) <= cap

    @pytest.mark.parametrize("cap", [1, 5, 20, 50])
    async def test_max_results_cap_large(self, large_corpus, cap):
        cands = large_corpus.get_candidates("test", max_results=cap)
        assert len(cands) <= cap

    # --- Invariant: empty / whitespace queries return empty ---

    async def test_empty_query(self, tiny_corpus):
        assert tiny_corpus.get_candidates("") == []
        assert tiny_corpus.get_candidates("   ") == []

    # --- Invariant: no empty candidates for ANY seed word at any scale ---

    @pytest.mark.parametrize("word", _SEED_WORDS[:20])
    async def test_never_empty_for_seed_words_small(self, small_corpus, word):
        cands = small_corpus.get_candidates(word, max_results=50)
        assert len(cands) > 0, f"Empty candidates for seed word '{word}' at 10K"

    @pytest.mark.parametrize("word", _SEED_WORDS[:10])
    async def test_never_empty_for_seed_words_large(self, large_corpus, word):
        cands = large_corpus.get_candidates(word, max_results=50)
        assert len(cands) > 0, f"Empty candidates for seed word '{word}' at 278K"

    # --- Regression: typo queries should also get candidates ---

    async def test_typo_candidates_at_every_scale(self, small_corpus, large_corpus):
        for typo, _ in FUZZY_QUERIES[:5]:
            for corpus in [small_corpus, large_corpus]:
                cands = corpus.get_candidates(typo, max_results=50)
                assert len(cands) > 0, f"Empty candidates for typo '{typo}' at {_label(corpus)}"


@pytest.mark.asyncio
class TestLemmaIndex:
    """Verify lemma_text_to_index is populated, consistent, and survives rebuilds."""

    async def test_populated_after_create(self, tiny_corpus):
        assert len(tiny_corpus.lemma_text_to_index) > 0
        assert len(tiny_corpus.lemma_text_to_index) == len(tiny_corpus.lemmatized_vocabulary)

    async def test_consistent_with_lemmatized_vocabulary(self, small_corpus):
        for lemma, idx in small_corpus.lemma_text_to_index.items():
            assert small_corpus.lemmatized_vocabulary[idx] == lemma

    async def test_survives_add_words(self, test_db):
        corpus = await _make_corpus(test_db, "lemma_add", VOCAB_TINY[:20])
        old_size = len(corpus.lemma_text_to_index)
        await corpus.add_words(["xylophone", "zebra", "quixotic"])
        # lemma_text_to_index should be rebuilt (not stale)
        assert len(corpus.lemma_text_to_index) >= old_size
        for lemma, idx in corpus.lemma_text_to_index.items():
            assert corpus.lemmatized_vocabulary[idx] == lemma

    async def test_survives_rebuild_indices(self, test_db):
        corpus = await _make_corpus(test_db, "lemma_rebuild", VOCAB_TINY[:20])
        await corpus._rebuild_indices()
        assert len(corpus.lemma_text_to_index) > 0
        for lemma, idx in corpus.lemma_text_to_index.items():
            assert corpus.lemmatized_vocabulary[idx] == lemma

    async def test_bidirectional_consistency(self, small_corpus):
        """lemma_text_to_index[text] == idx  <->  lemmatized_vocabulary[idx] == text"""
        for idx, lemma in enumerate(small_corpus.lemmatized_vocabulary):
            assert small_corpus.lemma_text_to_index[lemma] == idx


@pytest.mark.asyncio
class TestTrieIndexSort:
    async def test_trie_data_matches_vocabulary(self, tiny_corpus):
        trie_index = await TrieIndex.create(tiny_corpus)
        assert trie_index.trie_data == list(tiny_corpus.vocabulary)

    async def test_trie_data_is_sorted(self, small_corpus):
        trie_index = await TrieIndex.create(small_corpus)
        assert trie_index.trie_data == sorted(trie_index.trie_data)
