"""Tests for embedding-based synset matching.

These test the shared best_synset_by_embedding() function that replaces
the three duplicate word-overlap matchers across domain.py, frequency.py,
and hybrid.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from floridify.ai.embedding_utils import (
    best_synset_by_embedding,
    best_synset_word_overlap,
)


class TestWordOverlapFallback:
    """The synchronous word-overlap matcher — used when encoder is unavailable."""

    def test_bank_slope_matches_by_overlap(self) -> None:
        synset = best_synset_word_overlap(
            "bank", "noun",
            "sloping land especially the slope beside a body of water",
        )
        assert synset is not None
        assert "slop" in synset.definition().lower()

    def test_bank_financial_matches_by_overlap(self) -> None:
        synset = best_synset_word_overlap(
            "bank", "noun",
            "a financial institution that accepts deposits and channels money into lending",
        )
        assert synset is not None
        assert "financial" in synset.definition().lower() or "deposit" in synset.definition().lower()

    def test_returns_none_for_unknown_word(self) -> None:
        assert best_synset_word_overlap("xyzzyplugh", "noun", "nonsense") is None


class TestEmbeddingBasedMatching:
    """The async embedding-based matcher — primary path."""

    @pytest.mark.asyncio
    async def test_falls_back_when_encoder_unavailable(self) -> None:
        """When encode_texts returns None, falls back to word overlap."""
        with patch("floridify.ai.embedding_utils.encode_texts", new_callable=AsyncMock, return_value=None):
            synset = await best_synset_by_embedding(
                "bank", "noun",
                "a financial institution that accepts deposits",
            )
            # Should still return a result via word-overlap fallback
            assert synset is not None

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_word(self) -> None:
        synset = await best_synset_by_embedding("xyzzyplugh", "noun", "nonsense")
        assert synset is None

    @pytest.mark.asyncio
    async def test_bank_financial_with_real_encoder(self) -> None:
        """With real embeddings, should match the financial synset even for
        paraphrased definitions that word-overlap might miss."""
        synset = await best_synset_by_embedding(
            "bank", "noun",
            "A place where you deposit your money and get loans for purchases",
        )
        if synset is None:
            pytest.skip("Encoder not available in this environment")
        # Should match the financial institution synset, not slope
        assert "financial" in synset.definition().lower() or "deposit" in synset.definition().lower()

    @pytest.mark.asyncio
    async def test_bank_slope_with_real_encoder(self) -> None:
        synset = await best_synset_by_embedding(
            "bank", "noun",
            "The raised ground along the edge of a river where the water meets land",
        )
        if synset is None:
            pytest.skip("Encoder not available in this environment")
        assert "slop" in synset.definition().lower() or "land" in synset.definition().lower()

    @pytest.mark.asyncio
    async def test_bank_aviation_with_real_encoder(self) -> None:
        synset = await best_synset_by_embedding(
            "bank", "noun",
            "The lateral tilt of an aircraft during a turn, measured by wing angle",
        )
        if synset is None:
            pytest.skip("Encoder not available in this environment")
        # Should match the flight maneuver synset
        defn = synset.definition().lower()
        assert "aircraft" in defn or "flight" in defn or "lateral" in defn or "tip" in defn

    @pytest.mark.asyncio
    async def test_different_senses_match_different_synsets(self) -> None:
        """The key test: two different definitions of 'bank' should match
        two different synsets."""
        s1 = await best_synset_by_embedding(
            "bank", "noun",
            "A financial institution that manages deposits and provides loans",
        )
        s2 = await best_synset_by_embedding(
            "bank", "noun",
            "A raised strip of ground along a river forming the water's edge",
        )
        if s1 is None or s2 is None:
            pytest.skip("Encoder not available in this environment")
        assert s1.name() != s2.name(), f"Both matched {s1.name()} — should be different synsets"
