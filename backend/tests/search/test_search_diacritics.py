"""Diacritics, multi-word, combining characters, and Unicode edge cases."""

from __future__ import annotations

import pytest

from floridify.search.constants import SearchMode


@pytest.mark.asyncio
class TestDiacriticsAndUnicode:
    """Verify diacritics, combining characters, and Unicode edge cases."""

    # --- Normalization strips diacritics for indexing ---

    async def test_diacritics_stripped_in_vocabulary(self, diacritics_corpus):
        """Vocabulary should contain normalized (ASCII) forms."""
        vocab_set = set(diacritics_corpus.vocabulary)
        # "cafe" normalizes to "cafe"
        assert "cafe" in vocab_set, "Normalized 'cafe' should be in vocabulary"
        # "naive" normalizes to "naive"
        assert "naive" in vocab_set

    async def test_original_vocabulary_preserves_diacritics(self, diacritics_corpus):
        """Original vocabulary should keep diacritics (NFC-normalized)."""
        orig_set = set(diacritics_corpus.original_vocabulary)
        # Input is NFC-normalized: decomposed forms become precomposed
        assert "café" in orig_set
        assert "naïve" in orig_set
        assert "résumé" in orig_set

    # --- Exact search finds diacriticized queries ---

    async def test_exact_finds_cafe_with_accent(self, diacritics_engine):
        """Query 'cafe' should find 'cafe' via normalization."""
        results = diacritics_engine.search_exact("cafe\u0301")
        assert len(results) >= 1, "Exact search should find 'cafe' -> 'cafe'"

    async def test_exact_finds_naive_with_diaeresis(self, diacritics_engine):
        results = diacritics_engine.search_exact("nai\u0308ve")
        assert len(results) >= 1

    async def test_exact_finds_resume_with_accents(self, diacritics_engine):
        results = diacritics_engine.search_exact("re\u0301sume\u0301")
        assert len(results) >= 1

    async def test_exact_finds_uber_with_umlaut(self, diacritics_engine):
        results = diacritics_engine.search_exact("\u00fcber")
        assert len(results) >= 1

    # --- Combining characters (U+0301 etc.) normalize same as precomposed ---

    async def test_combining_acute_matches_precomposed(self, diacritics_engine):
        """'cafe\\u0301' (e + combining acute) should match same as 'cafe' (precomposed)."""
        results = diacritics_engine.search_exact("cafe\u0301")
        assert len(results) >= 1, "Combining acute on 'e' should normalize to 'cafe'"

    async def test_combining_diaeresis_matches_precomposed(self, diacritics_engine):
        """'nai\\u0308ve' should match same as 'naive'."""
        results = diacritics_engine.search_exact("nai\u0308ve")
        assert len(results) >= 1

    # --- Fuzzy search with diacritics ---

    async def test_fuzzy_finds_cafe_typo(self, diacritics_engine):
        """Typo 'caff' should find 'cafe'."""
        results = diacritics_engine.search_fuzzy("caff", max_results=10)
        words = [r.word.lower() for r in results]
        # Should find cafe/cafe
        assert any("caf" in w for w in words), f"Expected cafe-like result, got {words}"

    async def test_fuzzy_finds_jalapeno_typo(self, diacritics_engine):
        """Typo 'jalapno' should find 'jalapeno' (normalized from jalapeno)."""
        results = diacritics_engine.search_fuzzy("jalapno", max_results=10)
        words = [r.word.lower() for r in results]
        assert any("jalap" in w for w in words), f"Expected jalapeno, got {words}"

    # --- Multi-word queries ---

    async def test_exact_finds_multi_word(self, diacritics_engine):
        """Exact search for 'ice cream' should find it."""
        results = diacritics_engine.search_exact("ice cream")
        assert len(results) >= 1, "Should find 'ice cream' as exact match"

    async def test_exact_finds_en_coulisses(self, diacritics_engine):
        """Exact search for 'en coulisses' should find it."""
        results = diacritics_engine.search_exact("en coulisses")
        assert len(results) >= 1

    async def test_exact_finds_a_fond(self, diacritics_engine):
        """Exact search for 'a fond' should find it."""
        results = diacritics_engine.search_exact("a fond")
        assert len(results) >= 1

    async def test_fuzzy_finds_multi_word_typo(self, diacritics_engine):
        """Fuzzy search for 'machne lerning' should find 'machine learning'."""
        results = diacritics_engine.search_fuzzy("machne lerning", max_results=10)
        words = [r.word.lower() for r in results]
        # Should find either the full phrase or component words
        assert any("machine" in w or "learning" in w for w in words), (
            f"Expected machine/learning, got {words}"
        )

    # --- Smart cascade with diacritics ---

    async def test_smart_finds_cafe_accent(self, diacritics_engine):
        results = await diacritics_engine.search_with_mode(
            "cafe\u0301", mode=SearchMode.SMART, max_results=10
        )
        assert len(results) >= 1

    async def test_smart_finds_en_coulisses(self, diacritics_engine):
        results = await diacritics_engine.search_with_mode(
            "en coulisses", mode=SearchMode.SMART, max_results=10
        )
        words = [r.word.lower() for r in results]
        assert "en coulisses" in words

    # --- Apostrophe / contraction handling (normalize expands contractions) ---

    async def test_exact_finds_dont_contraction(self, diacritics_engine):
        """Query \"don't\" normalizes to 'do not' and finds it."""
        results = diacritics_engine.search_exact("don't")
        assert len(results) >= 1, "Should find 'do not' via contraction expansion"

    async def test_exact_finds_its_contraction(self, diacritics_engine):
        """Query \"it's\" normalizes to 'it is' and finds it."""
        results = diacritics_engine.search_exact("it's")
        assert len(results) >= 1

    # --- Hyphen handling (normalize converts hyphens to spaces) ---

    async def test_exact_finds_hyphenated_query(self, diacritics_engine):
        """Query 'well-known' normalizes to 'well known' and matches."""
        results = diacritics_engine.search_exact("well-known")
        assert len(results) >= 1

    # --- Zero-width and control characters ---

    async def test_zero_width_space_ignored(self, diacritics_engine):
        """Zero-width space (U+200B) should be stripped, not crash."""
        results = diacritics_engine.search_exact("app\u200ble")
        assert isinstance(results, list)

    async def test_zero_width_joiner_ignored(self, diacritics_engine):
        """Zero-width joiner (U+200D) should not crash."""
        results = diacritics_engine.search_fuzzy("hap\u200dpy", max_results=5)
        assert isinstance(results, list)
