"""Tests for local frequency assessment (word-level + sense-level)."""

from __future__ import annotations

import pytest

from floridify.ai.assessment.frequency import (
    adjust_band_for_sense,
    assess_frequency_local,
    assess_frequency_score_local,
    assess_sense_frequency,
)


class TestWordLevelFrequency:
    def test_core_vocabulary_is_band_5(self) -> None:
        assert assess_frequency_local("the") == 5

    def test_rare_words_are_band_1(self) -> None:
        assert assess_frequency_local("perspicacious") == 1

    def test_returns_int_in_valid_range(self) -> None:
        for word in ["the", "run", "happy", "perspicacious"]:
            result = assess_frequency_local(word)
            assert result is not None
            assert 1 <= result <= 5

    def test_monotonic_ordering(self) -> None:
        band_the = assess_frequency_local("the")
        band_rare = assess_frequency_local("perspicacious")
        assert band_the is not None and band_rare is not None
        assert band_the >= band_rare


class TestFrequencyScore:
    def test_returns_float_in_range(self) -> None:
        score = assess_frequency_score_local("run")
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_common_word_has_high_score(self) -> None:
        score = assess_frequency_score_local("the")
        assert score is not None
        assert score > 0.7

    def test_rare_word_has_low_score(self) -> None:
        score = assess_frequency_score_local("defenestrate")
        assert score is not None
        assert score < 0.3


class TestSenseFrequency:
    """Per-sense frequency from WordNet SemCor corpus counts."""

    @pytest.mark.asyncio
    async def test_dominant_sense_has_high_frequency(self) -> None:
        freq = await assess_sense_frequency(
            "bank", "noun",
            "sloping land especially the slope beside a body of water",
        )
        assert freq is not None
        assert freq > 0.3

    @pytest.mark.asyncio
    async def test_rare_sense_has_low_frequency(self) -> None:
        freq = await assess_sense_frequency(
            "bank", "noun",
            "an arrangement of similar objects in a row or in tiers",
        )
        assert freq is not None
        assert freq < 0.1

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_word(self) -> None:
        freq = await assess_sense_frequency("xyzzyplugh", "noun", "nonsense")
        assert freq is None

    @pytest.mark.asyncio
    async def test_different_senses_get_different_frequencies(self) -> None:
        freq_slope = await assess_sense_frequency(
            "bank", "noun", "sloping land beside a body of water",
        )
        freq_row = await assess_sense_frequency(
            "bank", "noun", "an arrangement of similar objects in a row",
        )
        assert freq_slope is not None and freq_row is not None
        assert freq_slope > freq_row


class TestBandAdjustment:
    def test_dominant_sense_keeps_band(self) -> None:
        assert adjust_band_for_sense(4, 0.5) == 4

    def test_rare_sense_drops_band(self) -> None:
        assert adjust_band_for_sense(4, 0.03) <= 3

    def test_none_frequency_keeps_band(self) -> None:
        assert adjust_band_for_sense(4, None) == 4

    def test_never_below_band_1(self) -> None:
        assert adjust_band_for_sense(1, 0.01) == 1
