"""Tests for local CEFR level assessment (word-level + sense-adjusted)."""

from __future__ import annotations

import pytest

from floridify.ai.assessment.cefr import assess_cefr_local


class TestWordLevelCefr:
    @pytest.mark.asyncio
    async def test_core_words_are_a_level(self) -> None:
        result = await assess_cefr_local("the")
        assert result in ("A1", "A2")

    @pytest.mark.asyncio
    async def test_rare_words_are_c_level(self) -> None:
        result = await assess_cefr_local("perspicacious")
        assert result in ("C1", "C2")

    @pytest.mark.asyncio
    async def test_returns_valid_cefr_level(self) -> None:
        valid = {"A1", "A2", "B1", "B2", "C1", "C2"}
        for word in ["the", "run", "obtain", "perspicacious"]:
            result = await assess_cefr_local(word)
            assert result in valid


class TestSenseAdjustedCefr:
    @pytest.mark.asyncio
    async def test_common_sense_gets_base_level(self) -> None:
        result = await assess_cefr_local(
            "bank",
            definition_text="a financial institution that accepts deposits",
            part_of_speech="noun",
        )
        assert result is not None
        assert result in ("A2", "B1")

    @pytest.mark.asyncio
    async def test_rare_sense_gets_harder_level(self) -> None:
        common = await assess_cefr_local(
            "bank",
            definition_text="a financial institution that accepts deposits",
            part_of_speech="noun",
        )
        rare = await assess_cefr_local(
            "bank",
            definition_text="an arrangement of similar objects in a row or in tiers",
            part_of_speech="noun",
        )
        assert common is not None and rare is not None
        order = ["A1", "A2", "B1", "B2", "C1", "C2"]
        assert order.index(rare) >= order.index(common)

    @pytest.mark.asyncio
    async def test_without_definition_returns_word_level(self) -> None:
        result = await assess_cefr_local("bank")
        assert result is not None
        assert result in ("A1", "A2", "B1", "B2")
