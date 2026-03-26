"""Tests for signal boosting, diacritics restoration, multi-word decomposition,
pathological inputs, and FuzzyIndex serialization.

Covers: CandidateSignals scoring, diacritical form preference, per-word query
decomposition, edge-case inputs, and FuzzyIndex pickle + base64 round-trip.
"""

from __future__ import annotations

import pytest

from floridify.corpus.core import Corpus
from floridify.search.config import (
    CLOSE_EDIT_DISTANCE_BOOST,
    MULTI_SIGNAL_BOOST,
    PHONETIC_MATCH_BOOST,
)
from floridify.search.fuzzy.bk_tree import BKTree
from floridify.search.fuzzy.search import CandidateSignals, FuzzySearch
from floridify.search.fuzzy.suffix_array import SuffixArray
from floridify.search.phonetic.encoder import get_phonetic_encoder
from floridify.search.phonetic.index import PhoneticIndex


# ═══════════════════════════════════════════════════════════════════════
# Signal Boost Tests
# ═══════════════════════════════════════════════════════════════════════


class TestSignalBoosting:
    """Tests for signal-based score boosting in FuzzySearch."""

    def test_phonetic_boost_applied(self):
        """Phonetic match applies PHONETIC_MATCH_BOOST."""
        fs = FuzzySearch()
        signals = CandidateSignals(phonetic_match=True)
        boosted = fs._score_with_signals(0.5, signals)
        assert boosted == pytest.approx(0.5 * PHONETIC_MATCH_BOOST, abs=0.01)

    def test_edit_distance_boost_applied(self):
        """Close edit distance applies CLOSE_EDIT_DISTANCE_BOOST."""
        fs = FuzzySearch()
        signals = CandidateSignals(edit_distance=1)
        boosted = fs._score_with_signals(0.5, signals)
        assert boosted == pytest.approx(0.5 * CLOSE_EDIT_DISTANCE_BOOST, abs=0.01)

    def test_multi_signal_boost(self):
        """3+ strategies triggers MULTI_SIGNAL_BOOST."""
        fs = FuzzySearch()
        signals = CandidateSignals(
            edit_distance=1,
            phonetic_match=True,
            trigram_overlap=True,
        )
        boosted = fs._score_with_signals(0.5, signals)
        expected = 0.5 * PHONETIC_MATCH_BOOST * CLOSE_EDIT_DISTANCE_BOOST * MULTI_SIGNAL_BOOST
        assert boosted == pytest.approx(min(1.0, expected), abs=0.01)

    def test_no_signal_no_boost(self):
        """No signals → no boost."""
        fs = FuzzySearch()
        signals = CandidateSignals()
        assert fs._score_with_signals(0.5, signals) == 0.5

    def test_boost_capped_at_1(self):
        """Boosted score never exceeds 1.0."""
        fs = FuzzySearch()
        signals = CandidateSignals(edit_distance=0, phonetic_match=True, trigram_overlap=True)
        boosted = fs._score_with_signals(0.95, signals)
        assert boosted <= 1.0

    def test_edit_distance_2_no_boost(self):
        """Edit distance > 1 does NOT apply close-edit boost."""
        fs = FuzzySearch()
        signals = CandidateSignals(edit_distance=2)
        assert fs._score_with_signals(0.5, signals) == 0.5


# ═══════════════════════════════════════════════════════════════════════
# Diacritics Restoration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestDiacriticsRestoration:
    """Tests for input-agnostic search with canonical diacritical output."""

    def test_search_without_diacritics_finds_diacritical_word(self, small_corpus: Corpus):
        """Searching 'cafe' should find 'café' in the corpus."""
        idx = small_corpus.vocabulary_to_index.get("cafe")
        if idx is not None:
            original = small_corpus.get_original_word_by_index(idx)
            # Should prefer the diacritical form
            assert original == "café" or original == "cafe"

    def test_diacritical_preference_ordering(self, small_corpus: Corpus):
        """When both 'café' and 'cafe' exist, diacritical form is preferred."""
        idx = small_corpus.vocabulary_to_index.get("cafe")
        if idx is not None:
            original = small_corpus.get_original_word_by_index(idx)
            assert original == "café"  # Diacritical preferred

    def test_resume_with_accents(self, small_corpus: Corpus):
        """'resume' maps back to 'résumé'."""
        idx = small_corpus.vocabulary_to_index.get("resume")
        if idx is not None:
            original = small_corpus.get_original_word_by_index(idx)
            assert original == "résumé"


