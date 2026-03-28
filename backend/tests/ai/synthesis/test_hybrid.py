"""Tests for hybrid synthesis: Wiktionary + WordNet → AI delta."""

from __future__ import annotations

import pytest

from floridify.ai.synthesis.hybrid import (
    compute_antonym_delta,
    compute_synonym_delta,
    get_wordnet_antonyms,
    get_wordnet_synonyms,
    merge_with_existing,
)


class TestGetWordNetSynonyms:
    @pytest.mark.asyncio
    async def test_returns_synonyms_for_common_word(self) -> None:
        syns = await get_wordnet_synonyms("happy")
        assert len(syns) > 0
        assert "happy" not in [s.lower() for s in syns]

    @pytest.mark.asyncio
    async def test_returns_empty_for_nonsense(self) -> None:
        assert await get_wordnet_synonyms("xyzzyplugh") == []

    @pytest.mark.asyncio
    async def test_sense_isolated_for_polysemous_word(self) -> None:
        """Financial synonyms should NOT appear in slope definition."""
        slope_syns = await get_wordnet_synonyms(
            "bank", "noun",
            "sloping land beside a body of water",
        )
        financial_syns = await get_wordnet_synonyms(
            "bank", "noun",
            "a financial institution that accepts deposits and channels money",
        )
        # These should be completely different sets
        slope_set = {s.lower() for s in slope_syns}
        financial_set = {s.lower() for s in financial_syns}
        # Financial terms like "banking concern" should NOT be in slope synonyms
        assert "banking concern" not in slope_set or len(slope_set) == 0

    @pytest.mark.asyncio
    async def test_limits_results(self) -> None:
        syns = await get_wordnet_synonyms("run")
        assert len(syns) <= 20


class TestGetWordNetAntonyms:
    @pytest.mark.asyncio
    async def test_returns_antonyms_for_adjective(self) -> None:
        ants = await get_wordnet_antonyms("good")
        assert len(ants) > 0


class TestMergeWithExisting:
    def test_merges_unique_items(self) -> None:
        assert merge_with_existing(["a", "b"], ["c", "d"]) == ["a", "b", "c", "d"]

    def test_deduplicates_case_insensitive(self) -> None:
        result = merge_with_existing(["Apple", "banana"], ["apple", "Cherry"])
        assert len(result) == 3

    def test_respects_max_total(self) -> None:
        result = merge_with_existing(["a", "b"], ["c", "d", "e"], max_total=3)
        assert len(result) == 3


class TestComputeSynonymDelta:
    @pytest.mark.asyncio
    async def test_wordnet_reduces_ai_needed(self, test_db) -> None:
        from bson import ObjectId

        from floridify.models.dictionary import Definition

        defn = Definition(
            word_id=ObjectId(),
            part_of_speech="noun",
            text="a financial institution that accepts deposits and channels money into lending",
            synonyms=["lender"],
        )
        merged, ai_needed = await compute_synonym_delta(defn, "bank", target_count=10)
        assert len(merged) > 1
        assert ai_needed < 10

    @pytest.mark.asyncio
    async def test_enough_local_means_zero_ai(self, test_db) -> None:
        from bson import ObjectId

        from floridify.models.dictionary import Definition

        defn = Definition(
            word_id=ObjectId(),
            part_of_speech="noun",
            text="a rounded fruit",
            synonyms=["fruit"] * 10,
        )
        merged, ai_needed = await compute_synonym_delta(defn, "apple", target_count=10)
        assert ai_needed == 0


class TestComputeAntonymDelta:
    @pytest.mark.asyncio
    async def test_wordnet_provides_antonyms(self, test_db) -> None:
        from bson import ObjectId

        from floridify.models.dictionary import Definition

        defn = Definition(
            word_id=ObjectId(),
            part_of_speech="adjective",
            text="having desirable or positive qualities, the opposite of bad",
            antonyms=[],
        )
        merged, ai_needed = await compute_antonym_delta(defn, "good", target_count=5)
        # good.a.01 has antonym "bad" — should find it
        assert len(merged) > 0
        assert ai_needed < 5
