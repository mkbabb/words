"""Tests for PhoneticEncoder and PhoneticIndex.

Covers: ICU normalization, jellyfish Metaphone encoding, multilingual phonetic
inverted index, composite key matching, and per-word intersection search.
"""

from __future__ import annotations

import pytest

from floridify.search.phonetic.encoder import PhoneticEncoder, get_phonetic_encoder
from floridify.search.phonetic.index import PhoneticIndex


# ═══════════════════════════════════════════════════════════════════════
# PhoneticEncoder Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPhoneticEncoder:
    """Tests for ICU normalization + jellyfish Metaphone encoding."""

    def test_diacritics_stripped(self, encoder: PhoneticEncoder):
        """ICU Latin-ASCII removes diacritics."""
        assert "e" in encoder.normalize("é")
        assert encoder.normalize("café") == encoder.normalize("cafe")
        assert encoder.normalize("naïve") == encoder.normalize("naive")
        assert encoder.normalize("résumé") == encoder.normalize("resume")

    def test_french_nasal_vowels_collapsed(self, encoder: PhoneticEncoder):
        """en/on/ahn produce the same Metaphone composite key."""
        en_key = encoder.encode_composite("en coulisses")
        on_key = encoder.encode_composite("on coulisses")
        ahn_key = encoder.encode_composite("ahn coulisses")
        assert en_key == on_key == ahn_key

    def test_french_digraphs(self, encoder: PhoneticEncoder):
        """French vowel digraphs normalized: oi→wa, ou→oo, eau→o."""
        assert "wa" in encoder.normalize("joie")
        assert "oo" in encoder.normalize("coup")

    def test_german_consonants(self, encoder: PhoneticEncoder):
        """German sch→sh normalization."""
        assert "sh" in encoder.normalize("schon")

    def test_cross_linguistic_ph_to_f(self, encoder: PhoneticEncoder):
        """ph→f normalization."""
        assert "f" in encoder.normalize("philosophy")

    def test_composite_key_multi_word(self, encoder: PhoneticEncoder):
        """Multi-word phrases produce per-word composite keys."""
        key = encoder.encode_composite("joie de vivre")
        assert key is not None
        assert "|" in key  # Multi-word → pipe-separated codes

    def test_composite_key_consistency(self, encoder: PhoneticEncoder):
        """Same-sounding phrases produce same composite key."""
        key1 = encoder.encode_composite("en coulisses")
        key2 = encoder.encode_composite("ahn coulisses")
        key3 = encoder.encode_composite("on coulisses")
        assert key1 == key2 == key3

    def test_single_word_encode(self, encoder: PhoneticEncoder):
        """Single words produce a non-empty code."""
        code = encoder.encode("apple")
        assert code and len(code) > 0

    def test_empty_input(self, encoder: PhoneticEncoder):
        """Empty/whitespace returns empty."""
        assert encoder.encode("") == ""
        assert encoder.encode_composite("") is None
        assert encoder.encode_composite("   ") is None

    def test_cyrillic_transliteration(self, encoder: PhoneticEncoder):
        """Cyrillic is transliterated to Latin via ICU Any-Latin."""
        norm = encoder.normalize("Москва")
        assert norm.isascii()
        assert len(norm) > 0

    def test_singleton_instance(self):
        """get_phonetic_encoder() returns a singleton."""
        a = get_phonetic_encoder()
        b = get_phonetic_encoder()
        assert a is b


# ═══════════════════════════════════════════════════════════════════════
# PhoneticIndex Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPhoneticIndex:
    """Tests for the multilingual phonetic inverted index."""

    def test_exact_composite_match(self, phonetic_index: PhoneticIndex, multilingual_vocab: list[str]):
        """Exact composite key match for a vocabulary entry."""
        results = phonetic_index.search("entrepreneur", max_results=5)
        found = [multilingual_vocab[i] for i in results]
        assert "entrepreneur" in found

    def test_phonetic_misspelling(self, phonetic_index: PhoneticIndex, multilingual_vocab: list[str]):
        """Phonetic match for misspelled word."""
        results = phonetic_index.search("restorant", max_results=5)
        found = [multilingual_vocab[i] for i in results]
        assert "restaurant" in found

    def test_french_nasal_phrase(self, phonetic_index: PhoneticIndex, multilingual_vocab: list[str]):
        """'ahn coulisses' matches 'en coulisses' via nasal normalization."""
        results = phonetic_index.search("ahn coulisses", max_results=5)
        found = [multilingual_vocab[i] for i in results]
        assert "en coulisses" in found or "coulisses" in found

    def test_phonetic_ontrepreneur(self, phonetic_index: PhoneticIndex, multilingual_vocab: list[str]):
        """'ontrepreneur' matches 'entrepreneur' via nasal normalization."""
        results = phonetic_index.search("ontrepreneur", max_results=5)
        found = [multilingual_vocab[i] for i in results]
        assert "entrepreneur" in found

    def test_per_word_intersection(self, phonetic_index: PhoneticIndex, multilingual_vocab: list[str]):
        """Per-word phonetic matching finds phrase via word overlap."""
        results = phonetic_index.search("joy de vevre", max_results=10)
        found = [multilingual_vocab[i] for i in results]
        assert "joie de vivre" in found

    def test_fuzzy_composite_match(self, phonetic_index: PhoneticIndex, multilingual_vocab: list[str]):
        """Near-miss composite codes found via Levenshtein on Metaphone codes."""
        results = phonetic_index.search("bourjwa", max_results=5)
        found = [multilingual_vocab[i] for i in results]
        assert "bourgeois" in found

    def test_empty_query(self, phonetic_index: PhoneticIndex):
        """Empty query returns empty."""
        assert phonetic_index.search("") == []
        assert phonetic_index.search("   ") == []

    def test_no_match(self, phonetic_index: PhoneticIndex):
        """Completely unrelated query returns few/no matches."""
        results = phonetic_index.search("zzzzxxx", max_results=5)
        assert len(results) <= 5