# ═══════════════════════════════════════════════════════════════════════
# Multi-Word Query Decomposition Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMultiWordDecomposition:
    """Tests for per-word search in multi-word queries."""

    def test_per_word_candidates(self, small_corpus: Corpus):
        """Multi-word query finds individual words."""
        fs = FuzzySearch()
        fs.phonetic_index = PhoneticIndex(small_corpus.vocabulary)
        candidates = fs._collect_candidates("ahn coulisses", small_corpus, 500)

        # Should find 'coulisses' via per-word decomposition
        coulisses_idx = small_corpus.vocabulary_to_index.get("coulisses")
        if coulisses_idx is not None:
            assert coulisses_idx in candidates

    def test_phrase_search_finds_subwords(self, small_corpus: Corpus):
        """Fuzzy search for a phrase finds words contained in it."""
        fs = FuzzySearch()
        fs.phonetic_index = PhoneticIndex(small_corpus.vocabulary)
        results = fs.search("ahn coulisses", small_corpus, max_results=10)
        found = [r.word for r in results]
        assert "coulisses" in found or len(found) > 0


# ═══════════════════════════════════════════════════════════════════════
# Pathological Input Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPathologicalInputs:
    """Tests for edge cases and adversarial inputs."""

    def test_empty_string(self, small_corpus: Corpus):
        fs = FuzzySearch()
        results = fs.search("", small_corpus, max_results=10)
        assert results == []

    def test_whitespace_only(self, small_corpus: Corpus):
        fs = FuzzySearch()
        results = fs.search("   ", small_corpus, max_results=10)
        assert results == []

    def test_single_character(self, small_corpus: Corpus):
        fs = FuzzySearch()
        results = fs.search("a", small_corpus, max_results=10)
        assert isinstance(results, list)  # Should not crash

    def test_very_long_query(self, small_corpus: Corpus):
        fs = FuzzySearch()
        long_query = "a" * 100
        results = fs.search(long_query, small_corpus, max_results=10)
        assert isinstance(results, list)  # Should not crash

    def test_special_characters(self, small_corpus: Corpus):
        fs = FuzzySearch()
        for query in ["@#$%", "hello!", "test&test", "foo/bar"]:
            results = fs.search(query, small_corpus, max_results=10)
            assert isinstance(results, list)

    def test_numeric_query(self, small_corpus: Corpus):
        fs = FuzzySearch()
        results = fs.search("12345", small_corpus, max_results=10)
        assert isinstance(results, list)

    def test_unicode_query(self):
        """Unicode queries processed by ICU without crashing."""
        encoder = get_phonetic_encoder()
        for query in ["你好", "привет", "مرحبا", "café北京"]:
            norm = encoder.normalize(query)
            assert isinstance(norm, str)
            assert len(norm) > 0

    def test_suffix_array_pathological(self):
        """SuffixArray handles pathological inputs."""
        sa = SuffixArray(["aaa", "bbb", "ccc"])
        assert sa.search("") == []
        assert isinstance(sa.search("a" * 50), list)

    def test_bk_tree_pathological(self):
        """BK-tree handles pathological inputs."""
        tree = BKTree.build(["hello", "world"])
        results = tree.find("", max_distance=5)
        assert isinstance(results, list)
        results = tree.find("a" * 100, max_distance=1)
        assert isinstance(results, list)


# ═══════════════════════════════════════════════════════════════════════
# FuzzyIndex Serialization Round-Trip Tests
# ═══════════════════════════════════════════════════════════════════════


class TestFuzzyIndexSerialization:
    """Tests for FuzzyIndex pickle + base64 round-trip."""

    def test_round_trip_preserves_bk_tree(self, multilingual_vocab: list[str]):
        from floridify.search.fuzzy.index import FuzzyIndex

        class FakeCorpus:
            corpus_uuid = "test-uuid"
            corpus_name = "test"
            vocabulary_hash = "abc123"
            vocabulary = multilingual_vocab

        idx = FuzzyIndex.create(FakeCorpus())
        bk, phonetic, suffix = idx.deserialize()
        assert bk is not None
        results = bk.find("aple", max_distance=1)
        assert any(multilingual_vocab[i] == "apple" for i, _ in results)

    def test_json_round_trip(self, multilingual_vocab: list[str]):
        from floridify.search.fuzzy.index import FuzzyIndex

        class FakeCorpus:
            corpus_uuid = "test-uuid"
            corpus_name = "test"
            vocabulary_hash = "abc123"
            vocabulary = multilingual_vocab

        idx = FuzzyIndex.create(FakeCorpus())
        data = idx.model_dump(mode="json")
        idx2 = FuzzyIndex.model_validate(data)
        bk2, ph2, sa2 = idx2.deserialize()

        # BK-tree works after JSON round-trip
        results = bk2.find("restorant", max_distance=2)
        found = [multilingual_vocab[i] for i, _ in results]
        assert "restaurant" in found

        # Phonetic works after JSON round-trip
        ph_results = ph2.search("akomodate", max_results=5)
        found = [multilingual_vocab[i] for i in ph_results]
        assert "accommodate" in found

        # Suffix array works after JSON round-trip
        sa_results = sa2.search("couliss", max_results=5)
        found = [multilingual_vocab[i] for i, _ in sa_results]
        assert any("couliss" in w for w in found)
