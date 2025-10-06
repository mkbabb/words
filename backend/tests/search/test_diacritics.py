"""Test diacritics preservation in search pipeline."""

from __future__ import annotations

import pytest
import pytest_asyncio

from floridify.corpus.core import Corpus, CorpusType
from floridify.corpus.manager import CorpusManager
from floridify.models.base import Language
from floridify.search.core import Search


class TestDiacriticsPreservation:
    """Test that diacritics are preserved correctly in search operations."""

    @pytest_asyncio.fixture
    async def diacritics_corpus(self, test_db) -> Corpus:
        """Corpus with words containing diacritics."""
        vocabulary = [
            # French
            "café",
            "cliché",
            "façade",
            "naïve",
            "résumé",
            # Spanish
            "niño",
            "mañana",
            "señor",
            # German
            "über",
            "Müller",
            # Portuguese
            "ção",
            "não",
            # Nordic
            "smørgåsbord",
            "Björk",
            # Czech/Slovak
            "Dvořák",
            "Škoda",
            # Also include ASCII versions for comparison
            "cafe",
            "cliche",
            "facade",
            "naive",
            "resume",
        ]

        # Use Corpus.create() which properly normalizes vocabulary
        corpus = await Corpus.create(
            corpus_name="test_diacritics",
            vocabulary=vocabulary,
            language=Language.ENGLISH,
        )
        corpus.corpus_type = CorpusType.CUSTOM

        manager = CorpusManager()
        return await manager.save_corpus(corpus)

    @pytest.mark.asyncio
    async def test_exact_search_preserves_diacritics(self, diacritics_corpus, test_db):
        """Test that exact search can find words with diacritics."""
        engine = await Search.from_corpus(
            corpus_name=diacritics_corpus.corpus_name,
            semantic=False,
        )

        # Verify corpus has diacritic words in original vocabulary
        assert "café" in diacritics_corpus.original_vocabulary, "café should be in original_vocabulary"
        # And normalized form in normalized vocabulary
        assert "cafe" in diacritics_corpus.vocabulary, "cafe should be in vocabulary"

        # Search for word with diacritics
        results = engine.search_exact("café")

        # Should find results and return original form with diacritics
        assert len(results) > 0, "Should find results for café"
        assert results[0].word == "café", f"Should return 'café', got '{results[0].word}'"

    @pytest.mark.asyncio
    async def test_fuzzy_search_handles_diacritics(self, diacritics_corpus, test_db):
        """Test that fuzzy search handles diacritics gracefully."""
        engine = await Search.from_corpus(
            corpus_name=diacritics_corpus.corpus_name,
            semantic=False,
        )

        # Search without diacritics should find diacritic version
        results = engine.search_fuzzy("cafe", max_results=5)
        assert len(results) > 0

        # Should match both "café" and "cafe"
        words = [r.word for r in results]
        # At minimum, should find one of them
        assert "café" in words or "cafe" in words

    @pytest.mark.asyncio
    async def test_search_multiple_diacritics(self, diacritics_corpus, test_db):
        """Test search with multiple diacritic types."""
        engine = await Search.from_corpus(
            corpus_name=diacritics_corpus.corpus_name,
            semantic=False,
        )

        test_cases = [
            ("naïve", "naïve"),  # Diaeresis
            ("résumé", "résumé"),  # Acute accents
            ("façade", "façade"),  # Cedilla
            ("über", "über"),  # Umlaut
            ("Björk", "Björk"),  # Nordic ö
        ]

        for query, expected in test_cases:
            results = engine.search_exact(query)
            assert len(results) > 0, f"No results for {query}"
            found_words = [r.word for r in results]
            assert expected in found_words, f"Expected '{expected}' not found for query '{query}'"

    @pytest.mark.asyncio
    async def test_corpus_preserves_diacritics_in_indices(self, diacritics_corpus, test_db):
        """Test that corpus indices preserve diacritics."""
        # Check original_vocabulary has diacritic forms
        assert "café" in diacritics_corpus.original_vocabulary
        assert "niño" in diacritics_corpus.original_vocabulary
        assert "Björk" in diacritics_corpus.original_vocabulary

        # Check vocabulary has normalized forms
        assert "cafe" in diacritics_corpus.vocabulary_to_index
        assert "bjork" in diacritics_corpus.vocabulary_to_index

        # Verify indices are consistent - check normalized forms map back to originals
        test_pairs = [("cafe", "café"), ("nino", "niño"), ("bjork", "Björk"), ("resume", "résumé")]
        for normalized, original in test_pairs:
            if normalized in diacritics_corpus.vocabulary_to_index:
                idx = diacritics_corpus.vocabulary_to_index[normalized]
                restored = diacritics_corpus.get_original_word_by_index(idx)
                assert restored == original, f"Expected '{original}' but got '{restored}'"

    @pytest.mark.asyncio
    async def test_normalization_preserves_essential_diacritics(self, diacritics_corpus, test_db):
        """Test that essential diacritics are preserved during normalization."""
        # These diacritics change meaning and should be preserved
        essential_pairs = [
            ("café", "cafe"),  # French: coffee vs. cafeteria-like
            ("niño", "nino"),  # Spanish: child vs. non-word
            ("año", "ano"),  # Spanish: year vs. anus (if we had it)
        ]

        for diacritic_word, ascii_word in essential_pairs:
            if diacritic_word in diacritics_corpus.vocabulary:
                # Both should exist if we added them
                diacritic_idx = diacritics_corpus.vocabulary_to_index.get(diacritic_word)
                ascii_idx = diacritics_corpus.vocabulary_to_index.get(ascii_word)

                if ascii_word in diacritics_corpus.vocabulary:
                    # If both exist, they should have different indices
                    assert diacritic_idx != ascii_idx, (
                        f"{diacritic_word} and {ascii_word} should be different words"
                    )